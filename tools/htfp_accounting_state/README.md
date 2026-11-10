# Offline HTFP accounting-state inspector

Python 3.12 standard library only. Inspect exactly four supplied Config,
Inventory, Mint and Custody records against the fixed historical local-m3
layout and identity profile. No blockchain connection, signing, transaction,
native execution, service or instruction construction occurs.

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m htfp_accounting_state REQUEST.json
```

The request schema is `htfp-accounting-state-request-v1`, with an explicit
`profile: "LOCAL_M3_ACCOUNTING_V1"` and exactly `accounts.config`,
`accounts.inventory`, `accounts.mint`, `accounts.custody`. Each record contains
only `address`, `owner`, `executable` and lowercase `data_hex`. All four records
and fields are required. Addresses/owners are canonical Base58 32-byte keys;
executable is a JSON boolean. No caller hash, slot, verified label, lamports,
amount override, filesystem path or RPC endpoint is accepted inside a request.

The default production profile is **UNCONFIGURED**. The explicitly selected
profile retains twelve existing synthetic public identities and the historical
477-byte genesis commitment. The fixed packaged profile is checked against a
compiled exact byte-size/SHA-256 pin on each selected local request. It is not
a current Testnet/Devnet bank or a production identity selection.

The inspector reports layout-gated supplied supply, raw Inventory guard, booked
R, Custody spendable, Custody withheld and Mint withheld separately. Guard0 and1
are recognized serialized local-m3 values;1 is in-flight and grants no operation
eligibility. Guard2/3/unknown bits remain raw facts but fail the selected profile.
Nonzero withholding is permitted. Native COption None ignores inactive payload
bytes; native Pubkey, native u64 and extension nullable-key encodings remain
distinct. A malformed role can retain explicitly gated partial facts.

Only when all four roles conform does accounting compare R with Custody
spendable C. If R<=C, the report shows exact C-R with origin **UNKNOWN**. If R>C,
it reports undercoverage and no surplus; neither withholding balance rescues
coverage. Any role failure makes aggregate accounting UNASSESSED. There is no
invented R<=supply/global-conservation check, donation-origin claim, recovered
receipt estimate, active-fee calculation, R transition, backing or quote.

Exit0 means selected static conformance, exit1 means nonconformance, exit2 means
an input/profile error. Deterministic JSON plus LF is emitted on stdout; fixed
errors have empty stderr. The input must be a bounded regular file (16,384-byte
maximum), strict UTF-8 JSON without BOM, numbers or duplicate keys. IO uses
nonblocking read-only open, fstat-before-read, bounded reads and descriptor
closure. `--help` is a fixed usage error; no stdin/default/output-file mode is
provided. The source-bound contract is `evidence/m6e/design/CONTRACT.md`.

Matching supplied metadata, computing hashes or satisfying coverage does not
authenticate account ownership, bank provenance, same-bank coherence, freshness,
native reachability, signatures, authorization, a receipt or execution. Fixed
assurances remain false/UNASSESSED even for conformant reports. Arbitrary input
does not inherit the test fixtures' historical provenance.

Reusable exports are `process_bytes(bytes)`, `process_file(path)` returning
`(report, exit_code)`, and `format_report(report)` returning serialized bytes.
Imports perform no IO; returned reports share no mutable objects. The example
in `evidence/m6e/design/EXAMPLE.json` is explicitly documentary counterfactual
bytes, never genuine native evidence or known usable funds. Verification
procedures and campaign budgets belong to `tests/m6e/README.md`.
