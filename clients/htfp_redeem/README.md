# Offline Redeem descriptor codec

Python3.12 standard library only. Prepare or inspect the existing56-byte HTFP Redeem instruction descriptor without constructing a transaction, signing, consulting balances or contacting a network.

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=clients python3 -B -m htfp_redeem REQUEST.json
```

The command reads one explicit bounded regular JSON file and prints one deterministic JSON report. Exit0 means static descriptor/declared-intent conformance; exit1 means nonconformant or unresolved intent; exit2 means an input/profile error. There is no help mode, stdin/default request, output-file or network option. An omitted/null/UNCONFIGURED profile fails closed. Only the explicit `LOCAL_M3_HISTORICAL_V1` profile is available; production is UNCONFIGURED. Its fixed public identities are synthetic historical local fixtures, not current Testnet/Devnet accounts or deployment instructions. The packaged PROFILE.json is authenticated against a compiled size/SHA256 on each selected local request.

Encode request:

```json
{
  "schema": "htfp-redeem-request-v1",
  "operation": "encode",
  "profile": "LOCAL_M3_HISTORICAL_V1",
  "intent": {
    "source": "37mc4KkGAPZGv3CG3xNfW7azVbDziDsRLUo4QtAMYV4q",
    "authority": "Hyx62wPQGyvXCoihZq1BrbUjBRh2LuNxWiiqMkfAuSZr",
    "recipient": "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z",
    "amount_base_units": "9",
    "minimum_lamports": "0",
    "authorization_route": "owner",
    "signers": []
  }
}
```

These explicit example keys/values are never defaults or known usable funds. Amount/minimum are canonical decimal u64 strings; public keys are canonical Base58/32bytes. Positive odd amounts are allowed. No redemption tax, Q8 restriction, payout quote or recommended minimum is computed. Encode requires every intent field. An invalid intent, including amount0 or kind1 with no signers, emits no descriptor.

Decode replaces intent with `descriptor:{program_id,accounts,data_hex}` and an explicit `route_claim`. Accounts are ordered `{pubkey,is_signer,is_writable}` entries; data_hex is lowercase hexadecimal. Route_claim is owner/pda/native_multisig or explicit null. Body kind0 cannot distinguish owner from PDA; a null claim remains UNRESOLVED. The decoder retains amount0/count0 fields losslessly with invalid-intent findings rather than treating them as successful redemption. Kind1 supplied count is not the threshold or configured membership count.

Required flags are invocation minima after per-key privilege union, including permitted external aliases. Extra flags and raw occurrence order are preserved by decode. Fixed protected protocol keys are rejected in external roles. The tool has no account owner/data/executable information; it neither requires a System-owned recipient nor proves actual recipient eligibility, ownership, PDA wallet policy, native membership/threshold, signatures or consent. All such assessments remain UNASSESSED and authorization_verified/execution_guaranteed are always false. No conformant result is an execution receipt or production readiness claim.

Reusable entrypoints have the same contract:

```python
from htfp_redeem import process_bytes, process_file, format_report
report, exit_code = process_bytes(exact_request_bytes)
# process_file(path) additionally performs bounded nonblocking regular-file IO.
stdout_bytes = format_report(report)
```

Importing the package performs no file IO or writes. The exact reviewed request/report/catalog and scope are in evidence/m6c/design/CONTRACT.md and REQUIREMENTS.json. Verification procedures and campaign accounting belong to tests/m6c/README.md, not the product API.
