# M3 local runtime reproduction

Run from `/home/jerem/htfp` on `weathertrades` as `jerem`. Use the existing cached tools/packages only. Each command's output directory must be new; prior trials are retained unchanged.

The captured candidate artifacts are:

- `evidence/m3/author/correction-001/build-local/htfp.so` — `local-m3`.
- `evidence/m3/author/correction-001/build-default/htfp.so` — default disabled.
- `evidence/m3/author/build-helper-003/pda_wallet.so` — authenticated test-only PDA caller.

Build fresh captures, if assigned, with separate sequential commands:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 tests/m3/build.py reproduce-local local-m3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 tests/m3/build.py reproduce-default ''
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 tests/m3/build.py reproduce-helper local-m3 helper
```

The driver runs installed platform Cargo directly, offline/locked/single-job, with owned cache/target directories. It captures raw and stripped ELF files, tool/input/output hashes, commands and exit statuses. Installed `llvm-objcopy --strip-all` produces the actual loaded artifact. No packaging wrapper, keypair file, rustup, install or download is involved. Resource limits are1GiB for the owned cache plus target and a2GiB free-disk floor.

Reproduce the bundled baseline comparison without rebuilding:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages /usr/bin/python3 tests/m3/run.py --out evidence/m3/supervisor/reproduce-candidate --elf evidence/m3/author/correction-001/build-local/htfp.so --default-elf evidence/m3/author/correction-001/build-default/htfp.so --helper-elf evidence/m3/author/build-helper-003/pda_wallet.so
```

The default bundled fixture must retain **exit1/FAIL**,33methods, two required-success legacy multisig subcase failures in one method,0errors/skips. Direct controls are fresh separate VMs, so successful burns cannot consume later HTFP redemption inputs.

Select the fixed captured Testnet fixture explicitly (fresh output directory):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages /usr/bin/python3 tests/m3/run.py --out evidence/m3/supervisor/reproduce-captured-target --elf evidence/m3/author/correction-001/build-local/htfp.so --default-elf evidence/m3/author/correction-001/build-default/htfp.so --helper-elf evidence/m3/author/build-helper-003/pda_wallet.so --native-fixture testnet-capture-462242918
```

Expected captured result: **exit0/PASS**,33methods/788transactions/0failures/errors/skips,93expected negative transaction outcomes. All four direct and four HTFP multisig positive profiles succeed. The full691008unmodified bytes, including79952padding bytes, are pinned with capture provenance by config/m3/native_fixture.json; the captured dependency is never stripped or fetched during tests. Every VM verifies the bundled constructor then selected native account bytes/owner. No arbitrary native ELF path or fallback exists.

`run.py` requires successful build associations for all three profiles, current source/input hashes and exact ELF hashes before loading validated bytes. It rejects zero-test or skipped suites and checks source/artifact stability after execution. `report.json`, `environment.json`, `unittest.txt` and `events.json` retain actual outcomes. Event records contain exact integer strings, instruction metas/data, native/custom logs, signatures, packet sizes, CU, raw/decoded account snapshots and rollback checks. No test key is serialized.

The runtime explicitly enables signature and recent-blockhash verification. A corrupted-signature control proves native rejection without state or fees changing. All genuine instruction-execution failures verify rollback of tracked protocol/source/destination accounts; only actual native transaction fees are excluded. Synthetic clocks/funding are local setup. Explicit malformed-state, under-rent, stale-option or overflow mutations are labelled separately from native-created monetary state.

The32-source recovery uses a genuinely created/extended native lookup table and a signed v0 transaction. Its actual packet is360bytes and consumption211991CU for bundled and147386CU for captured under an explicit400000CU budget. Parser bookkeeping uses bounded arrays/digests and preallocated source/CPI vectors after the earlier full-batch heap failure. No runtime heap enlargement or reduced source cap is used.

Generated checks use fixed standard-library seeds and independent integer/conservation inequalities:48 redemption transitions and six recovery checkpoints across24 native transfers. This is bounded deterministic coverage without automatic shrinking. Native binary source/version matching, public deployment, production genesis, Process/AMM/volume behavior and independent review are not established by these tests.

Current correction evidence is `evidence/m3/author/correction-001/HANDOFF.json`; supervisor reproduction is `evidence/M3_SUPERVISOR_REPRODUCTION_002.json`. Native multisig classification precedes kind0, with30negative classification cases and four additional supervisor threshold negatives. Earlier build-local-004/default-003 captures remain historical and no longer match current Rust inputs. Supervisor updates to this README are documentation only; executable input hashes remain those recorded at the corrected code/test freeze.

Current fixture source/test freeze:e39f7b6e732649ee5d178c06c4e4aed6ea9ac0d1. Author handback:evidence/m3/author/native-target/HANDOFF.json. Separate supervisor replay:evidence/M3_NATIVE_SUPERVISOR_REPRODUCTION.json; raw audit:evidence/M3_NATIVE_CAPTURED_RAW_AUDIT.json. Historical correction001failures remain evidence for the original bundled binary. Exact integrated independent Review PASS closes bounded LOCAL M3; see evidence/M3_NATIVE_FINAL_REVIEW.json.
