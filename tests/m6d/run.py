"""Serial, prospectively counted actual CLI comparison with the sealed oracle.

No product imports and no construction of expected reports from product code.
"""

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
INDEX = "evidence/m6d/supervisor/oracle_design/FINAL_INDEX.json"
INDEX_SHA = "d257d9c399a14fe4885f78254d868e593a518891b5772bdf01e4cffc9cfd986b"
OWNED = ("clients/htfp_recover", "tests/m6d", "evidence/m6d/author")


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
    author_bytes = sum(p.stat().st_size for prefix in OWNED
                       for p in (ROOT / prefix).rglob("*") if p.is_file())
    all_paths = [p for prefix in ("clients/htfp_recover", "tests/m6d", "evidence/m6d")
                 for p in (ROOT / prefix).rglob("*") if p.is_file()]
    all_paths.extend(ROOT.glob("evidence/M6D_*"))
    result = dict(author_source_tests_evidence_bytes=author_bytes,
                  total_m6d_bytes=sum(p.stat().st_size for p in all_paths),
                  free_bytes=shutil.disk_usage(ROOT).free)
    if enforce:
        assert author_bytes <= 1572864 and result["total_m6d_bytes"] <= 4194304, result
        assert result["free_bytes"] >= 2147483648, result
    return result


def oracle():
    raw = (ROOT / INDEX).read_bytes()
    assert sha(raw) == INDEX_SHA
    index = json.loads(raw)
    by_id = {}
    for component in index["components"]:
        stored = (ROOT / component["path"]).read_bytes()
        raw = gzip.decompress(stored)
        assert len(stored) == component["stored_bytes"] and sha(stored) == component["stored_sha256"]
        assert len(raw) == component["raw_bytes"] and sha(raw) == component["raw_sha256"]
        dossier = json.loads(raw)
        assert len(dossier["cases"]) == component["case_count"]
        for case in dossier["cases"]:
            assert case["case_id"] not in by_id
            by_id[case["case_id"]] = case
    assert len(by_id) == len(index["case_ids"]) == len(set(index["case_ids"])) == 159
    assert set(by_id) == set(index["case_ids"])
    # The retained draft component has explicitly historical preparation pins.
    # The union's final seal is the authoritative current design binding.
    for pin in index["design_pins"].values():
        current = entry(ROOT / pin["path"])
        assert current == pin, (current, pin)
    return index, [by_id[case_id] for case_id in index["case_ids"]]


def original_input(case):
    text, encoded = case["input_utf8"], case["input_base64"]
    assert text is None or encoded is None
    raw = text.encode("utf-8") if text is not None else (
        base64.b64decode(encoded, validate=True) if encoded is not None else None)
    assert (len(raw) if raw is not None else None) == case["input_bytes"]
    assert (sha(raw) if raw is not None else None) == case["input_sha256"]
    for stream in ("stdout", "stderr"):
        expected = case["expected_" + stream + "_utf8"].encode("utf-8")
        assert len(expected) == case["expected_" + stream + "_bytes"]
        assert sha(expected) == case["expected_" + stream + "_sha256"]
    return raw


def isolated_package(base, case, sources):
    variant = case["execution_variant"]
    package_base = base / "isolated_packages" / case["case_id"]
    copied, py_sources = {}, {}
    for original in sorted((ROOT / "clients/htfp_recover").rglob("*")):
        if not original.is_file() or original.name == "PROFILE.json":
            continue
        relative = original.relative_to(ROOT / "clients")
        dest = package_base / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = original.read_bytes()
        name = str(original.relative_to(ROOT))
        assert sha(raw) == sources[name]
        dest.write_bytes(raw)
        copied[name] = str(dest.relative_to(ROOT))
        if original.suffix == ".py":
            py_sources[name] = sha(raw)
    profile_path = package_base / variant["profile_relative_path"]
    fixture = variant["profile_fixture_utf8"]
    if fixture is not None:
        raw = fixture.encode("utf-8")
        assert len(raw) == variant["profile_fixture_bytes"] and sha(raw) == variant["profile_fixture_sha256"]
        profile_path.write_bytes(raw)
    else:
        assert not profile_path.exists()
    evidence = dict(base=str(package_base.relative_to(ROOT)), copied_paths=copied,
                    python_source_hashes=py_sources, profile_path=str(profile_path.relative_to(ROOT)),
                    profile_present=fixture is not None, profile_bytes=variant["profile_fixture_bytes"],
                    profile_sha256=variant["profile_fixture_sha256"])
    return package_base, evidence


def raw_output(row, stream, raw):
    row[stream + "_bytes"], row[stream + "_sha256"] = len(raw), sha(raw)
    try:
        row[stream + "_utf8"] = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        row[stream + "_utf8"] = None
        row[stream + "_base64"] = base64.b64encode(raw).decode("ascii")


def main():
    assert sys.version_info[:2] == (3, 12) and sys.dont_write_bytecode
    assert Path.cwd() == ROOT == Path("/home/jerem/htfp")
    assert os.uname().nodename == "weathertrades" and os.getuid() == 1001
    assert len(sys.argv) == 2 and sys.argv[1].startswith("author-")
    name = sys.argv[1]
    assert name == Path(name).name and name not in (".", "..")
    base = ROOT / "evidence/m6d/author" / name
    assert not base.exists()
    index, cases = oracle()
    for case in cases:
        original_input(case)
    sources, prior, before = source_map(), scan(ROOT / "evidence/m6d"), resources()
    assert prior["author"] + len(cases) <= 1024
    generation = sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    base.mkdir(parents=True)
    (base / "inputs").mkdir()
    for path, digest in sources.items():
        raw = (ROOT / path).read_bytes()
        assert sha(raw) == digest
        dest = base / "source" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    execution = dict(status="RUNNING_UNFINALIZED", UTC=utc(), run_id="m6d-" + name,
                     role="author", source_hashes=sources, source_generation_sha256=generation,
                     prior_counts=prior, resources_before=before, target_imports_in_runner=False,
                     new_HTTP_native_public_actions=0)
    write(base / "EXECUTION.json", execution)
    journal = Journal(base, execution["run_id"], "author", prior)
    capture = dict(schema="HTFP_M6D_AUTHOR_CLI_CAPTURE_V1", role="author", run_id=execution["run_id"],
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
            raw = original_input(case)
            row = dict(case_id=case_id,
                       required_matrix_ids=[key for key, value in index["required_case_aliases"].items() if value == case_id],
                       generated_matrix_ids=[case_id] if case_id in index["generated_ids"] else [],
                       execution_variant=variant, input_utf8=case["input_utf8"], input_base64=case["input_base64"],
                       input_bytes=case["input_bytes"], input_sha256=case["input_sha256"], exit_code=None,
                       exact_oracle_match=False)
            raw_output(row, "stdout", b"")
            raw_output(row, "stderr", b"")
            pythonpath = ROOT / "clients"
            if kind == "isolated_package_copy":
                pythonpath, row["copied_package"] = isolated_package(base, case, sources)
            readfd = None
            if raw is not None:
                path = base / "inputs" / (case_id + ".json")
                path.write_bytes(raw)
                assert path.read_bytes() == raw
                row["input_path"] = str(path.relative_to(ROOT))
                args = [str(path)]
            elif kind == "argv_help":
                args = ["--help"]
            elif kind == "missing_path":
                path = base / "inputs" / (case_id + ".absent")
                assert not path.exists()
                row["missing_path"] = str(path.relative_to(ROOT))
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
            argv = [sys.executable, "-B", "-m", "htfp_recover", *args]
            row.update(argv=argv, pythonpath=str(pythonpath), timeout_seconds=5)
            capture["records"].append(row)
            # The durable START precedes creation/execution of the target child.
            attempted = journal.start(case_id=case_id, argv=argv, input_sha256=row["input_sha256"],
                                      source_generation_sha256=generation)
            try:
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(pythonpath))
                result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, check=False,
                                        timeout=5, stdin=readfd if readfd is not None else subprocess.DEVNULL)
                completed += 1
                row["exit_code"] = result.returncode
                raw_output(row, "stdout", result.stdout)
                raw_output(row, "stderr", result.stderr)
                row["exact_oracle_match"] = (
                    result.returncode == case["expected_exit"] and
                    result.stdout == case["expected_stdout_utf8"].encode("utf-8") and
                    result.stderr == case["expected_stderr_utf8"].encode("utf-8"))
                if not row["exact_oracle_match"]:
                    mismatches.append(case_id)
                assert len(result.stdout) <= 65536 and len(result.stderr) <= 65536, "Output bound exceeded"
            except BaseException as exc:
                row["capture_failure"] = dict(type=type(exc).__name__, message=str(exc))
                if isinstance(exc, subprocess.TimeoutExpired):
                    raw_output(row, "stdout", exc.stdout or b"")
                    raw_output(row, "stderr", exc.stderr or b"")
                raise
            finally:
                if readfd is not None:
                    os.close(readfd)
                    row["FIFO_materialization"]["owned_read_descriptor_closed_after_invocation"] = True
                journal.finish(case_id=case_id, completed=row["exit_code"] is not None,
                               exit_code=row["exit_code"], stdout_sha256=row["stdout_sha256"],
                               stderr_sha256=row["stderr_sha256"], exact_oracle_match=row["exact_oracle_match"])
        assert source_map() == sources, "Source changed during campaign"
    except BaseException as exc:
        infrastructure = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    finally:
        counters = dict(attempted=attempted, completed=completed, prior_role_attempts=prior["author"],
                        prior_global_attempts=sum(prior.values()), role_cumulative_attempts=prior["author"] + attempted,
                        global_cumulative_attempts=sum(prior.values()) + attempted)
        capture["counters"] = counters
        capture["infrastructure_failure"] = infrastructure
        capture["mismatched_case_ids"] = mismatches
        raw_capture = (json.dumps(capture, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        stored = gzip.compress(raw_capture, mtime=0)
        (base / "CAPTURE.json.gz").write_bytes(stored)
        current = source_map()
        passed = (infrastructure is None and not mismatches and attempted == completed == 159 and current == sources)
        result = dict(schema="HTFP_M6D_AUTHOR_RESULT_V1", stage_acceptance=False,
                      status="LOCAL_OFFLINE_CLI_159_EXACT_PASS" if passed else "FAIL_OR_INCOMPLETE",
                      UTC=utc(), counters=counters, required_case_count=159, matched_case_count=sum(
                          row["exact_oracle_match"] for row in capture["records"]),
                      coverage=dict(C_aliases=[key for row in capture["records"] if row["exact_oracle_match"]
                                              for key in row["required_matrix_ids"]],
                                    G_separately_executed=[key for row in capture["records"] if row["exact_oracle_match"]
                                                           for key in row["generated_matrix_ids"]]),
                      capture=dict(path=str((base / "CAPTURE.json.gz").relative_to(ROOT)),
                                   stored_bytes=len(stored), stored_sha256=sha(stored),
                                   raw_bytes=len(raw_capture), raw_sha256=sha(raw_capture)),
                      source_hashes=sources, source_generation_sha256=generation,
                      sources_unchanged=current == sources, mismatched_case_ids=mismatches,
                      infrastructure_failure=infrastructure, limits="FINITE_FIXED_ORACLE_CASES; no exhaustive or native proof",
                      new_HTTP_native_public_actions=0)
        # Reserve ample final seal/result headroom; no PASS after resource failure.
        observed = resources(enforce=False)
        if (observed["author_source_tests_evidence_bytes"] + 49152 > 1572864 or
                observed["total_m6d_bytes"] + 49152 > 4194304 or observed["free_bytes"] < 2147483648):
            result["status"] = "FAIL_OR_INCOMPLETE"
            result["resource_finalization_failure"] = observed
        result["resources_before_final_records"] = observed
        write(base / "RESULT.json", result)
        execution.update(status=result["status"], finalized_UTC=utc(), counters=counters,
                         infrastructure_failure=infrastructure, sources_unchanged=current == sources,
                         result_sha256=sha((base / "RESULT.json").read_bytes()))
        write(base / "EXECUTION.json", execution)
        journal.finalize(status=result["status"], attempted=attempted, completed=completed,
                         cumulative_role=prior["author"] + attempted,
                         cumulative_global=sum(prior.values()) + attempted,
                         result_sha256=execution["result_sha256"])
    print(json.dumps(dict(status=result["status"], run=str(base.relative_to(ROOT)), counters=counters,
                          mismatches=mismatches, infrastructure_failure=infrastructure), sort_keys=True))
    return 0 if result["status"] == "LOCAL_OFFLINE_CLI_159_EXACT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
