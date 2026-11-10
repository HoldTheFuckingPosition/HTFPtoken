"""One fixed serial 153-case actual CLI campaign; never imports the product.

Read the frozen independent oracle, retain exact bytes/source/IO setup and
prospectively journal every subprocess. No hidden probes or automatic retries.
"""

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import traceback

from ledger import Journal, utc


ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / "evidence/m6c/supervisor/oracle_design"
INDEX_SHA = "e373628d96f0c71c609eea37498c2af225f49ed24cf4b3515e42adb522cfaa22"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n")


def source_map():
    result = {}
    for prefix in ("clients/htfp_redeem", "tests/m6c"):
        for path in sorted((ROOT / prefix).rglob("*")):
            if path.is_file():
                if path.is_symlink() or "__pycache__" in path.parts:
                    raise RuntimeError("Unexpected product/test source representation")
                result[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    return result


def resources(enforce=True):
    prefixes = ("clients/htfp_redeem", "tests/m6c", "evidence/m6c/author")
    author = sum(p.stat().st_size for prefix in prefixes
                 for p in (ROOT / prefix).rglob("*") if p.is_file())
    total = sum(p.stat().st_size for prefix in ("clients/htfp_redeem", "tests/m6c", "evidence/m6c")
                for p in (ROOT / prefix).rglob("*") if p.is_file())
    total += sum(p.stat().st_size for p in ROOT.glob("evidence/M6C_*") if p.is_file())
    free = shutil.disk_usage(ROOT).free
    if enforce and (author > 1572864 or total > 4194304 or free < 2147483648):
        raise RuntimeError("M6C resource boundary reached")
    return dict(author_owned_bytes=author, all_m6c_bytes=total, free_bytes=free)


def load_cases():
    index_raw = (ORACLE / "FINAL_INDEX.json").read_bytes()
    if sha(index_raw) != INDEX_SHA:
        raise RuntimeError("Frozen union index changed")
    index, cases = json.loads(index_raw), []
    design_hashes = None
    for component in index["components"]:
        stored = (ROOT / component["path"]).read_bytes()
        raw = gzip.decompress(stored)
        if (sha(stored) != component["stored_sha256"] or len(stored) != component["stored_bytes"] or
                sha(raw) != component["raw_sha256"] or len(raw) != component["raw_bytes"]):
            raise RuntimeError("Frozen oracle component changed")
        dossier = json.loads(raw)
        if len(dossier["cases"]) != component["cases"]:
            raise RuntimeError("Wrong oracle component case count")
        for pin in dossier["design_pins"].values():
            content = (ROOT / pin["path"]).read_bytes()
            if len(content) != pin["bytes"] or sha(content) != pin["sha256"]:
                raise RuntimeError("Frozen design changed")
        if design_hashes is None:
            design_hashes = {pin["path"]: pin["sha256"] for pin in dossier["design_pins"].values()}
        cases.extend(dossier["cases"])
    if len(cases) != 153 or [case["case_id"] for case in cases] != index["case_ids"]:
        raise RuntimeError("The complete ordered 153-case union is required")
    return index, cases, design_hashes


def exact_input(case):
    text, encoded = case.get("input_utf8"), case.get("input_base64")
    if text is not None and encoded is not None:
        raise RuntimeError("Ambiguous oracle input representation")
    raw = text.encode("utf-8") if text is not None else (
        base64.b64decode(encoded, validate=True) if encoded is not None else None)
    if ((len(raw) if raw is not None else None) != case["input_bytes"] or
            (sha(raw) if raw is not None else None) != case["input_sha256"]):
        raise RuntimeError("Oracle input bytes differ")
    return raw


def materialize(case, base, frozen):
    name, variant = case["case_id"], case.get("execution_variant")
    if name != Path(name).name or name in (".", ".."):
        raise RuntimeError("Invalid oracle case ID")
    raw, pythonpath, metadata = exact_input(case), ROOT / "clients", {}
    kind = variant["kind"] if variant else None
    if kind == "isolated_package_copy":
        pythonpath = base / "isolated_packages" / name
        copied, sources = {}, {}
        for original in sorted((ROOT / "clients/htfp_redeem").rglob("*")):
            if not original.is_file() or original.name == "PROFILE.json":
                continue
            relative = str(original.relative_to(ROOT))
            content = original.read_bytes()
            if sha(content) != frozen[relative]:
                raise RuntimeError("Source changed before isolated copy")
            dest = pythonpath / original.relative_to(ROOT / "clients")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            copied[relative] = str(dest.relative_to(ROOT))
            if original.suffix == ".py":
                sources[relative] = sha(content)
        profile_path = pythonpath / variant["profile_relative_path"]
        fixture = variant["profile_fixture_utf8"]
        if fixture is not None:
            content = fixture.encode("utf-8")
            if len(content) != variant["profile_fixture_bytes"] or sha(content) != variant["profile_fixture_sha256"]:
                raise RuntimeError("Isolated dependency fixture changed")
            profile_path.write_bytes(content)
        elif profile_path.exists():
            raise RuntimeError("Missing-profile fixture unexpectedly exists")
        metadata["copied_package"] = dict(
            base=str(pythonpath.relative_to(ROOT)), python_source_hashes=sources, copied_paths=copied,
            profile_path=str(profile_path.relative_to(ROOT)), profile_present=fixture is not None,
            profile_bytes=variant["profile_fixture_bytes"], profile_sha256=variant["profile_fixture_sha256"])
    readfd = None
    if raw is not None:
        path = base / "inputs" / (name + ".json")
        path.write_bytes(raw)
        if path.read_bytes() != raw:
            raise RuntimeError("Materialized input changed")
        metadata["input_path"] = str(path.relative_to(ROOT))
        args = [str(path)]
    elif kind == "argv_help":
        args = ["--help"]
    elif kind == "missing_path":
        path = base / "inputs" / (name + ".absent")
        if path.exists():
            raise RuntimeError("Absent input unexpectedly exists")
        metadata["missing_path"] = str(path.relative_to(ROOT))
        args = [str(path)]
    elif kind == "fifo_path":
        readfd, writefd = os.pipe()
        try:
            os.close(writefd)
            mode = os.fstat(readfd).st_mode
            if not stat.S_ISFIFO(mode):
                raise RuntimeError("Anonymous read descriptor is not FIFO")
        except BaseException:
            os.close(readfd)
            raise
        metadata["FIFO_materialization"] = dict(
            kind="NEW_ANONYMOUS_FIFO", fstat_mode=mode, fstat_is_fifo=True,
            writer_closed_before_invocation=True, child_stdin_is_read_descriptor=True,
            pathname="/proc/self/fd/0")
        args = ["/proc/self/fd/0"]
    else:
        raise RuntimeError("Unsupported no-input variant")
    return [sys.executable, "-B", "-m", "htfp_redeem", *args], pythonpath, readfd, metadata


def output_record(row, field, raw):
    row[field + "_bytes"], row[field + "_sha256"] = len(raw), sha(raw)
    try:
        row[field + "_utf8"] = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        row[field + "_utf8"] = None
        row[field + "_base64"] = base64.b64encode(raw).decode("ascii")


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"author-[0-9]{3}", sys.argv[1]):
        raise RuntimeError("Usage: python3 -B tests/m6c/run.py author-NNN")
    if (sys.version_info[:2] != (3, 12) or not sys.dont_write_bytecode or
            os.uname().nodename != "weathertrades" or os.getuid() != ROOT.stat().st_uid or
            ROOT != Path("/home/jerem/htfp") or Path.cwd() != ROOT):
        raise RuntimeError("Unexpected host/user/cwd/Python or bytecode policy")
    authority = json.loads((ROOT / "evidence/M6C_STAGE_B_HANDOFF.json").read_bytes())
    if authority["source_id"] != "S117" or authority["status"] != "STAGE_B_OFFLINE_CODEC_IMPLEMENTATION_ASSIGNED":
        raise RuntimeError("Implementation gate is unavailable")
    index, cases, pins = load_cases()
    frozen = source_map()
    generation = sha(json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    before = resources()
    run_id = "m6c-" + sys.argv[1]
    base = ROOT / "evidence/m6c/author" / sys.argv[1]
    base.mkdir(exist_ok=False)
    (base / "inputs").mkdir()
    for name, digest in frozen.items():
        raw = (ROOT / name).read_bytes()
        if sha(raw) != digest:
            raise RuntimeError("Source changed before snapshot")
        dest = base / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    journal = Journal(base, run_id, "author", ROOT / "evidence/m6c")
    result = dict(schema="HTFP_M6C_AUTHOR_EXECUTION_V1", status="RUNNING_UNFINALIZED", UTC=utc(),
                  run_id=run_id, role="author", source_hashes=frozen,
                  source_generation_sha256=generation, resources_before=before,
                  product_imports=False, new_HTTP_native_public_actions=0)
    capture = dict(schema="HTFP_M6C_AUTHOR_CLI_CAPTURE_V1", role="author",
                   oracle_union_index_sha256=INDEX_SHA, oracle_components=index["components"],
                   design_hashes=pins, source_hashes=frozen, source_generation_sha256=generation, records=[])
    write_json(base / "EXECUTION.json", result)
    journal.begin(source_generation_sha256=generation, oracle_union_index_sha256=INDEX_SHA)
    mismatches, success = [], False
    try:
        for case in cases:
            resources()
            if source_map() != frozen:
                raise RuntimeError("Product/test source changed during campaign")
            argv, pythonpath, readfd, extra = materialize(case, base, frozen)
            row = dict(case_id=case["case_id"], required_matrix_ids=case["required_matrix_ids"],
                       execution_variant=case.get("execution_variant"), argv=argv, pythonpath=str(pythonpath),
                       input_utf8=case.get("input_utf8"), input_base64=case.get("input_base64"),
                       input_bytes=case["input_bytes"], input_sha256=case["input_sha256"], exit_code=None, **extra)
            for field in ("stdout", "stderr"):
                output_record(row, field, b"")
            capture["records"].append(row)
            number = None
            try:
                number = journal.start(case["case_id"], argv=argv, input_sha256=case["input_sha256"],
                                       source_generation_sha256=generation)
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(pythonpath))
                child = subprocess.run(argv, cwd=ROOT, env=env,
                                       stdin=readfd if readfd is not None else subprocess.DEVNULL,
                                       capture_output=True, timeout=5, check=False)
                row["exit_code"] = child.returncode
                output_record(row, "stdout", child.stdout)
                output_record(row, "stderr", child.stderr)
                equal = (child.returncode == case["expected_exit"] and
                         child.stdout == case["expected_stdout_utf8"].encode("utf-8") and
                         child.stderr == case["expected_stderr_utf8"].encode("utf-8"))
                row["exact_oracle_match"] = equal
                if not equal:
                    mismatches.append(case["case_id"])
            except subprocess.TimeoutExpired as exc:
                row["failure"] = dict(type="TimeoutExpired", seconds=5)
                output_record(row, "stdout", exc.stdout or b"")
                output_record(row, "stderr", exc.stderr or b"")
                raise
            finally:
                if readfd is not None:
                    os.close(readfd)
                    row["FIFO_materialization"]["owned_read_descriptor_closed_after_invocation"] = True
                if number is not None:
                    journal.finish(number, completed=row["exit_code"] is not None, case_id=case["case_id"],
                                   exit_code=row["exit_code"], stdout_sha256=row["stdout_sha256"],
                                   stderr_sha256=row["stderr_sha256"], exact_oracle_match=row.get("exact_oracle_match", False))
        if source_map() != frozen or journal.attempted != 153 or journal.completed != 153:
            raise RuntimeError("Incomplete campaign or source race")
        success = not mismatches
    except BaseException as exc:
        result["failure"] = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
    finally:
        counters = dict(attempted=journal.attempted, completed=journal.completed,
                        prior_role_attempts=journal.prior["author"], prior_global_attempts=sum(journal.prior.values()),
                        role_cumulative_attempts=journal.prior["author"] + journal.attempted,
                        global_cumulative_attempts=sum(journal.prior.values()) + journal.attempted)
        capture["counters"] = counters
        raw = (json.dumps(capture, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        stored = gzip.compress(raw, mtime=0)
        (base / "CAPTURE.json.gz").write_bytes(stored)
        represented = {cid for row in capture["records"] if row.get("exact_oracle_match") for cid in row["required_matrix_ids"]}
        matrix = json.loads((ROOT / "evidence/m6c/design/MATRIX.json").read_bytes())
        required = {row["id"] for row in matrix["cases"]} | set(matrix["finite_generation"]["ids"])
        if represented != required:
            success = False
        final_sources = source_map()
        budget = resources(False)
        # Reserve ample space for RESULT, EXECUTION and journal finalization;
        # never first write a PASS then discover an exhausted evidence budget.
        budget_ok = (budget["author_owned_bytes"] + 65536 <= 1572864 and
                     budget["all_m6c_bytes"] + 65536 <= 4194304 and
                     budget["free_bytes"] - 65536 >= 2147483648)
        success = success and final_sources == frozen and budget_ok
        result.update(status="PASS_OFFLINE_CLI_CONFORMANCE" if success else "FAILED_OR_INCOMPLETE",
                      stage_acceptance=False, counters=counters, mismatched_cases=mismatches,
                      required_obligations=len(required), represented_matching_obligations=len(represented),
                      unmet_obligations=sorted(required - represented),
                      raw_capture=dict(path=str((base / "CAPTURE.json.gz").relative_to(ROOT)),
                                       stored_bytes=len(stored), stored_sha256=sha(stored),
                                       raw_bytes=len(raw), raw_sha256=sha(raw)),
                      source_hashes_after=final_sources, resources_after=budget,
                      finalization_headroom_bytes=65536, finalization_budget_check=budget_ok,
                      limitations="Finite static CLI/IO evidence only; no signatures, ownership, threshold, wallet, native or public proof.")
        write_json(base / "RESULT.json", result)
        journal.finalize(result["status"], mismatched_cases=mismatches)
        write_json(base / "EXECUTION.json", dict(status="FINALIZED", result="RESULT.json", counters=counters))
    print(json.dumps(dict(status=result["status"], counters=counters, mismatched_cases=mismatches,
                          unmet_obligations=result["unmet_obligations"], failure=result.get("failure"))))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
