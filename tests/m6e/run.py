"""One frozen270case actual CLI campaign, without importing any product."""

import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import traceback

from ledger import Journal, scan

ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = "evidence/m6e/supervisor/oracle_design/FINAL_INDEX.json"
INDEX_SHA = "c5c32e95c9aa77448a312f60bee404009ee00689b7e93208a1746aad861f6281"
OWNED = ("tools/htfp_accounting_state", "tests/m6e", "evidence/m6e/author")
MARKER = b"M6E retained nonregular directory fixture; not account or profile data.\n"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def entry(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def source_map():
    result = {}
    for prefix in OWNED[:2]:
        for path in sorted((ROOT / prefix).rglob("*")):
            if path.is_file():
                assert not path.is_symlink() and "__pycache__" not in path.parts
                result[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    assert result
    return result


def resources(enforce=True):
    owned = [p for prefix in OWNED for p in (ROOT / prefix).rglob("*") if p.is_file()]
    total = [p for prefix in (OWNED[0], OWNED[1], "evidence/m6e")
             for p in (ROOT / prefix).rglob("*") if p.is_file()]
    total.extend(ROOT.glob("evidence/M6E_*"))
    report = dict(author_source_tests_evidence_bytes=sum(p.stat().st_size for p in owned),
                  total_m6e_bytes=sum(p.stat().st_size for p in total), free_bytes=shutil.disk_usage(ROOT).free)
    if enforce:
        assert report["author_source_tests_evidence_bytes"] <= 1572864, report
        assert report["total_m6e_bytes"] <= 4194304 and report["free_bytes"] >= 2147483648, report
    return report


def load_plan():
    raw = (ROOT / INDEX_PATH).read_bytes()
    assert sha(raw) == INDEX_SHA
    index = json.loads(raw)
    cases = []
    for component in index["components"]:
        stored = (ROOT / component["path"]).read_bytes()
        decoded = gzip.decompress(stored)
        assert len(stored) == component["stored_bytes"] and sha(stored) == component["stored_sha256"]
        assert len(decoded) == component["raw_bytes"] and sha(decoded) == component["raw_sha256"]
        dossier = json.loads(decoded)
        assert len(dossier["cases"]) == component["case_count"]
        cases.extend(dossier["cases"])
    assert len(cases) == 270 and [case["case_id"] for case in cases] == index["case_ids"]
    assert len(set(index["case_ids"])) == 270
    for pin in index["design_pins"].values():
        assert entry(ROOT / pin["path"]) == pin
    return index, cases


def request_bytes(case):
    text, encoded = case["input_utf8"], case["input_base64"]
    assert text is None or encoded is None
    raw = text.encode("utf-8") if text is not None else (
        base64.b64decode(encoded, validate=True) if encoded is not None else None)
    assert (len(raw) if raw is not None else None) == case["input_bytes"]
    assert (sha(raw) if raw is not None else None) == case["input_sha256"]
    for field in ("stdout", "stderr"):
        expected = case["expected_" + field + "_utf8"].encode("utf-8")
        assert len(expected) == case["expected_" + field + "_bytes"]
        assert sha(expected) == case["expected_" + field + "_sha256"]
    return raw


def directory_fixture(path):
    path.mkdir(parents=True, exist_ok=False)
    mode = path.stat().st_mode
    assert stat.S_ISDIR(mode)
    marker = path / "RETAINED_DIRECTORY_MARKER.txt"
    marker.write_bytes(MARKER)
    return dict(path=str(path.relative_to(ROOT)), actual_kind="directory", fstat_mode=mode,
                marker=entry(marker), marker_is_account_or_profile_data=False)


def copy_package(base, case, sources):
    variant = case["execution_variant"]
    package_base = base / "isolated_packages" / case["case_id"]
    copied, python_hashes = {}, {}
    for original in sorted((ROOT / OWNED[0]).rglob("*")):
        if not original.is_file() or original.name == "PROFILE.json":
            continue
        dest = package_base / original.relative_to(ROOT / "tools")
        dest.parent.mkdir(parents=True, exist_ok=True)
        name, raw = str(original.relative_to(ROOT)), original.read_bytes()
        assert sha(raw) == sources[name]
        dest.write_bytes(raw)
        copied[name] = str(dest.relative_to(ROOT))
        if original.suffix == ".py":
            python_hashes[name] = sha(raw)
    path = package_base / variant["profile_relative_path"]
    fixture = variant["profile_fixture_utf8"]
    proof = dict(base=str(package_base.relative_to(ROOT)), copied_paths=copied,
                 python_source_hashes=python_hashes, profile_path=str(path.relative_to(ROOT)),
                 profile_bytes=variant["profile_fixture_bytes"], profile_sha256=variant["profile_fixture_sha256"])
    if variant.get("profile_fixture_kind") == "directory":
        proof["profile_kind"] = "directory"
        proof["profile_present"] = True
        proof["directory_fixture"] = directory_fixture(path)
    elif fixture is None:
        assert not path.exists()
        proof.update(profile_kind="missing", profile_present=False)
    else:
        raw = fixture.encode("utf-8")
        assert len(raw) == variant["profile_fixture_bytes"] and sha(raw) == variant["profile_fixture_sha256"]
        path.write_bytes(raw)
        proof.update(profile_kind="regular_file", profile_present=True)
    return package_base, proof


def capture_output(row, name, raw):
    row[name + "_bytes"], row[name + "_sha256"] = len(raw), sha(raw)
    try:
        row[name + "_utf8"] = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        row[name + "_utf8"] = None
        row[name + "_base64"] = base64.b64encode(raw).decode("ascii")


def main():
    assert sys.version_info[:2] == (3, 12) and sys.dont_write_bytecode
    assert Path.cwd() == ROOT == Path("/home/jerem/htfp")
    assert os.uname().nodename == "weathertrades" and os.getuid() == 1001
    assert len(sys.argv) == 2 and sys.argv[1].startswith("author-")
    name = sys.argv[1]
    assert name == Path(name).name and name not in (".", "..")
    base = ROOT / OWNED[2] / name
    assert not base.exists()
    index, cases = load_plan()
    for case in cases:
        request_bytes(case)
    sources, prior, before = source_map(), scan(ROOT / "evidence/m6e"), resources()
    assert prior["author"] + 270 <= 1024
    generation = sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    base.mkdir(parents=True)
    (base / "inputs").mkdir()
    for path, digest in sources.items():
        raw = (ROOT / path).read_bytes()
        assert sha(raw) == digest
        dest = base / "source" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    execution = dict(status="RUNNING_UNFINALIZED", UTC=utc(), run_id="m6e-" + name, role="author",
                     source_hashes=sources, source_generation_sha256=generation, prior_counts=prior,
                     resources_before=before, product_imports_in_runner=False, new_HTTP_native_public_actions=0)
    write(base / "EXECUTION.json", execution)
    journal = Journal(base, execution["run_id"], "author", prior)
    capture = dict(schema="HTFP_M6E_AUTHOR_CLI_CAPTURE_V1", role="author", run_id=execution["run_id"],
                   oracle_union_index_sha256=INDEX_SHA, oracle_components=index["components"],
                   design_hashes={p["path"]: p["sha256"] for p in index["design_pins"].values()},
                   source_hashes=sources, source_generation_sha256=generation, records=[])
    attempted = completed = 0
    mismatches, infrastructure = [], None
    try:
        for case in cases:
            resources()
            assert source_map() == sources, "Source changed before invocation"
            case_id, variant = case["case_id"], case.get("execution_variant")
            assert case_id == Path(case_id).name and case_id not in (".", "..")
            kind = variant["kind"] if variant else None
            raw = request_bytes(case)
            row = dict(case_id=case_id,
                       required_matrix_ids=[key for key, value in index["required_case_aliases"].items() if value == case_id],
                       generated_matrix_ids=[case_id] if case_id in index["generated_ids"] else [],
                       execution_variant=variant, input_utf8=case["input_utf8"], input_base64=case["input_base64"],
                       input_bytes=case["input_bytes"], input_sha256=case["input_sha256"],
                       exit_code=None, exact_oracle_match=False)
            capture_output(row, "stdout", b"")
            capture_output(row, "stderr", b"")
            pythonpath = ROOT / "tools"
            if kind == "isolated_package_copy":
                pythonpath, row["copied_package"] = copy_package(base, case, sources)
            readfd = None
            if raw is not None:
                path = base / "inputs" / (case_id + ".json")
                path.write_bytes(raw)
                assert path.read_bytes() == raw
                row["input_path"] = str(path.relative_to(ROOT))
                args = [str(path)]
            elif kind == "argv_help":
                args = ["--help"]
            elif kind == "argv_empty":
                args = []
            elif kind == "argv_extra":
                args = [str(base / "inputs" / "extra-one.absent"), str(base / "inputs" / "extra-two.absent")]
            elif kind == "empty_path":
                args = [""]
            elif kind == "overlong_path":
                args = ["x" * 5000]
                row["overlong_path_characters"] = 5000
            elif kind == "leading_dash":
                args = ["-request.json"]
            elif kind == "missing_path":
                path = base / "inputs" / (case_id + ".absent")
                assert not path.exists()
                row["missing_path"] = str(path.relative_to(ROOT))
                args = [str(path)]
            elif kind == "directory_path":
                path = base / "input_directories" / case_id
                row["directory_fixture"] = directory_fixture(path)
                args = [str(path)]
            elif kind == "fifo_path":
                readfd, writefd = os.pipe()
                os.close(writefd)
                mode = os.fstat(readfd).st_mode
                assert stat.S_ISFIFO(mode)
                args = ["/proc/self/fd/0"]
                row["FIFO_materialization"] = dict(kind="NEW_ANONYMOUS_FIFO", fstat_is_fifo=True,
                    fstat_mode=mode, writer_closed_before_invocation=True,
                    child_stdin_is_read_descriptor=True, pathname="/proc/self/fd/0")
            else:
                raise AssertionError("Unknown exact input materialization")
            argv = [sys.executable, "-B", "-m", "htfp_accounting_state", *args]
            row.update(argv=argv, pythonpath=str(pythonpath), timeout_seconds=5)
            capture["records"].append(row)
            attempted = journal.start(case_id=case_id, argv=argv, input_sha256=row["input_sha256"],
                                      source_generation_sha256=generation)
            try:
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(pythonpath))
                response = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, check=False,
                                          timeout=5, stdin=readfd if readfd is not None else subprocess.DEVNULL)
                completed += 1
                row["exit_code"] = response.returncode
                capture_output(row, "stdout", response.stdout)
                capture_output(row, "stderr", response.stderr)
                row["exact_oracle_match"] = (
                    response.returncode == case["expected_exit"] and
                    response.stdout == case["expected_stdout_utf8"].encode("utf-8") and
                    response.stderr == case["expected_stderr_utf8"].encode("utf-8"))
                if not row["exact_oracle_match"]:
                    mismatches.append(case_id)
                assert len(response.stdout) <= 65536 and len(response.stderr) <= 65536, "Output exceeds bound"
            except BaseException as exc:
                row["capture_failure"] = dict(type=type(exc).__name__, message=str(exc))
                if isinstance(exc, subprocess.TimeoutExpired):
                    capture_output(row, "stdout", exc.stdout or b"")
                    capture_output(row, "stderr", exc.stderr or b"")
                raise
            finally:
                if readfd is not None:
                    os.close(readfd)
                    row["FIFO_materialization"]["owned_read_descriptor_closed_after_invocation"] = True
                journal.finish(case_id=case_id, completed=row["exit_code"] is not None,
                               exit_code=row["exit_code"], stdout_sha256=row["stdout_sha256"],
                               stderr_sha256=row["stderr_sha256"], exact_oracle_match=row["exact_oracle_match"])
            if mismatches:
                # S137: preserve and report the observed generation before retry/correction.
                break
        assert source_map() == sources, "Source changed during campaign"
    except BaseException as exc:
        infrastructure = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    finally:
        counters = dict(attempted=attempted, completed=completed, prior_role_attempts=prior["author"],
                        prior_global_attempts=sum(prior.values()), role_cumulative_attempts=prior["author"] + attempted,
                        global_cumulative_attempts=sum(prior.values()) + attempted)
        capture.update(counters=counters, mismatched_case_ids=mismatches, infrastructure_failure=infrastructure)
        raw_capture = (json.dumps(capture, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        stored = gzip.compress(raw_capture, mtime=0)
        (base / "CAPTURE.json.gz").write_bytes(stored)
        current = source_map()
        passed = infrastructure is None and not mismatches and attempted == completed == 270 and current == sources
        result = dict(schema="HTFP_M6E_AUTHOR_RESULT_V1", stage_acceptance=False,
                      status="LOCAL_OFFLINE_CLI_270_EXACT_PASS" if passed else "FAIL_OR_INCOMPLETE",
                      UTC=utc(), counters=counters, required_case_count=270,
                      matched_case_count=sum(row["exact_oracle_match"] for row in capture["records"]),
                      coverage=dict(C_aliases=[key for row in capture["records"] if row["exact_oracle_match"]
                                              for key in row["required_matrix_ids"]],
                                    G_separately_executed=[key for row in capture["records"] if row["exact_oracle_match"]
                                                           for key in row["generated_matrix_ids"]]),
                      capture=dict(path=str((base / "CAPTURE.json.gz").relative_to(ROOT)), stored_bytes=len(stored),
                                   stored_sha256=sha(stored), raw_bytes=len(raw_capture), raw_sha256=sha(raw_capture)),
                      source_hashes=sources, source_generation_sha256=generation, sources_unchanged=current == sources,
                      mismatched_case_ids=mismatches, infrastructure_failure=infrastructure,
                      stopped_on_first_unexpected_mismatch=bool(mismatches), new_HTTP_native_public_actions=0,
                      limits="Finite fixed independent oracle reports; no exhaustive, shrinking, native or public acceptance")
        observed = resources(enforce=False)
        if (observed["author_source_tests_evidence_bytes"] + 131072 > 1572864 or
                observed["total_m6e_bytes"] + 131072 > 4194304 or observed["free_bytes"] < 2147483648):
            result["status"] = "FAIL_OR_INCOMPLETE"
            result["resource_finalization_failure"] = observed
        result["resources_before_final_records"] = observed
        write(base / "RESULT.json", result)
        execution.update(status=result["status"], finalized_UTC=utc(), counters=counters,
                         infrastructure_failure=infrastructure, sources_unchanged=current == sources,
                         result_sha256=sha((base / "RESULT.json").read_bytes()))
        write(base / "EXECUTION.json", execution)
        journal.finalize(status=result["status"], completed=completed, result_sha256=execution["result_sha256"])
    print(json.dumps(dict(status=result["status"], run=str(base.relative_to(ROOT)), counters=counters,
                          mismatches=mismatches, infrastructure_failure=infrastructure), sort_keys=True))
    return 0 if result["status"] == "LOCAL_OFFLINE_CLI_270_EXACT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
