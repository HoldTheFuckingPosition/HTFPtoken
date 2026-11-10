# HTFP offline launch dossier checker

This Python3.12 standard-library command compares a supplied documentary dossier with frozen HTFP policy. It performs no network calls, public verification, signing, transaction construction or deployment.

From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m htfp_launch_manifest evidence/m6b/design/revision-001/EXAMPLE.json
```

Supply exactly one explicit regular local JSON file. Reports go to stdout. Exit0 means no documentary contradiction was found; exit1 means contradictions; exit2 means invalid/unreadable input or CLI usage. **Exit0 never establishes approval, completeness or launch readiness.** Missing/provisional choices and external claims remain explicit. No quota, ledger, role or campaign configuration applies to product use.

The reviewed schema, exact fields/messages/source references and incomplete example are frozen in `evidence/m6b/design/revision-001/`. Monetary inputs are canonical unsigned64-bit decimal strings. The example is documentary intent with unresolved nulls, not a production genesis or selected public mint. The command reads at most65537 bytes and refuses files above65536 bytes or nonregular devices/pipes/directories.

Partial allocation shortfall is distinct from an asserted completed allocation. Funding checks use gross raised lamports, preserving unresolved80/20 rounding; they never subtract maintenance or choose a remainder destination. Claimed addresses, authority removal, source hashes, URLs, receipts and approval labels remain unverified. M5/deferred work and production choices are not resolved by this checker. Exact policy-source hashes describe embodied rules, not verification of current local files or blockchain state.

Verification accounting belongs only to `tests/m6b/` and the assigned agent evidence, separately from this command.
