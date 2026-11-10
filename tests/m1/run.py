"""Run M1 tests with installed dependencies only; retain each trial separately.

From /home/jerem/htfp:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages \
/usr/bin/python3 tests/m1/run.py --out evidence/m1/<new-run-name>

No downloads, installs, RPC, key files, compilation or cleanup. Re-running needs
a NEW output directory: failed attempts are never overwritten or deleted.
"""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests/m1"))
EXPECTED_SO_SHA256 = "648e13d02ec2e8555d751e38980e01faa5cbb47c2e7d7262f3a2103caa3afa02"
BASE_COMMIT = "b331cd6898e550382ecf1160648f977e341e577b"


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact(value):
    if type(value) is int:
        return str(value)
    if isinstance(value, dict):
        return {str(k): exact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact(v) for v in value]
    return value


def write_json(path, obj):
    path.write_text(json.dumps(exact(obj), indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if not out.is_relative_to(ROOT / "evidence/m1") or out == ROOT / "evidence/m1":
        parser.error("--out must be a new subdirectory of evidence/m1")
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    stream = io.StringIO()
    report = {"base_commit": BASE_COMMIT, "result": "HARNESS_FAILED", "exit_status": 1}
    native = None
    try:
        assert Path.cwd().resolve() == ROOT, "run from repository root"
        assert sys.dont_write_bytecode, "PYTHONDONTWRITEBYTECODE=1 required"
        assert sys.version_info[:3] == (3, 12, 3), "unexpected interpreter version"
        import solders
        import native_fixture
        native = native_fixture
        from solders.litesvm import LiteSVM
        installed = {}
        for name, expected in [("solders", "0.26.0"), ("jsonalias", "0.1.1"),
                               ("typing_extensions", "4.16.0")]:
            distribution = importlib.metadata.distribution(name)
            assert distribution.version == expected, (name, distribution.version)
            installed[name] = {
                "version": distribution.version,
                "files": [{"path": str(distribution.locate_file(f)),
                           "sha256": hash_file(distribution.locate_file(f))}
                          for f in distribution.files
                          if str(f).endswith((".dist-info/METADATA", ".dist-info/RECORD"))]}
        package = Path(solders.__file__).parent
        shared_object = package / "solders.abi3.so"
        assert hash_file(shared_object) == EXPECTED_SO_SHA256, "solders native extension changed"
        svm = LiteSVM()
        program = svm.get_account(native.TOKEN_2022)
        assert program is not None
        elf_hash = native.sha256(bytes(program.data))
        assert elf_hash == native.EXPECTED_ELF_SHA256, "bundled Token-2022 ELF changed"
        sources = sorted((ROOT / "models").rglob("*.py")) + sorted((ROOT / "tests/m1").rglob("*.py"))
        source_hashes = {str(p.relative_to(ROOT)): hash_file(p) for p in sources}
        specs = {name: hash_file(ROOT / name) for name in [
            "SOURCE_INDEX.md", "DECISION_REGISTER.md", "HTFP_FUNCTIONAL_SPEC.md",
            "SECURITY_REQUIREMENTS.md", "OPEN_QUESTIONS.md", "CODEX_HANDOFF.md",
            "AGENTS.md", "evidence/M1_AUTHORIZATION.md", "evidence/M1_REVIEW_CRITERIA.txt"]}
        environment = {
            "host": platform.node(), "user": os.environ.get("USER"),
            "cwd": str(ROOT), "python_executable": sys.executable,
            "python_version": sys.version, "python_binary_sha256": hash_file(sys.executable),
            "platform": platform.platform(), "packages": installed,
            "cached_package_directory_read_only": str(package.parent),
            "PYTHONDONTWRITEBYTECODE": os.environ.get("PYTHONDONTWRITEBYTECODE"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "native_extension": {"path": str(shared_object), "sha256": hash_file(shared_object)},
            "solders_python_api_sha256": {
                p.name: hash_file(p) for p in [package / "litesvm.py", package / "solders.pyi"]},
            "token_2022": {
                "id": str(native.TOKEN_2022), "owner": str(program.owner),
                "executable": program.executable, "data_len": len(program.data),
                "magic_hex": bytes(program.data)[:4].hex(), "elf_sha256": elf_hash,
                "version": "UNKNOWN (bundled native executable)",
                "research_source_match": "UNKNOWN", "public_deployment_match": "NOT_ESTABLISHED"},
            "source_sha256": source_hashes, "spec_and_authorization_sha256": specs,
            "research_sources_index_sha256": hash_file(ROOT / "evidence/m1/sources/index.json"),
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages "
                       + "/usr/bin/python3 tests/m1/run.py --out " + str(out.relative_to(ROOT)),
            "transaction_scope": "in-process synthetic signers/accounts/sysvars only; no RPC",
            "sigverify_and_blockhash_checks": "LiteSVM defaults retained; fresh hashes used",
        }
        write_json(out / "environment.json", environment)
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/m1"), pattern="test_*.py")
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        import test_models
        report.update({
            "result": "PASS" if result.wasSuccessful() else "FAIL",
            "exit_status": 0 if result.wasSuccessful() else 1,
            "tests_run": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "skipped": len(result.skipped),
            "failure_details": [{"test": str(t), "traceback": detail} for t, detail in result.failures],
            "error_details": [{"test": str(t), "traceback": detail} for t, detail in result.errors],
            "generated_seed": test_models.SEED, "generated_case_counts": test_models.COUNTS,
            "native_transaction_count": sum(e["kind"] == "native_transaction" for e in native.EVENTS),
            "native_expected_failure_count": sum(e["kind"] == "native_transaction" and e["actual"] == "FAILURE"
                                                 for e in native.EVENTS),
            "source_sha256": source_hashes,
            "source_hashes_unchanged_during_run": all(hash_file(ROOT / p) == h for p, h in source_hashes.items()),
            "proof_scope": {
                "mathematical_model": "exact-integer finite deterministic generated/exhaustive checks",
                "native_runtime": "actual bundled Token-2022 instructions in LiteSVM 0.26.0",
                "htfp_redemption_or_processor_runtime": "NOT_IMPLEMENTED / NOT_RUN",
                "amm_integration": "NOT_RUN", "source_to_binary_match": "UNKNOWN",
                "public_network": "NOT_USED", "production_wallet_verification": "NOT_RUN",
                "independent_review": "PENDING", "founder_deliverable_acceptance": "NOT_RECORDED"},
            "limitations": [
                "Finite generated coverage with fixed seeds, no automatic shrinking; no Hypothesis/pytest dependency.",
                "Maintenance and signed minimum are model inputs; no authorization, CPI or native SOL payout proof.",
                "Native rollback is only for native mint/transfer instructions; no HTFP/AMM atomic composition.",
                "Clock epochs/slots are synthetic and not live epoch timing or launch rehearsal.",
                "Native ELF/package hashes identify local bytes, not a known Token-2022 version or public deployment.",
                "u64::MAX issuance fixture is a separate native range test, not HTFP issuance policy.",
                "All monetary integers in JSON are decimal strings or explicit hex; no private key serialization.",
            ],
        })
        if not report["source_hashes_unchanged_during_run"]:
            report.update(result="FAIL", exit_status=1)
    except Exception:
        stream.write(traceback.format_exc())
        report["harness_exception"] = traceback.format_exc()
    finally:
        if native is not None:
            write_json(out / "native_events.json", native.EVENTS)
        report["duration_seconds"] = format(time.monotonic() - start, ".6f")
        report["run_kind"] = out.name
        (out / "unittest.txt").write_text(stream.getvalue())
        write_json(out / "report.json", report)
        print(stream.getvalue(), end="")
        print(json.dumps(exact({k: report[k] for k in ["result", "exit_status"]})))
        print("Evidence: " + str(out))
    return report["exit_status"]


if __name__ == "__main__":
    raise SystemExit(main())
