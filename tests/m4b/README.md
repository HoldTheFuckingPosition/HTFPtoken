# M4B isolated local proofs

Authority: evidence/M4B_STAGE_B_HANDOFF.md and the independently reviewed exact native-mint supplement handoff. These new drivers never implement H Process/Volume/Finalize. Kernel and restricted wallet use separate fixed public IDs/PDAs and artificial published RFC test signers only. Original H/M3 source, tests, config and evidence remain read-only.

Run from /home/jerem/htfp as jerem on weathertrades. Exact cached toolchain/dependencies only, no network/install/cleanup. Each label must be NEW; no run directory may be reused or overwritten.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages \
  /usr/bin/python3 tests/m4b/build.py NEW_BUILD_LABEL
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages \
  /usr/bin/python3 tests/m4b/run.py NEW_RUN_LABEL
```

The reviewed final helper artifact association is build-003 (kernel3067348eae5569b660cd3e0fe06b9e6afcc5bbbf953c79b6a782a6e1d32e479d; walleta19d3ae42a97cc793d95ae48b28faf44334e366f5beceb75924360fb13d41351). A separate supervisor build must explicitly verify/map its own source/build/ELF hashes before reproduction, never relabel the author's build record. New build labels do not automatically change the fixed runtime association. Default Runtime/AMM helper selection references build-003; supervisor may reproduce identical bytes independently and compare, or receive a reviewed exact path adapter. Whole source/build associations are checked, not only ELF header validity.

run.py snapshots owned source bytes, binds frozen Stage A/design/supplement/build inputs, executes all seven families sequentially, and verifies source hashes unchanged. All runtime packets are genuine signed local messages with sigverify/blockhash checks, <=1232 bytes, CU<=1400000, heap32768. No ALT is needed by new combined native settlement packets; original M3 replay includes genuine native ALT setup. No native/AMM program is stripped, trimmed, patched, substituted or rebuilt. Custom helper stripping follows the pinned existing build route only.

The native fixture is three entire captured binaries plus bundled ATA, with explicit reviewed captured82-byte canonical zero-supply nativeSOL mint as an additional static dependency. Only local Rent82 is supplied, not the public mint's lamports. All HTFP supply, token amounts, LP state, swaps, creation fee, creator collection and settlement outcomes come from genuine native instructions. Explicit malformed-state tests are rejection-only and marked as such. Zero/under-rent/exempt System0data reserve starting funding is marked SYNTHETIC_STARTING_BASELINE, never a new minimum-reserve gate or public creation proof.

The regression adapter compiles the unchanged old driver in memory with only the owned evidence output prefix and per-run output-budget prefix changed; its matching evidence-policy adapter adds only the exact new evidence root. It retains all33 methods, native fixture provenance, original artifact/source/build associations, discovery, financial/assertion/success rules and signature checks. It records the original/adapted source hashes and text. A read-only send wrapper records full messages for the788 original harness transactions plus its separate invalid-signature control (789 native send attempts total). Each M3 replay keeps the original128MiB per-run output limit; common.resources enforces256MiB for all new M4B evidence and1GiB for all owned cache/targets, including root target/m4b-*.

Precursor trial failures remain preserved with diagnoses. build-002 briefly included an unreviewed minimum reserve precondition and is explicitly superseded; build-003 restores the reviewed contract and matches build-001 kernel bytes. Only the exact final family run/source freeze is an acceptance candidate. Pure volume integer/Fraction agreement is MODEL ONLY; actual H capacity, tax-recycling and full Process integration remain Stage C obligations. External admin/custom-share positive lifecycle is NOT_RUN because genuine admin authority is unavailable; no fake signer/config/counter stand-in is accepted.
