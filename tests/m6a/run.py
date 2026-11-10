"""Retained offline/loopback verification with prospective attempt accounting."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import traceback

from campaign import Ledger, now, write_json, run as run_http
from offline import run as run_offline

ROOT = Path(__file__).resolve().parents[2]


def source_files():
    paths = list((ROOT / "api/htfp_readonly").rglob("*"))
    paths += list((ROOT / "tests/m6a").rglob("*")) + [ROOT / "api/README.md"]
    return sorted(path for path in paths if path.is_file())


def manifest(paths):
    return {str(path.relative_to(ROOT)): {"bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths}


def preflight():
    expected = {
        "evidence/M6A_STAGE_B_HANDOFF.json": "2dd9ddf37c7de9c40a14313059ff8c237e46c6e166d1c9b9745a968492aed3d2",
        "evidence/m6a/design/CONTRACT.md": "5eb275a5900038eb2e529c7b8ee63d270f4caed393f33870312e663aca62610b",
        "evidence/m6a/design/REQUIREMENTS.json": "b1269a95355ce9a1edf1241c1bf87ba750913fb12b5055494eeae485ead88274",
        "evidence/m6a/design/SNAPSHOT_PROFILE.json": "804b91c9763aeeeb98cdb771a6c40d2ec556b5e7796d8d0f127b0c820bb3b640",
        "evidence/m6a/design/HANDOFF.json": "ec4a83bd6e9fce494361df619f3d0e7237b56c807bf692c5fbbb2866fd931cfb",
        "evidence/m6a/supervisor/fixture_inventory/SNAPSHOT.json": "49b81e98caf11a51c7c93b66e9829ba4da4e661a8cf99ca98dfbfc8e5d90840d",
        "evidence/m6a/supervisor/fixture_inventory/extract_snapshot.py": "cf673dcf932a248b82a83826d8ec168d5acd1011b5d21537a14bac48a2e1b020",
    }
    profile = json.loads((ROOT / "evidence/m6a/design/SNAPSHOT_PROFILE.json").read_text())
    p = profile["snapshot"]["provenance"]
    expected[p["trace_path"]] = p["stored_sha256"]
    expected[p["H_artifact_path"]] = p["H_artifact_sha256"]
    expected.update(p["H_source_sha256"])
    verified = {}
    for name, digest in expected.items():
        raw = (ROOT / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest, name
        verified[name] = {"bytes": len(raw), "sha256": digest}
    with gzip.open(ROOT / p["trace_path"], "rb") as stream:
        decoded = stream.read()
    assert hashlib.sha256(decoded).hexdigest() == p["decoded_sha256"] and len(decoded) == int(p["decoded_bytes"])
    assert (ROOT / "api/htfp_readonly/data/snapshot.json").read_bytes() == (ROOT / "evidence/m6a/supervisor/fixture_inventory/SNAPSHOT.json").read_bytes()
    usage = resources()
    assert usage["API_tests_fixtures_bytes"] <= 1048576 and usage["author_evidence_bytes"] <= 3145728
    assert usage["all_m6a_bytes"] <= 8388608 and usage["free_bytes"] >= 2147483648
    return {"status": "BOUND_ORIGINAL_BYTES_VERIFIED", "files": verified,
            "decoded_original_trace_sha256": p["decoded_sha256"], "resource_preflight": usage,
            "not_claimed": "No native program is loaded; hashes do not establish present public deployment or network equivalence."}


def resources():
    def size(paths):
        return sum(path.stat().st_size for path in paths if path.is_file())
    return {"API_tests_fixtures_bytes": size(source_files()),
            "author_evidence_bytes": size((ROOT / "evidence/m6a/author").rglob("*")),
            "all_m6a_bytes": size((ROOT / "evidence/m6a").rglob("*")) + size(source_files()),
            "free_bytes": shutil.disk_usage(ROOT).free}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--role", choices=("author", "supervisor"), default="author")
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args()
    assert sys.version_info[:2] == (3, 12), "Python3.12 required"
    assert sys.dont_write_bytecode, "Use python3 -B"
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.run_id)
    base = ROOT / "evidence/m6a" / ("author" if args.role == "author" else "supervisor/api_reproduction")
    base.mkdir(parents=True, exist_ok=True)
    for previous in (ROOT / "evidence/m6a").rglob("RESULT.json"):
        prior = json.loads(previous.read_text())
        assert prior.get("status") != "RUNNING_UNFINALIZED", "Unfinalized run: " + str(previous)
    evidence = base / args.run_id
    evidence.mkdir(exist_ok=False)
    initial = manifest(source_files())
    for name in initial:
        destination = evidence / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    write_json(evidence / "INPUTS.json", {"UTC": now(), "command": sys.argv,
                                         "sources": initial, "offline_only": args.offline_only,
                                         "role": args.role, "native_VMs": 0, "native_sends": 0})
    result = {"status": "RUNNING_UNFINALIZED", "UTC_started": now(), "stage_acceptance": False,
              "native_VMs": 0, "native_sends": 0, "HTTP_attempted": 0}
    write_json(evidence / "RESULT.json", result)
    ledger = None
    success = False
    try:
        result["preflight"] = preflight()
        result["offline"] = run_offline()
        if not args.offline_only:
            ledger = Ledger(base, args.run_id, args.role)
            ledger.begin()
            result["loopback"] = run_http(ledger)
        assert manifest(source_files()) == initial, "Source changed during verification"
        usage = resources()
        assert usage["API_tests_fixtures_bytes"] <= 1048576 and usage["author_evidence_bytes"] <= 3145728
        assert usage["all_m6a_bytes"] <= 8388608 and usage["free_bytes"] >= 2147483648
        result["resource_before_finalization"] = usage
        success = True
    except BaseException as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        result["status"] = "AUTHOR_CHECKS_PASS" if success else "AUTHOR_CHECKS_FAIL"
        if ledger:
            ledger.finish(result["status"])
            result["HTTP_attempted"] = ledger.attempted
            result["HTTP_completed"] = ledger.completed
            result["HTTP_server_seen"] = ledger.server_seen
            result["cumulative_role_attempts"] = ledger.prior_role + ledger.attempted
            result["cumulative_global_attempts"] = ledger.prior_global + ledger.attempted
            write_json(evidence / "HTTP.json", ledger.rows)
        result["sources_after"] = manifest(source_files())
        result["UTC_finished"] = now()
        result["limitations"] = "Author checks only, finite cases, no native/runtime/authorization/public data/production acceptance; root reproduction and exact independent Review pending."
        write_json(evidence / "RESULT.json", result)
    print(json.dumps({"status": result["status"], "path": str(evidence.relative_to(ROOT)),
                      "HTTP_attempted": result["HTTP_attempted"], "failure": result.get("failure")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
