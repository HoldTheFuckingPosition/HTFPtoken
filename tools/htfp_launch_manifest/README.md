# HTFP offline launch dossier checker

This Python3.12 standard-library command compares a supplied documentary dossier with frozen HTFP policy. It performs no network calls, public verification, signing, transaction construction or deployment.

From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m htfp_launch_manifest tools/htfp_launch_manifest/EXAMPLE.json
```

Supply exactly one explicit regular local JSON file. Reports go to stdout. Exit0 means no documentary contradiction was found; exit1 means contradictions; exit2 means invalid/unreadable input or CLI usage. **Exit0 never establishes approval, completeness or launch readiness.** Missing/provisional choices and external claims remain explicit. No quota, ledger, role or campaign configuration applies to product use.

The original reviewed schema remains in the checker. The [incomplete example](EXAMPLE.json) illustrates the documented inputs and leaves the launch identity and ledger unresolved. The current checker applies D38/S141 to all four token tranches and D39 to SOL funding. Monetary inputs are canonical unsigned 64-bit decimal strings. The command reads at most 65,537 bytes and refuses files above 65,536 bytes or nonregular devices, pipes or directories.

Each supplied tranche total must match the confirmed 55/35/5/5 allocation. Missing tranche totals remain open in draft dossiers. Funding checks use gross raised lamports. Each supplied share must be the floor or ceiling of its confirmed fraction, and two supplied shares must add up to the raised total. The rounding choice, participant ledger and remainder ownership remain open. Claimed addresses, authority removal, source hashes, URLs, receipts and approval labels remain unverified. Policy-source hashes identify the documents used to define the rules.

Run the focused current-policy regression from the repository root:

```sh
python3 -B -m unittest discover -s tests -p test_launch_manifest_policy.py -v
```

The policy hashes identify the archived specification and decision inputs.
The historical M6B campaign is retained separately.
