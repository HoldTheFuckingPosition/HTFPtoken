# HTFP M6A local snapshot API

This Python3.12 standard-library service has three GET endpoints and no blockchain connection. Its default production profile is **UNCONFIGURED**. The optional fixed profile is a **SYNTHETIC_LOCAL_HISTORICAL** M4B snapshot, never Testnet or current public data.

From the repository root, run in the foreground with bytecode disabled:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=api python3 -B -m htfp_readonly
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=api python3 -B -m htfp_readonly --profile local-historical
```

The server binds only 127.0.0.1 and chooses an ephemeral port unless a port is supplied, for example `--port 8765` (range 0..65535). Stop it with Ctrl-C; no persistent service is installed.

Endpoints are `GET /health`, `GET /v1/status`, and `GET /v1/redemption-preview?amount_base_units=...&minimum_lamports=...`. Query inputs are canonical unsigned 64-bit decimal strings; all monetary outputs and chain counters are strings. The local snapshot is digest-checked on every application request and strictly decoded before use. Missing or changed bytes make it unavailable. There is no request-selected file/profile/state/RPC or alternate evidence fallback.

Preview is arithmetic only: `V=max(0,reserve-maintenance)` and `P=floor(V*amount/supply)`. Positive amount, positive payout, amount<=supply and payout>=minimum are required. Odd amounts are allowed; no Q8 rule, token transfer tax or redemption fee is applied. Source balance, ownership, signatures, wallet/PDA/multisig policy, recipient eligibility and execution are **UNASSESSED**. The API constructs no transactions and makes no payment or freshness promise.

The fixed historical supply is 9999999994000000000 and backing 90565764 lamports. Full-supply preview gives 90565764; 110417000336 or odd 110417000337 gives 1; 1 base unit rejects with ZERO_PAYOUT. These are hypothetical requests against retained synthetic state, not wallet holdings or executable quotes. Production identities, launch parameters and volume economics remain open.

The exact contract, errors, evidence boundaries and ownership are frozen in `evidence/m6a/design/`. HTTP uses the stdlib parser; normal GET application responses are JSON, connection-close, no-store, with a 2-second socket timeout. Transport failures before a GET handler exists retain stdlib behavior. No authentication credentials or CORS are added: loopback access does not establish wallet consent.

Offline verification and the bounded HTTP campaign are documented in `tests/m6a/README.md`. No packages, native VM, signers or public network are required. Root reproduction and independent Review remain separate from author results.
