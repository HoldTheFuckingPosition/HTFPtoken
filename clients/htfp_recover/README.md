# Offline Recover descriptor codec

This Python 3.12 stdlib client encodes or inspects the eight-byte Recover
instruction and its ordered account descriptor. It creates no transaction,
message, signature, network request or service. It does not discover accounts,
split batches, estimate recovered tax or assess execution eligibility.

Run from the repository root with one explicit regular request file:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=clients python3 -B -m htfp_recover REQUEST.json
```

A minimal local historical request is:

```json
{
  "schema": "htfp-recover-request-v1",
  "operation": "encode",
  "profile": "LOCAL_M3_HISTORICAL_V1",
  "intent": {"sources": []}
}
```

The empty list is valid and makes no claim about an actual recovered amount.
Supply an explicit ordered list of up to 32 canonical Base58 32-byte public
keys to encode source accounts. There are no holder or outer tax-authority
signer requirements in this local Recover ABI. A public key is not ownership,
consent or native account-state evidence.

For inspection, use `operation: "decode"` and replace `intent` with
`descriptor`, containing `program_id`, ordered `accounts` and lowercase
`data_hex`. Each account has exactly `pubkey`, `is_signer` and `is_writable`.
Inspection preserves order and supplied flags; effective privileges are ORed
by actual public key. Required writable privileges are minima. Wrong fixed
identities, fixed duplicates, protected sources, source duplicates and missing
effective privileges are reported separately. No count override is accepted.

The default profile is `UNCONFIGURED`: omitting the explicit local profile
returns an error. The packaged profile is authenticated against a compiled
size/SHA-256 pin on every local request. Its nine identities and source bindings
describe a synthetic historical fixture, never current public Testnet/Devnet
state or a production default. No request or environment variable selects a
profile file or RPC endpoint.

Requests are strict UTF-8 JSON without numeric literals, duplicate keys or BOM,
limited to 16,384 bytes and the fixed schema. Only the explicit regular input
and fixed regular profile are read, using bounded nonblocking descriptor IO.
Reports are deterministic JSON plus LF on stdout; fixed errors use empty
stderr. Exit codes are 0 for static conformance, 1 for static nonconformance
and 2 for input/profile errors. `--help` is a fixed usage error.

The reusable API exports `process_bytes(raw: bytes)`, `process_file(path)` and
`format_report(report)`. The first two return `(report, exit_code)`; the last
serializes an unmodified returned report. Calls do not share mutable report
objects. Imports perform no IO.

Static conformance does not verify source owners, mints, extensions, frozen
state, withholding, Inventory guards, custody/R coverage, an actual receipt,
packet fit, signatures or future execution. All such report assessments remain
`UNASSESSED`; authorization, signature, receipt and execution assertions remain
false. The frozen contract is `evidence/m6d/design/CONTRACT.md`.
