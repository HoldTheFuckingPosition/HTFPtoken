"""Prospectively counted finite loopback campaign; no native or public network."""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import sys
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
from htfp_readonly import core
from htfp_readonly.server import Handler, make_server


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class Ledger:
    """Durable append-only attempt journal, including unfinished runs."""
    def __init__(self, evidence, run_id, role):
        self.evidence = evidence
        self.role = role
        self.run_id = run_id
        self.path = evidence / "HTTP_LEDGER.jsonl"
        global_count = 0
        role_count = 0
        for existing in sorted((ROOT / "evidence/m6a").rglob("HTTP_LEDGER.jsonl")):
            active = set()
            for line in existing.read_text().splitlines():
                row = json.loads(line)
                if row["event"] == "RUN_STARTED":
                    assert row["run_id"] not in active
                    active.add(row["run_id"])
                elif row["event"] == "ATTEMPT_STARTED":
                    global_count += 1
                    if row["role"] == role:
                        role_count += 1
                elif row["event"] == "RUN_FINALIZED":
                    active.remove(row["run_id"])
            assert not active, "Unfinalized HTTP campaign blocks new requests: " + str(existing)
        self.prior_global = global_count
        self.prior_role = role_count
        self.attempted = self.completed = self.server_seen = 0
        self.rows = []

    def append(self, event, **fields):
        row = {"event": event, "run_id": self.run_id, "role": self.role, "UTC": now(), **fields}
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            import os
            os.fsync(stream.fileno())

    def begin(self):
        self.append("RUN_STARTED", prior_global_attempts=self.prior_global, prior_role_attempts=self.prior_role)

    def request(self, server, name, target, expected_status, expected_code=None, headers=None, body=None, checks=None):
        assert self.prior_role + self.attempted < 256, "Role HTTP budget exhausted"
        assert self.prior_global + self.attempted < 512, "Global HTTP budget exhausted"
        self.attempted += 1
        self.append("ATTEMPT_STARTED", attempt=self.attempted, name=name, target=target,
                    cumulative_role=self.prior_role + self.attempted, cumulative_global=self.prior_global + self.attempted)
        row = {"attempt": self.attempted, "name": name, "target": target, "headers": headers or {},
               "expected_status": expected_status, "expected_code": expected_code}
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
            connection.request("GET", target, body=body, headers=headers or {})
            response = connection.getresponse()
            raw = response.read(16385)
            self.completed += 1
            row.update(status=response.status, response_headers=dict(response.getheaders()),
                       response_sha256=hashlib.sha256(raw).hexdigest(), response_bytes=len(raw))
            parsed = json.loads(raw)
            row["response"] = parsed
            assert response.status == expected_status, row
            assert response.getheader("Content-Type") == "application/json; charset=utf-8"
            assert response.getheader("Cache-Control") == "no-store"
            assert response.getheader("Connection") == "close"
            assert response.getheader("Content-Length") == str(len(raw)) and len(raw) <= 16384
            assert response.getheader("Access-Control-Allow-Origin") is None
            assert response.getheader("Content-Encoding") is None
            assert parsed["api_version"] == "HTFP_READONLY_V1"
            code = parsed["error"]["code"] if parsed["error"] else None
            assert code == expected_code, row
            if expected_code:
                assert parsed["error"]["message"] == core.ERRORS[expected_code][1]
                assert "payout_lamports" not in parsed and "state" not in parsed
            if checks:
                checks(parsed)
            row["assertions"] = "PASS"
        except BaseException as exc:
            row["assertions"] = "FAIL"
            row["exception"] = type(exc).__name__ + ": " + str(exc)
            raise
        finally:
            connection.close()
            self.rows.append(row)
            self.append("ATTEMPT_FINISHED", attempt=self.attempted, completed_response="status" in row,
                        assertions=row["assertions"], server_seen=self.server_seen)

    def finish(self, status):
        self.append("RUN_FINALIZED", status=status, attempted=self.attempted, completed=self.completed,
                    server_seen=self.server_seen, cumulative_role=self.prior_role + self.attempted,
                    cumulative_global=self.prior_global + self.attempted)


@contextmanager
def serving(ledger, profile):
    class CountedHandler(Handler):
        def parse_request(self):
            # Observe stdlib parsing without changing target/framing semantics.
            ledger.server_seen += 1
            return super().parse_request()
    server = make_server(profile, handler_class=CountedHandler)
    assert server.server_address[0] == "127.0.0.1"
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
        assert not thread.is_alive(), "Listener thread remained alive"


def run(ledger):
    def health_unconfigured(body):
        assert body["mode"] == "UNCONFIGURED" and body["ready"] is False
        assert body["profile_state"] == "UNCONFIGURED" and body["snapshot_id"] is None
    def status_unconfigured(body):
        assert not body["ready"] and body["state"] is None and body["provenance"] is None
        assert body["production_profile_configured"] is False and body["data_current"] is False
    full = "9999999994000000000"
    base = "/v1/redemption-preview?amount_base_units="
    with serving(ledger, "unconfigured") as server:
        ledger.request(server, "default_health", "/health", 200, checks=health_unconfigured)
        ledger.request(server, "default_status", "/v1/status", 200, checks=status_unconfigured)
        ledger.request(server, "default_preview", base + full + "&minimum_lamports=0", 503, "PROFILE_UNCONFIGURED")
        ledger.request(server, "syntax_before_profile", base + "01&minimum_lamports=0", 400, "INVALID_QUERY")
    def status_local(body):
        state = body["state"]
        assert body["ready"] and body["mode"] == "SYNTHETIC_LOCAL_HISTORICAL"
        assert body["snapshot_id"] == core.t.SNAPSHOT_ID and body["snapshot_sha256"] == core.t.SNAPSHOT_SHA256
        assert all(type(value) is str for value in state.values())
        assert state["supply_base_units"] == full and state["backing_lamports"] == "90565764"
        assert body["provenance"]["public_cluster"] is None and body["provenance"]["event_index"] == "24"
        assert not body["production_profile_configured"] and not body["data_current"]
    def preview_ok(payout, amount):
        def check(body):
            assert body["payout_lamports"] == payout and body["amount_base_units"] == amount
            assert body["arithmetic_only"] and body["authorization_verified"] is False
            assert body["execution_guaranteed"] is False and body["eligibility"] == "UNASSESSED"
            assert not body["production_profile_configured"] and not body["data_current"]
            assert body["provenance"] == core.provenance()
            assert "can_redeem" not in body and "transaction" not in body
            for field in ("amount_base_units", "minimum_lamports", "supply_base_units", "reserve_lamports",
                          "maintenance_lamports", "backing_lamports", "payout_lamports", "division_remainder"):
                assert type(body[field]) is str
        return check
    with serving(ledger, "local-historical") as server:
        ledger.request(server, "local_health", "/health", 200, checks=lambda body: body["ready"] is True or (_ for _ in ()).throw(AssertionError()))
        ledger.request(server, "local_status", "/v1/status", 200, checks=status_local)
        for name, amount, minimum, status, code, payout in (
            ("full_supply", full, "0", 200, None, "90565764"),
            ("exact_minimum", full, "90565764", 200, None, "90565764"),
            ("minimum_one_over", full, "90565765", 422, "MINIMUM_NOT_MET", None),
            ("odd_valid", "110417000337", "1", 200, None, "1"),
            ("first_positive", "110417000336", "0", 200, None, "1"),
            ("last_zero", "110417000335", "0", 422, "ZERO_PAYOUT", None),
            ("tiny", "1", "0", 422, "ZERO_PAYOUT", None),
            ("zero", "0", "0", 422, "INVALID_AMOUNT", None),
            ("above_supply", "9999999994000000001", "0", 422, "AMOUNT_EXCEEDS_SUPPLY", None),
            ("u64_amount", str(core.U64_MAX), "0", 422, "AMOUNT_EXCEEDS_SUPPLY", None),
            ("u64_overflow", str(2**64), "0", 400, "INTEGER_OUT_OF_RANGE", None),
            ("large_odd_exact", "9007199254740993", "0", 200, None, "81574")):
            ledger.request(server, name, base + amount + "&minimum_lamports=" + minimum, status, code,
                           checks=preview_ok(payout, amount) if payout is not None else None)
        ledger.request(server, "query_reordered", "/v1/redemption-preview?minimum_lamports=1&amount_base_units=110417000337", 200,
                       checks=preview_ok("1", "110417000337"))
        for name, target, code in (
            ("unknown", "/v1/other", "NOT_FOUND"), ("double_slash", "//health", "INVALID_REQUEST"),
            ("encoded", "/he%61lth", "INVALID_REQUEST"), ("fragment", "/health#x", "INVALID_REQUEST"),
            ("plus", "/health+x", "INVALID_REQUEST"), ("absolute", "http://example.invalid/health", "INVALID_REQUEST"),
            ("health_query", "/health?x=0", "INVALID_QUERY"), ("empty_health_query", "/health?", "INVALID_QUERY"),
            ("missing_key", base + "1", "INVALID_QUERY"),
            ("duplicate", base + "1&minimum_lamports=0&minimum_lamports=0", "INVALID_QUERY"),
            ("unknown_key", base + "1&minimum_lamports=0&profile=local", "INVALID_QUERY"),
            ("leading_zero", base + "01&minimum_lamports=0", "INVALID_QUERY"),
            ("negative", base + "-1&minimum_lamports=0", "INVALID_QUERY"),
            ("exponent", base + "1e5&minimum_lamports=0", "INVALID_QUERY"),
            ("empty_minimum", base + "1&minimum_lamports=", "INVALID_QUERY"),
            ("query_limit", "/v1/redemption-preview?" + "x" * 129, "REQUEST_TOO_LARGE"),
            ("target_limit", "/" + "x" * 1024, "REQUEST_TOO_LARGE")):
            ledger.request(server, name, target, 414 if code == "REQUEST_TOO_LARGE" else 404 if code == "NOT_FOUND" else 400, code)
        ledger.request(server, "body_rejected", "/health", 400, "INVALID_REQUEST", body=b"x")
        ledger.request(server, "transfer_encoding_rejected", "/health", 400, "INVALID_REQUEST", headers={"Transfer-Encoding": "chunked"})
        ledger.request(server, "length_zero_allowed", "/v1/status", 200, headers={"Content-Length": "0"}, checks=status_local)
        ledger.request(server, "length_noncanonical", "/health", 400, "INVALID_REQUEST", headers={"Content-Length": "00"})
        # In-memory test-only corrupt/missing read; never change the actual packaged fixture.
        with patch.object(core, "read_snapshot_bytes", return_value=b"bad"):
            ledger.request(server, "changed_health", "/health", 200,
                           checks=lambda body: body["ready"] is False and body["profile_state"] == "INVALID" or (_ for _ in ()).throw(AssertionError()))
            ledger.request(server, "changed_status", "/v1/status", 503, "SNAPSHOT_INVALID")
            ledger.request(server, "changed_preview", base + full + "&minimum_lamports=0", 503, "SNAPSHOT_INVALID")
            ledger.request(server, "bad_syntax_before_changed_snapshot", base + "00&minimum_lamports=0", 400, "INVALID_QUERY")
        with patch.object(core, "read_snapshot_bytes", side_effect=FileNotFoundError()):
            ledger.request(server, "missing_status", "/v1/status", 503, "SNAPSHOT_INVALID")
        ledger.request(server, "restored_status", "/v1/status", 200, checks=status_local)
    assert ledger.attempted == ledger.completed == ledger.server_seen
    return {"status": "LOOPBACK_APPLICATION_CHECKS_PASS", "attempted": ledger.attempted,
            "completed": ledger.completed, "server_seen": ledger.server_seen,
            "listeners_closed": True, "native_VMs": 0, "native_sends": 0,
            "limitations": "Finite normal-GET contract checks. Pre-handler stdlib malformed transport/unsupported methods are not a JSON-conformance claim."}
