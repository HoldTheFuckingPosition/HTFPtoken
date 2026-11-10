"""Counted actual-CLI finite verification; never imports the product."""

import argparse
import base64
import copy
from fractions import Fraction
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import traceback

from ledger import Journal, utc

ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "evidence/m6b/design/revision-001"
ORACLE = ROOT / "evidence/m6b/supervisor/oracle/revision-001/EXPECTED_CASES.json"


def encode(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, obj):
    path.write_bytes((json.dumps(obj, indent=2, sort_keys=True) + "\n").encode())


def sources():
    return sorted(p for base in ("tools/htfp_launch_manifest", "tests/m6b") for p in (ROOT / base).rglob("*") if p.is_file())


def manifest(paths):
    return {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in paths}


def preflight(requirements):
    pins = {**requirements["source_bindings"],
        "evidence/M6B_STAGE_B_HANDOFF.json": {"sha256": "24a0bbe11be7989a32139450687a96821bf3c0e4bd6cc25e33e6d4d62ce393d6"},
        "evidence/m6b/design/revision-001/CONTRACT.md": {"sha256": "a782f48a27e2b8a1e4e10aeac1ec1aa3b0b5b1d0b5f3ff08d7a32a81b8b790bb"},
        "evidence/m6b/design/revision-001/REQUIREMENTS.json": {"sha256": "b3e4c89de4be1923527b51ca437f2274d7f73c11fe02a362c9fbdf098d49e3f9"},
        "evidence/m6b/design/revision-001/EXAMPLE.json": {"sha256": "de9b32af6ed24277af35ed1da23633e520382bda5fac07c9dbd01534e806a5bd"},
        "evidence/m6b/design/revision-001/HANDOFF.json": {"sha256": "7b8e78529f63de4db9cc93f219e2e41c7916f5a18adc84b0b6ca27ab061d1eb0"},
        str(ORACLE.relative_to(ROOT)): {"sha256": "1852ce93d887e566797274c02c2c5b4e84b93bce2f2c05a344b50681f10ffdf6"}}
    for name, pin in pins.items():
        raw = (ROOT / name).read_bytes()
        assert sha(raw) == pin["sha256"], name
        assert "bytes" not in pin or len(raw) == pin["bytes"], name
    return {"bound_files": len(pins), "all_source_pins_match": True}


def make_cases(requirements, oracle):
    cases = []
    for case in oracle["cases"]:
        raw = (ROOT / case["input_file"]).read_bytes() if case["input_bytes_kind"] == "PINNED_FILE_BYTES" else encode(case["input"])
        assert len(raw) == case["input_bytes"] and sha(raw) == case["expected"]["input_sha256"]
        cases.append({"id": "oracle-" + case["id"], "raw": raw, "oracle": case["expected"], "input": case["input"]})
    for path, rule in sorted(requirements["fixed_policy_checks"].items()):
        group, key = path.split(".")
        value = rule["expected"]
        if type(value) is bool:
            wrong = not value
        elif requirements["grammar"]["optional_groups"][group][key] == "pubkey":
            wrong = "11111111111111111111111111111111"
        elif value.isascii() and value.isdecimal():
            number = int(value); wrong = str(number - 1 if number == 2**64 - 1 else number + 1)
        else:
            wrong = "OTHER"
        obj = {"schema": "HTFP_LAUNCH_DOSSIER_V1", group: {key: wrong}}
        cases.append({"id": "fixed-" + path, "raw": encode(obj), "input": obj, "fixed_path": path})
    def raw_case(name, raw, error=None, path="$", positive=False):
        cases.append({"id": name, "raw": raw, "error": error, "error_path": path, "positive": positive})
    def obj_case(name, group, fields, error=None, path="$", positive=False):
        obj = {"schema": "HTFP_LAUNCH_DOSSIER_V1", group: fields}
        cases.append({"id": name, "raw": encode(obj), "input": obj, "error": error, "error_path": path, "positive": positive})
    for name, args in (("usage-empty", []), ("usage-help", ["--help"]), ("usage-extra", ["a", "b"])):
        cases.append({"id": name, "args": args, "error": "CLI_USAGE", "error_path": "$", "null_digest": True})
    for name, special in (("io-missing", "missing"), ("io-directory", "directory"), ("io-device", "device"), ("io-pipe-nonblocking", "pipe")):
        cases.append({"id": name, "special": special, "error": "INPUT_UNREADABLE", "error_path": "$", "null_digest": True})
    raw_case("oversize", b" " * 65537, "INPUT_TOO_LARGE"); cases[-1]["null_digest"] = True
    raw_case("invalid-utf8", b"\xff", "INVALID_UTF8")
    raw_case("utf8-bom", b"\xef\xbb\xbf{}", "INVALID_JSON")
    raw_case("invalid-json", b"{", "INVALID_JSON")
    raw_case("duplicate-key", b'{"schema":"HTFP_LAUNCH_DOSSIER_V1","schema":"HTFP_LAUNCH_DOSSIER_V1"}', "DUPLICATE_KEY")
    raw_case("nonfinite-nan", b'{"x":NaN}', "NONFINITE_JSON")
    raw_case("nonfinite-infinity", b'{"x":Infinity}', "NONFINITE_JSON")
    raw_case("float-literal", b'{"x":1e0}', "JSON_NUMBER_NOT_ALLOWED")
    raw_case("depth", b'[[[[[null]]]]]', "NESTING_LIMIT")
    obj_case("assertion-limit", "assertions", [{"subject": "x", "claim": "x"}] * 17, "COLLECTION_LIMIT")
    raw_case("wrong-schema", encode({"schema": "OTHER"}), "SCHEMA_MISMATCH", "schema")
    obj_case("unknown-root", "surprise", True, "UNKNOWN_FIELD")
    obj_case("wrong-group-type", "identity", [], "TYPE_MISMATCH", "identity")
    obj_case("leading-zero", "funding", {"raised_lamports": "01"}, "INVALID_INTEGER", "funding.raised_lamports")
    obj_case("u64-overflow", "funding", {"raised_lamports": str(2**64)}, "INTEGER_OUT_OF_RANGE", "funding.raised_lamports")
    obj_case("fraction-zero-denominator", "volume", {"alpha": {"numerator": "1", "denominator": "0"}}, "INVALID_FRACTION", "volume.alpha")
    obj_case("invalid-pubkey", "identity", {"mint": "0" * 32}, "INVALID_PUBKEY", "identity.mint")
    obj_case("invalid-hash", "identity", {"genesis_sha256": "A" * 64}, "INVALID_SHA256", "identity.genesis_sha256")
    obj_case("text-control", "identity", {"metadata_reference": "line\nline"}, "INVALID_TEXT", "identity.metadata_reference")
    obj_case("surrogate", "identity", {"metadata_reference": "\ud800"}, "INVALID_TEXT")
    obj_case("valid-surrogate-pair", "identity", {"metadata_reference": "\U0001f680"}, positive=True)
    minimal = encode({"schema": "HTFP_LAUNCH_DOSSIER_V1"})
    raw_case("exact-input-limit", minimal + b" " * (65536 - len(minimal)), positive=True)
    obj_case("exact-text-limit", "identity", {"metadata_reference": "x" * 512}, positive=True)
    obj_case("exact-assertion-limit", "assertions", [{"subject": "x", "claim": "approved", "claimed_status": "verified"}] * 16, positive=True)
    obj_case("missing-assertion-required", "assertions", [{"subject": "x"}], "TYPE_MISMATCH", "assertions[0]")
    obj_case("missing-fraction-required", "volume", {"alpha": {"numerator": "1"}}, "TYPE_MISMATCH", "volume.alpha")
    obj_case("negative-u64", "funding", {"raised_lamports": "-1"}, "INVALID_INTEGER", "funding.raised_lamports")
    rng = random.Random(0x6B20261109)
    for index in range(20):
        n = (0, 1, 2**53 + 1, 2**64 - 1)[index] if index < 4 else rng.randrange(2**64)
        pool = int(Fraction(4 * n, 5)); reserve = n - pool
        short = 1 if index % 3 != 2 else 0
        nonpool = 6500000000000000000 - short
        cuts = sorted((0, rng.randrange(nonpool + 1), rng.randrange(nonpool + 1), nonpool))
        remaining = [cuts[j + 1] - cuts[j] for j in range(3)]
        complete = index % 3 != 0
        capacity = rng.randrange(2**64); credit = rng.randrange(capacity + 1)
        obj = {"schema": "HTFP_LAUNCH_DOSSIER_V1",
               "allocation": {"complete": complete, "pool_base_units": "3500000000000000000",
                              **{key + "_base_units": str(value) for key, value in zip(("lge", "team", "marketing"), remaining)}},
               "funding": {"raised_lamports": str(n), "pool_lamports": str(pool), "reserve_lamports": str(reserve)},
               "volume": {"alpha": {"numerator": str(index + 2), "denominator": "1"}, "capacity_gross_base_units": str(capacity),
                          "initial_credit_gross_base_units": str(credit), "refill_gross_base_units_per_second": {"numerator": "0", "denominator": "1"}}}
        cases.append({"id": "generated-" + str(index), "raw": encode(obj), "input": obj,
                      "generated": {"n": n, "short": short, "complete": complete}})
    assert len(cases) <= 128 and len({c["id"] for c in cases}) == len(cases)
    return cases


def check_common(report, case, r, oracle):
    assert set(report) == set(r["report"]["keys"])
    assert report["policy_sources"] == oracle["common_policy_sources_exact"]
    for key, value in r["report"]["fixed"].items():
        assert report[key] == value, key
    expected_hash = None if case.get("null_digest") else sha(case["raw"])
    assert report["input_sha256"] == expected_hash
    if report["outcome"] == "INPUT_INVALID":
        for key in ("checks", "contradictions", "open_items", "unverified_assertions"):
            assert report[key] == []
        assert report["derived"] == {}
        assert set(report["error"]) == {"code", "path", "message"}
        assert report["error"]["message"] == r["input_errors"][report["error"]["code"]]
        return
    assert report["error"] is None
    obj = case.get("input") or json.loads(case["raw"])
    assert len(report["checks"]) == 38
    expected_fixed = []
    for path, rule in sorted(r["fixed_policy_checks"].items()):
        group, key = path.split("."); value = (obj.get(group) or {}).get(key)
        result = "MISSING" if value is None else "MATCH" if value == rule["expected"] else "CONTRADICTION"
        expected_fixed.append({"rule_id": path, "path": path, "result": result})
    assert report["checks"][:31] == expected_fixed
    assert [{k: row[k] for k in ("rule_id", "path")} for row in report["checks"][31:]] == oracle["common_relationship_check_tail_id_path_order_exact"]
    for key in ("contradictions", "open_items"):
        assert report[key] == sorted(report[key], key=lambda f: (f["path"], f["code"]))
    for key in ("contradictions", "open_items", "unverified_assertions"):
        for finding in report[key]:
            assert set(finding) == {"code", "path", "source_ids", "message"}
            assert finding["message"] == r["finding_catalog"][finding["code"]]
    assert report["unverified_assertions"][:7] == oracle["common_unverified_external_prefix_exact"]
    expected_leaves = []
    for group, fields in r["grammar"]["optional_groups"].items():
        section = obj.get(group) or {}
        for field in fields:
            path = group + "." + field
            value = section.get(field)
            code = "MISSING_INPUT" if value is None else "OPEN_CHOICE" if path in r["open_choice_paths"] else "PROVISIONAL_CHOICE" if path in r["provisional_choice_paths"] else None
            if code:
                expected_leaves.append({"code": code, "path": path, "source_ids": r["group_source_ids"][group], "message": r["finding_catalog"][code]})
    actual_leaves = [f for f in report["open_items"] if f["code"] in ("MISSING_INPUT", "OPEN_CHOICE", "PROVISIONAL_CHOICE")]
    assert actual_leaves == sorted(expected_leaves, key=lambda f: (f["path"], f["code"]))
    asserted = obj.get("assertions") or []
    assert report["unverified_assertions"][7:] == [{"code": "ATTRIBUTED_ASSERTION_UNVERIFIED", "path": "assertions[" + str(i) + "]",
               "source_ids": ["S98", "S99"], "message": r["finding_catalog"]["ATTRIBUTED_ASSERTION_UNVERIFIED"]} for i in range(len(asserted))]


def check_case(report, exit_code, case, r, oracle):
    check_common(report, case, r, oracle)
    assert exit_code == r["report"]["outcomes"][report["outcome"]]
    if "oracle" in case:
        expected = case["oracle"]
        for key in ("outcome", "input_sha256", "error"):
            assert report[key] == expected[key], (case["id"], key, report[key], expected[key])
        assert exit_code == expected["exit_code"]
        assert report["contradictions"] == expected["contradictions_exact"]
        assert report["derived"] == expected["derived_exact"], (case["id"], report["derived"], expected["derived_exact"])
        for finding in expected["required_open_items_subset"]:
            assert finding in report["open_items"]
        for check in expected["required_checks_subset"]:
            assert check in report["checks"]
        assert str(len(report["unverified_assertions"])) == expected["unverified_assertions_expected"]["total_count"]
    elif "fixed_path" in case:
        path = case["fixed_path"]
        assert report["contradictions"] == [{"code": "POLICY_MISMATCH", "path": path,
             "source_ids": r["fixed_policy_checks"][path]["source_ids"], "message": r["finding_catalog"]["POLICY_MISMATCH"]}]
    elif case.get("error"):
        assert exit_code == 2 and report["error"]["code"] == case["error"]
        assert report["error"]["path"] == case["error_path"], case["id"]
    elif case.get("positive"):
        assert exit_code == 0 and report["error"] is None
    elif "generated" in case:
        data, derived = case["generated"], report["derived"]
        for name, fraction in (("pool", Fraction(4 * data["n"], 5)), ("reserve", Fraction(data["n"], 5))):
            actual = derived["funding_expected_" + name + "_lamports"]
            assert Fraction(int(actual["numerator"]), int(actual["denominator"])) == fraction
        assert int(derived["funding_sum_lamports"]) == data["n"]
        assert int(derived["funding_pool_difference_numerator"]) + int(derived["funding_reserve_difference_numerator"]) == 0
        assert -4 <= int(derived["funding_pool_difference_numerator"]) <= 0
        assert int(derived["allocation_known_sum_base_units"]) + int(derived["allocation_unallocated_from_provided_base_units"]) == 10**19
        codes = [f["code"] for f in report["contradictions"]]
        assert codes == (["COMPLETED_ALLOCATION_SHORTFALL"] if data["short"] and data["complete"] else [])
        assert any(f["code"] == "ROUNDING_UNRESOLVED" for f in report["open_items"]) == bool(data["n"] % 5)


def resources():
    def size(base):
        return sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
    return {"author_source_tests_evidence_bytes": sum(p.stat().st_size for p in sources()) + size(ROOT / "evidence/m6b/author"),
            "all_M6B_bytes": sum(p.stat().st_size for p in sources()) + size(ROOT / "evidence/m6b"), "free_bytes": shutil.disk_usage(ROOT).free}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--role", choices=("author", "supervisor"), default="author")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12) or not sys.dont_write_bytecode or sys.flags.optimize:
        raise RuntimeError("Use Python3.12 -B without optimization")
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.run_id):
        raise ValueError("Use a simple unique run ID")
    base = ROOT / "evidence/m6b" / ("author" if args.role == "author" else "supervisor/reproduction")
    base.mkdir(parents=True, exist_ok=True)
    for previous in (ROOT / "evidence/m6b").rglob("RESULT.json"):
        if json.loads(previous.read_text()).get("status") == "RUNNING_UNFINALIZED":
            raise RuntimeError("Orphaned result blocks further target calls: " + str(previous))
    evidence = base / args.run_id; evidence.mkdir(exist_ok=False)
    initial = manifest(sources())
    for name in initial:
        destination = evidence / "source" / name; destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    r = json.loads((DESIGN / "REQUIREMENTS.json").read_text()); oracle = json.loads(ORACLE.read_text())
    cases = make_cases(r, oracle)
    write(evidence / "INPUTS.json", {"UTC": utc(), "command": sys.argv, "source_manifest": initial,
                                    "planned_cases": [c["id"] for c in cases], "oracle_sha256": sha(ORACLE.read_bytes())})
    result = {"status": "RUNNING_UNFINALIZED", "stage_acceptance": False, "UTC_started": utc(), "planned": len(cases)}
    write(evidence / "RESULT.json", result)
    journal, records, success = None, [], False
    try:
        result["preflight"] = preflight(r)
        current_usage = resources()
        assert current_usage["author_source_tests_evidence_bytes"] <= 1572864 and current_usage["all_M6B_bytes"] <= 4194304 and current_usage["free_bytes"] >= 2147483648
        journal = Journal(base, args.run_id, args.role, ROOT / "evidence/m6b")
        journal.begin(source_manifest_sha256=sha(encode(initial)), planned=len(cases))
        input_dir = evidence / "inputs"; input_dir.mkdir()
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT / "tools"))
        for case in cases:
            raw = case.get("raw")
            if raw is not None:
                input_path = input_dir / (case["id"] + ".json"); input_path.write_bytes(raw)
                arguments = [str(input_path)]
            elif "args" in case:
                arguments = case["args"]
            else:
                special = case["special"]
                arguments = [str(input_dir / "not-present.json") if special == "missing" else str(input_dir) if special == "directory" else "/dev/null" if special == "device" else "/proc/self/fd/0"]
            command = [sys.executable, "-B", "-m", "htfp_launch_manifest", *arguments]
            attempt = journal.start_case(case["id"], input_sha256=sha(raw) if raw is not None else None, command=command)
            record = {"case_id": case["id"], "attempt": attempt, "command": command,
                      "input_base64": base64.b64encode(raw).decode() if raw is not None else None}
            completed = False
            try:
                child = subprocess.run(command, input=b"", capture_output=True, env=environment, cwd=ROOT, timeout=5)
                completed = True
                record.update(exit_code=child.returncode, stdout_base64=base64.b64encode(child.stdout).decode(),
                              stderr_base64=base64.b64encode(child.stderr).decode(), stdout_sha256=sha(child.stdout), stderr_sha256=sha(child.stderr))
                assert child.stderr == b"", child.stderr
                assert len(child.stdout) <= 131072
                report = json.loads(child.stdout)
                assert child.stdout == encode(report), "Report serialization is not deterministic canonical JSON+LF"
                check_case(report, child.returncode, case, r, oracle)
                record["assertions"] = "PASS"
            except BaseException as exc:
                record["assertions"] = "FAIL"
                record["exception"] = type(exc).__name__ + ": " + str(exc)
                raise
            finally:
                records.append(record)
                journal.finish_case(attempt, completed=completed, exit_code=record.get("exit_code"),
                                    stdout_sha256=record.get("stdout_sha256"), assertions=record["assertions"])
        assert manifest(sources()) == initial, "Source race during verification"
        assert len(records) == len(cases)
        success = True
    except BaseException as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        encoded = encode(records); compressed = gzip.compress(encoded, mtime=0)
        (evidence / "records.json.gz").write_bytes(compressed)
        result["records"] = {"path": str((evidence / "records.json.gz").relative_to(ROOT)), "stored_bytes": len(compressed), "stored_sha256": sha(compressed),
                             "decoded_bytes": len(encoded), "decoded_sha256": sha(encoded), "record_count": len(records)}
        usage = resources(); result["resources_before_result"] = usage
        if usage["author_source_tests_evidence_bytes"] > 1572864 or usage["all_M6B_bytes"] > 4194304 or usage["free_bytes"] < 2147483648:
            success = False; result["resource_failure"] = True
        result["status"] = "AUTHOR_CHECKS_PASS" if success else "AUTHOR_CHECKS_FAIL"
        if journal is not None and journal.started:
            journal.finalize(result["status"], record_count=len(records))
        result.update(UTC_finished=utc(), attempted=journal.attempted if journal else 0,
                      completed=journal.completed if journal else 0, cumulative_role=(journal.prior_role + journal.attempted) if journal else 0,
                      source_manifest_after=manifest(sources()), new_HTTP=0, new_native_VMs=0, new_native_sends=0,
                      limitations="Finite CLI/documentary checks only; no shrinking/exhaustive/native/public/authorization/readiness acceptance. Root reproduction and exact Review pending.")
        write(evidence / "RESULT.json", result)
    print(json.dumps({"status": result["status"], "path": str(evidence.relative_to(ROOT)), "attempted": result["attempted"], "failure": result.get("failure")}, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
