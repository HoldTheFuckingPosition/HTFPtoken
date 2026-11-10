"""Exactly three prospectively counted CLI calls after the independent seal."""

import argparse
import base64
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
AUTHOR = ROOT / "evidence/m6b/author/correction-001"
ORACLE_DIR = ROOT / "evidence/m6b/supervisor/supplement_oracle"
LEDGER_PATH = ROOT / "tests/m6b/ledger.py"
LEDGER_SHA = "fbd7f033d91d6ca88146a07ccc1a011cbc6e8f32053fe3c343dae697f9c6d676"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def meta(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha(data)}


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_inputs():
    seal_path = ORACLE_DIR / "HANDOFF.json"
    if not seal_path.is_file():
        raise RuntimeError("Independent oracle seal is not present; no target call is authorized yet")
    assert sha(seal_path.read_bytes()) == "25b82c71d3135b10da064a5b6f19e345314fe14eb1415a6c0029d0286cf2dbc7"
    seal = json.loads(seal_path.read_text())
    assert seal["writes_stopped_after_handoff"] is True
    for name, expected in seal["files"].items():
        assert meta(ROOT / name) == expected, name
    data_path = ORACLE_DIR / "EXPECTED_CASES.json"
    assert sha(data_path.read_bytes()) == "bcf38e5d31059eaa5883fea813b3d0d85f6943d5ebdba5711f61afa64334f27f"
    oracle = json.loads(data_path.read_text())
    expected_ids = ["SUP_LP_EQ_2_2", "SUP_LP_NE_1_2", "SUP_CREDIT_8_GT_7"]
    assert [case["id"] for case in oracle["cases"]] == expected_ids
    expected_objects = [
        {"schema": "HTFP_LAUNCH_DOSSIER_V1", "market": {"initial_received_lp_lock_fraction": {"numerator": "2", "denominator": "2"}}},
        {"schema": "HTFP_LAUNCH_DOSSIER_V1", "market": {"initial_received_lp_lock_fraction": {"numerator": "1", "denominator": "2"}}},
        {"schema": "HTFP_LAUNCH_DOSSIER_V1", "volume": {"initial_credit_gross_base_units": "8", "capacity_gross_base_units": "7"}},
    ]
    assert [case["input"] for case in oracle["cases"]] == expected_objects
    assert sha((ROOT / "evidence/M6B_SUPPLEMENT_HANDOFF.json").read_bytes()) == "0be038a58dec5ee558b8152022f3788dbe8c9b233234813cd3998568799b6568"
    for key in ("frozen_product_source_pins", "design_pins"):
        for name, digest in oracle[key].items():
            assert sha((ROOT / name).read_bytes()) == digest, name
    return seal, oracle


def compare(report, code, expected, oracle, requirements, raw):
    assert report["input_sha256"] == sha(raw) == expected["input_sha256"]
    assert code == expected["exit_code"]
    for key in ("outcome", "error"):
        assert report[key] == expected[key]
    assert set(report) == set(requirements["report"]["keys"])
    for key, value in requirements["report"]["fixed"].items():
        assert report[key] == value
    assert report["policy_sources"] == oracle["common_policy_sources_exact"]
    assert report["contradictions"] == expected["contradictions_exact"]
    assert report["derived"] == expected["derived_exact"]
    assert len(report["checks"]) == 38
    assert [{k: row[k] for k in ("rule_id", "path")} for row in report["checks"][31:]] == oracle["common_relationship_check_tail_id_path_order_exact"]
    for row in expected["required_checks_subset"]:
        assert row in report["checks"]
    for row in expected["required_open_items_subset"]:
        assert row in report["open_items"]
    common = oracle["common_unverified_external_prefix_exact"]
    assert report["unverified_assertions"] == common
    assert len(common) == 7
    for finding in report["open_items"]:
        if finding["code"] in ("MISSING_INPUT", "OPEN_CHOICE", "PROVISIONAL_CHOICE"):
            group = finding["path"].split(".", 1)[0]
            assert finding["source_ids"] == requirements["group_source_ids"][group]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12) or not sys.dont_write_bytecode or sys.flags.optimize:
        raise RuntimeError("Use Python3.12 -B without optimization")
    if not args.run_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.run_id):
        raise ValueError("Use a simple unique run ID")
    seal, oracle = load_inputs()
    cases = oracle["cases"]
    assert len(cases) == 3
    assert sha(LEDGER_PATH.read_bytes()) == LEDGER_SHA
    specification = importlib.util.spec_from_file_location("m6b_supplement_frozen_ledger", LEDGER_PATH)
    ledger_module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(ledger_module)
    old_seal_path = ROOT / "evidence/m6b/author/HANDOFF.json"
    assert sha(old_seal_path.read_bytes()) == "827af11cef428d6bbd3a0a3f650136631952242b2e5fcb434a394b58981a8160"
    old = json.loads(old_seal_path.read_text())
    for name, expected in old["payload_manifest"].items():
        assert meta(ROOT / name) == expected, name
    requirement_path = ROOT / "evidence/m6b/design/revision-001/REQUIREMENTS.json"
    requirements = json.loads(requirement_path.read_text())
    paths = [ROOT / name for name in old["source_manifest"]]
    paths += [p for p in (ROOT / "tests/m6b_supplement").rglob("*") if p.is_file()]
    source_map = {str(path.relative_to(ROOT)): meta(path) for path in sorted(paths)}
    evidence = AUTHOR / args.run_id; evidence.mkdir(exist_ok=False)
    for name in source_map:
        destination = evidence / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    write(evidence / "INPUTS.json", {"command": sys.argv, "source_manifest": source_map,
          "oracle_seal": meta(ORACLE_DIR / "HANDOFF.json"), "oracle": meta(ORACLE_DIR / "EXPECTED_CASES.json"),
          "requirements": meta(requirement_path), "case_ids": [case["id"] for case in cases]})
    result = {"status": "RUNNING_UNFINALIZED", "stage_acceptance": False, "planned": 3}
    write(evidence / "RESULT.json", result)
    journal, records, passed = None, [], False
    try:
        pre_author = sum(p.stat().st_size for base in (ROOT / "tools/htfp_launch_manifest", ROOT / "tests/m6b", ROOT / "tests/m6b_supplement", ROOT / "evidence/m6b/author") for p in base.rglob("*") if p.is_file())
        pre_total = sum(p.stat().st_size for p in (ROOT / "evidence/m6b").rglob("*") if p.is_file()) + sum(p.stat().st_size for base in (ROOT / "tools/htfp_launch_manifest", ROOT / "tests/m6b", ROOT / "tests/m6b_supplement") for p in base.rglob("*") if p.is_file())
        result["resource_preflight"] = {"author_bytes": pre_author, "all_M6B_bytes": pre_total, "free_bytes": shutil.disk_usage(ROOT).free}
        assert pre_author <= 1572864 and pre_total <= 4194304 and result["resource_preflight"]["free_bytes"] >= 2147483648
        journal = ledger_module.Journal(AUTHOR, args.run_id, "author", ROOT / "evidence/m6b")
        assert journal.prior_counts == {"author": 125, "supervisor": 165}
        journal.begin(source_manifest_sha256=sha(canonical(source_map)), planned=3)
        input_dir = evidence / "inputs"; input_dir.mkdir()
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(ROOT / "tools"))
        for case in cases:
            raw = canonical(case["input"])
            assert len(raw) == case["input_bytes"] and sha(raw) == case["expected"]["input_sha256"]
            path = input_dir / (case["id"] + ".json"); path.write_bytes(raw)
            command = [sys.executable, "-B", "-m", "htfp_launch_manifest", str(path)]
            attempt = journal.start_case(case["id"], input_sha256=sha(raw), command=command)
            row = {"case_id": case["id"], "attempt": attempt, "command": command,
                   "input_base64": base64.b64encode(raw).decode()}
            completed = False
            try:
                child = subprocess.run(command, input=b"", capture_output=True, cwd=ROOT, env=environment, timeout=5)
                completed = True
                row.update(exit_code=child.returncode, stdout_base64=base64.b64encode(child.stdout).decode(),
                           stderr_base64=base64.b64encode(child.stderr).decode(), stdout_sha256=sha(child.stdout), stderr_sha256=sha(child.stderr))
                assert child.stderr == b"" and len(child.stdout) <= 131072
                report = json.loads(child.stdout)
                assert child.stdout == canonical(report)
                compare(report, child.returncode, case["expected"], oracle, requirements, raw)
                row["assertions"] = "PASS"
            except BaseException as exc:
                row["assertions"] = "FAIL"
                row["exception"] = type(exc).__name__ + ": " + str(exc)
                if isinstance(exc, subprocess.TimeoutExpired):
                    row["stdout_base64"] = base64.b64encode(exc.stdout or b"").decode()
                    row["stderr_base64"] = base64.b64encode(exc.stderr or b"").decode()
                raise
            finally:
                records.append(row)
                journal.finish_case(attempt, completed=completed, exit_code=row.get("exit_code"),
                                    stdout_sha256=row.get("stdout_sha256"), assertions=row["assertions"])
        assert len(records) == 3
        assert {name: meta(ROOT / name) for name in source_map} == source_map
        passed = True
    except BaseException as exc:
        result["failure"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        data = canonical(records); stored = gzip.compress(data, mtime=0)
        (evidence / "records.json.gz").write_bytes(stored)
        result["records"] = {"path": str((evidence / "records.json.gz").relative_to(ROOT)),
             "stored_bytes": len(stored), "stored_sha256": sha(stored), "decoded_bytes": len(data), "decoded_sha256": sha(data), "record_count": len(records)}
        own_size = sum(p.stat().st_size for base in (ROOT / "tools/htfp_launch_manifest", ROOT / "tests/m6b", ROOT / "tests/m6b_supplement", ROOT / "evidence/m6b/author") for p in base.rglob("*") if p.is_file())
        all_size = sum(p.stat().st_size for p in (ROOT / "evidence/m6b").rglob("*") if p.is_file()) + sum(p.stat().st_size for base in (ROOT / "tools/htfp_launch_manifest", ROOT / "tests/m6b", ROOT / "tests/m6b_supplement") for p in base.rglob("*") if p.is_file())
        free = shutil.disk_usage(ROOT).free
        result["resources_before_result"] = {"author_bytes": own_size, "all_M6B_bytes": all_size, "free_bytes": free}
        if own_size > 1572864 or all_size > 4194304 or free < 2147483648:
            passed = False; result["resource_failure"] = True
        result["status"] = "AUTHOR_SUPPLEMENT_CHECKS_PASS" if passed else "AUTHOR_SUPPLEMENT_CHECKS_FAIL"
        if journal is not None and journal.started:
            journal.finalize(result["status"], record_count=len(records))
        result.update(attempted=journal.attempted if journal else 0, completed=journal.completed if journal else 0,
                      cumulative_author=(journal.prior_role + journal.attempted) if journal else 125,
                      cumulative_supervisor_at_run=165, source_manifest_after={name: meta(ROOT / name) for name in source_map},
                      new_HTTP=0, new_native_VMs=0, new_native_sends=0, public_actions=0)
        write(evidence / "RESULT.json", result)
    print(json.dumps({"status": result["status"], "path": str(evidence.relative_to(ROOT)), "attempted": result["attempted"], "failure": result.get("failure")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
