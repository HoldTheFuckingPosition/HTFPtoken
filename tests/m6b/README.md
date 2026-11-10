# M6B finite offline verification

This developer tooling is separate from the product. Use Python3.12 with `-B` and bytecode disabled. No product module is imported by the accounting module or test runner; product checks run only through prospectively counted actual CLI subprocesses. No HTTP, native program, wallet, network or old harness is involved.

`ledger.py` exposes only stdlib accounting:

```python
journal = Journal(evidence_root, run_id, role, scan_root)
journal.begin(source_manifest_sha256="...")
attempt = journal.start_case(case_id, input_sha256="...")
# Only now invoke the CLI/helper under verification.
journal.finish_case(attempt, completed=True, exit_code=0, stdout_sha256="...", assertions="PASS")
journal.finalize("CHECKS_PASS")
```

`role` is author or supervisor; `evidence_root` is an existing assigned evidence directory; `scan_root` is the repository’s evidence/m6b directory. Its `CASE_LEDGER.jsonl` records RUN_STARTED, ATTEMPT_STARTED, ATTEMPT_FINISHED and RUN_FINALIZED. Every row has role/run_id/UTC; attempt events have attempt. Started rows are flushed/fsynced before target invocation. Public counters are attempted/completed/prior_role/prior_counts. `scan()` reads all historical CASE_LEDGER.jsonl files and refuses unfinalized runs/attempts. Coordinate one campaign/process at a time; a concurrent-start race is not a distributed lock claim.

Every help/read/parse/failure/retry/helper probe counts, with no source-generation reset. The role limit is1024 cumulative attempts; the complete authored campaign stays within128 cases. Retain input, raw stdout/stderr, exit status, sources and outcomes, including failed trials. A timeout/exception records the started attempt and failure; reconcile actual outcomes before any continuation. No hidden retries or uncounted product imports/calls are allowed. The product has no invocation quota or agent ledger.

The runner retains full raw case records losslessly gzipped at initial generation to fit the unchanged artifact budget, plus exact source snapshots and a per-run RESULT. Tests compare the40 frozen independent oracle cases, all31 fixed-policy mismatches, independent generated rational/conservation facts and parser/IO/trust boundaries. Finite coverage has no exhaustive-domain or shrinking claim. Root reproduction and exact independent Review remain separate.
