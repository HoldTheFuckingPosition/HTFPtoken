"""Finite constructive arithmetic and strict decoder/query checks. No HTTP."""

import copy
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import random
import struct
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))
from htfp_readonly import core
from htfp_readonly.server import Handler


def transport_regression():
    """Real stdlib handler dispatch over memory streams, without a socket/server."""
    class MemoryConnection:
        def __init__(self, request):
            self.input = io.BytesIO(request)
            self.output = bytearray()
            self.timeout = None

        def makefile(self, mode, *args):
            assert mode == "rb"
            return self.input

        def settimeout(self, value):
            self.timeout = value

        def sendall(self, data):
            self.output.extend(data)

    class ProbeApplication:
        def __init__(self):
            self.calls = []
            self.reader = core.Application()

        def handle(self, target, body_supported=True):
            self.calls.append((target, body_supported))
            return self.reader.handle(target, body_supported=body_supported)

    class MemoryServer:
        pass

    routes = ("/health", "/v1/status", "/v1/redemption-preview?amount_base_units=1&minimum_lamports=0")
    rejected = 0
    for route in routes:
        for suffix in ("", " HTTP/0.9"):
            connection = MemoryConnection(("GET " + route + suffix + "\r\n\r\n").encode("ascii"))
            server = MemoryServer(); server.application = ProbeApplication()
            handler = Handler(connection, ("127.0.0.1", 0), server)
            assert handler.request_version == "HTTP/0.9" and handler.close_connection
            assert not server.application.calls and connection.output == b""
            assert connection.timeout == 2
            rejected += 1
    positive = 0
    for version in ("HTTP/1.0", "HTTP/1.1"):
        connection = MemoryConnection(("GET /health " + version + "\r\nHost: localhost\r\n\r\n").encode("ascii"))
        server = MemoryServer(); server.application = ProbeApplication()
        handler = Handler(connection, ("127.0.0.1", 0), server)
        head, body = bytes(connection.output).split(b"\r\n\r\n", 1)
        lines = head.decode("ascii").split("\r\n")
        headers = dict(line.split(": ", 1) for line in lines[1:])
        assert lines[0] == "HTTP/1.0 200 OK"
        assert headers["Content-Type"] == "application/json; charset=utf-8"
        assert headers["Content-Length"] == str(len(body))
        assert headers["Cache-Control"] == "no-store" and headers["Connection"] == "close"
        assert server.application.calls == [("/health", True)] and handler.close_connection
        assert json.loads(body)["profile_state"] == "UNCONFIGURED"
        positive += 1
    return {"legacy_rejected_before_application": rejected, "modern_header_controls": positive,
            "transport": "IN_MEMORY_STREAMS_ONLY_NO_SOCKET", "HTTP_attempts": 0}


def expect_error(code, call):
    try:
        call()
    except core.APIError as exc:
        assert exc.code == code, (code, exc.code)
    else:
        raise AssertionError("Expected " + code)


def expect_invalid(call):
    try:
        call()
    except (ValueError, KeyError, TypeError, core.APIError, struct.error):
        return
    raise AssertionError("Corruption was accepted")


def run():
    transport = transport_regression()
    raw = core.SNAPSHOT_PATH.read_bytes()
    original = json.loads(raw)
    snapshot = core.decode_snapshot(raw)
    assert snapshot.supply == 9999999994000000000
    assert snapshot.reserve == 91456644 and snapshot.maintenance == 890880
    assert snapshot.state()["backing_lamports"] == "90565764"
    assert raw == (ROOT / "evidence/m6a/supervisor/fixture_inventory/SNAPSHOT.json").read_bytes()
    with_source = json.loads((ROOT / "evidence/m6a/design/REQUIREMENTS.json").read_text())
    assert {k: {"http_status": v[0], "message": v[1]} for k, v in core.ERRORS.items()} == with_source["application_errors"]

    # Each corruption changes a single material relationship or semantic field.
    mutations = []
    def changed(path, value):
        obj = copy.deepcopy(original)
        parent = obj
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]] = value
        mutations.append(obj)
    changed(["schema"], "other")
    changed(["profile"], "TESTNET")
    changed(["public_cluster"], "testnet")
    changed(["current_network_data"], True)
    changed(["snapshot_id"], "other")
    changed(["provenance", "transaction_sha256"], "0" * 64)
    changed(["provenance", "event_index_zero_based"], "23")
    changed(["accounts", "mint", "owner"], core.t.TUPLE["system"]["base58"])
    changed(["accounts", "config", "address"], core.t.TUPLE["mint"]["base58"])
    changed(["accounts", "reserve", "executable"], True)
    changed(["accounts", "reserve", "lamports"], 91456645)
    changed(["accounts", "reserve", "lamports"], True)
    changed(["accounts", "config", "bytes"], 174)
    changed(["accounts", "mint", "data_sha256"], "0" * 64)
    changed(["accounts", "mint", "data_hex"], "00")
    changed(["runtime_getters", "clock", "epoch"], 10)
    changed(["runtime_getters", "clock", "epoch"], 9.0)
    changed(["runtime_getters", "rent", "minimum_balances", "0"], 890881)
    changed(["runtime_getters", "rent", "exemption_threshold"], 2)
    changed(["runtime_getters", "rent", "exemption_threshold"], 2.1)
    changed(["runtime_getters", "rent", "burn_percent"], 49)
    changed(["runtime_getters", "rent", "minimum_balances", "0"], 890880.0)
    removed = copy.deepcopy(original); del removed["accounts"]["runtime_rent"]; mutations.append(removed)
    extra = copy.deepcopy(original); extra["caller_state"] = {}; mutations.append(extra)
    for obj in mutations:
        expect_invalid(lambda obj=obj: core.decode_envelope(obj))
        expect_invalid(lambda obj=obj: core.decode_snapshot(json.dumps(obj).encode()))
    for rawbad in (b"", raw[:-1], raw + b" ", raw.replace(b'"after"', b'"other"')):
        expect_invalid(lambda rawbad=rawbad: core.decode_snapshot(rawbad))
    for invalid_json in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff'):
        expect_invalid(lambda invalid_json=invalid_json: core.strict_json(invalid_json))

    mint = bytes.fromhex(original["accounts"]["mint"]["data_hex"])
    mint_negatives = []
    for offset, value in ((0, 2), (0, 1), (46, 1), (44, 8), (45, 0), (82, 1),
                          (165, 2), (166, 2), (168, 107), (170, 1), (202, 0),
                          (234, 1), (242, 8), (258, 1), (260, 10), (276, 0)):
        data = bytearray(mint); data[offset] = value; mint_negatives.append(bytes(data))
    mint_negatives += [mint[:-1], mint + bytes(4)]
    data = bytearray(mint); data[36:44] = (10**19 + 1).to_bytes(8, "little"); mint_negatives.append(bytes(data))
    for data in mint_negatives:
        expect_invalid(lambda data=data: core.decode_mint(data))
    # Native inactive-payload semantics, not a new trusted envelope.
    inactive = bytearray(mint); inactive[4:36] = bytes(range(32)); inactive[50:82] = bytes(range(32))
    assert core.decode_mint(bytes(inactive)) == snapshot.supply
    assert core.coption_pubkey(bytes(4) + bytes([255]) * 32) is None
    assert core.coption_pubkey(b"\x01\x00\x00\x00" + bytes([255]) * 32) == bytes([255]) * 32

    # Decoder digest/semantic gating and per-request fail-closed cached state.
    app = core.Application("local-historical")
    assert app.handle("/v1/status")[1]["ready"]
    for failure in (b"changed", None):
        kwargs = {"return_value": failure} if failure is not None else {"side_effect": FileNotFoundError()}
        with patch.object(core, "read_snapshot_bytes", **kwargs):
            for route in ("/v1/status", "/v1/redemption-preview?amount_base_units=1&minimum_lamports=0"):
                status, body = app.handle(route)
                assert status == 503 and body["error"]["code"] == "SNAPSHOT_INVALID"
                assert body["snapshot_id"] is None and "payout_lamports" not in body and "state" not in body
            status, body = app.handle("/health")
            assert status == 200 and body["profile_state"] == "INVALID" and not body["ready"]
    assert app.handle("/v1/status")[1]["ready"]

    query_negatives = [
        ("/", "NOT_FOUND"), ("https://example.invalid/health", "INVALID_REQUEST"),
        ("//health", "INVALID_REQUEST"), ("/he%61lth", "INVALID_REQUEST"),
        ("/health#x", "INVALID_REQUEST"), ("/health+x", "INVALID_REQUEST"),
        ("/health\\x", "INVALID_REQUEST"), ("/héalth", "INVALID_REQUEST"),
        ("/health?", "INVALID_QUERY"), ("/v1/status?a=1", "INVALID_QUERY"),
        ("/v1/redemption-preview", "INVALID_QUERY"), ("/" + "a" * 1024, "REQUEST_TOO_LARGE"),
        ("/v1/redemption-preview?" + "x" * 129, "REQUEST_TOO_LARGE"),
    ]
    prefix = "/v1/redemption-preview?"
    for value in ("", "00", "01", "-1", "1.0", "1e2", " 1", "١", "1=2"):
        query_negatives.append((prefix + "amount_base_units=" + value + "&minimum_lamports=0", "INVALID_QUERY" if value not in (" 1", "١") else "INVALID_REQUEST"))
    for tail in ("amount_base_units=1", "amount_base_units=1&minimum_lamports=0&x=1",
                 "amount_base_units=1&amount_base_units=1&minimum_lamports=0",
                 "minimum_lamports=0&", "amount_base_units=1&minimum_lamports=0&"):
        query_negatives.append((prefix + tail, "INVALID_QUERY"))
    for value in (str(2**64), "1" * 21):
        query_negatives.append((prefix + "amount_base_units=" + value + "&minimum_lamports=0", "INTEGER_OUT_OF_RANGE"))
    for target, code in query_negatives:
        expect_error(code, lambda target=target: core.parse_target(target))
    for value in ("0", "1", "9007199254740993", str(core.U64_MAX)):
        assert core.canonical_integer(value) == int(value)
    assert core.parse_target(prefix + "minimum_lamports=1&amount_base_units=110417000337")[1] == (110417000337, 1)

    # Fixed, independently supplied semantic oracle (31 cases), never native profiles.
    oracle_path = ROOT / "evidence/m6a/supervisor/oracle_design/EXPECTED_CASES.json"
    oracle = json.loads(oracle_path.read_text())
    for case in oracle["cases"]:
        vals = case["inputs"]; expected = case["expected"]
        args = [int(vals[k]) for k in ("supply_base_units", "reserve_lamports", "maintenance_lamports", "amount_base_units", "minimum_lamports")]
        reason = expected["semantic_reason"]
        if reason == "H_PROFILE_SUPPLY_BOUND_REJECT":
            data = bytearray(mint); data[36:44] = args[0].to_bytes(8, "little")
            expect_invalid(lambda: core.decode_mint(bytes(data)))
        elif reason == "ARITHMETIC_ELIGIBLE":
            out = core.preview(*args)
            assert out["payout_lamports"] == expected["mathematical_floor_lamports"]
            assert out["division_remainder"] == expected["division_remainder"]
        else:
            code = "INTEGER_OUT_OF_RANGE" if reason == "UNSIGNED_U64_DOMAIN_REJECT" else reason
            expect_error(code, lambda args=args: core.preview(*args))

    # Constructive valid arithmetic domains; no filtering, native-state claim or shrinking.
    rng = random.Random(0x6A20261109)
    generated_rows = []
    for index in range(256):
        supply = [1, 3, 2**53 + 1, 10**19, core.U64_MAX][index % 5] if index < 25 else rng.randrange(1, 2**64)
        reserve = rng.randrange(1, 2**64)
        maintenance = rng.randrange(reserve)  # Construct positive backing.
        backing = reserve - maintenance
        threshold = (supply + backing - 1) // backing
        amount = rng.randrange(threshold, supply + 1)  # Construct a positive payout.
        rational = Fraction(backing) * Fraction(amount, supply)
        floor = math.floor(rational)
        minimum = rng.randrange(floor + 1)
        out = core.preview(supply, reserve, maintenance, amount, minimum)
        payout, rem = int(out["payout_lamports"]), int(out["division_remainder"])
        assert payout == math.floor(rational) and all(type(v) is str for v in out.values())
        assert payout * supply <= backing * amount < (payout + 1) * supply
        assert 0 <= rem < supply and payout * supply + rem == backing * amount
        assert (backing - payout) * supply >= backing * (supply - amount)
        full = core.preview(supply, reserve, maintenance, supply, backing)
        assert int(full["payout_lamports"]) == backing and full["division_remainder"] == "0"
        later = rng.randrange(amount, supply + 1)
        assert int(core.preview(supply, reserve, maintenance, later, 0)["payout_lamports"]) >= payout
        if floor < core.U64_MAX:
            expect_error("MINIMUM_NOT_MET", lambda: core.preview(supply, reserve, maintenance, amount, floor + 1))
        generated_rows.append([supply, reserve, maintenance, amount, minimum, payout, rem])
    for args, code in (((0, 1, 0, 1, 0), "ZERO_SUPPLY"), ((1, 1, 0, 0, 0), "INVALID_AMOUNT"),
                       ((1, 1, 0, 2, 0), "AMOUNT_EXCEEDS_SUPPLY"), ((1, 0, 1, 1, 0), "ZERO_PAYOUT"),
                       ((1, 1, 1, 1, 0), "ZERO_PAYOUT")):
        expect_error(code, lambda args=args: core.preview(*args))
    for invalid in (-1, 2**64, True, 1.0, "1"):
        for offset in range(5):
            args = [1, 1, 0, 1, 0]; args[offset] = invalid
            expect_error("INTEGER_OUT_OF_RANGE", lambda args=args: core.preview(*args))
    assert core.preview(core.U64_MAX, core.U64_MAX, 0, core.U64_MAX, 0)["payout_lamports"] == str(core.U64_MAX)
    return {"status": "OFFLINE_CHECKS_PASS", "constructive_cases": len(generated_rows),
            "generated_seed_hex": "6a20261109", "generated_rows_sha256": hashlib.sha256(json.dumps(generated_rows, separators=(",", ":")).encode()).hexdigest(),
            "semantic_oracle_cases": len(oracle["cases"]), "oracle_sha256": hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
            "envelope_corruptions": len(mutations), "mint_corruptions": len(mint_negatives),
            "query_rejections": len(query_negatives), "HTTP_attempts": 0,
            "transport_regression": transport,
            "limits": "Finite deterministic coverage; no shrinking, exhaustiveness, native execution or authority proof."}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
