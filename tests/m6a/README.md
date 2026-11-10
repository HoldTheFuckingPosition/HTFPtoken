# M6A bounded developer verification

Use Python3.12 with `PYTHONDONTWRITEBYTECODE=1 python3 -B`. There are no external dependencies, native harness imports, signers, blockchain transactions or public requests. The API product does not contain these verification counters.

From repository root, a fresh unique run records exact source copies and hashes, original-evidence preflight and results:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/m6a/run.py --run-id author-offline-001 --offline-only
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/m6a/run.py --run-id author-http-001
```

Offline checks use256 finite constructively generated positive arithmetic tuples (fixed seed0x6a20261109), independent Fraction/floor certificates, full-supply, monotonicity/remainder/minimum invariants and exact edges. Generic u64 tuples are arithmetic units, not H profile snapshots. The31 independent semantic cases preserve their observed/counterfactual distinctions; the over-profile supply case is a decoder rejection. Additional checks cover native COption inactive payloads, TLV/authorities/owners/schema, Rent/getters, strict queries and per-request fail-closed behavior. These finite checks provide no shrinking or exhaustive-domain guarantee.

The HTTP campaign uses sequential temporary127.0.0.1 servers in one process, closes listeners/threads, and records every attempt prospectively before invoking the client. Each response is retained, including failures. No retries or health discovery are hidden. `HTTP_LEDGER.jsonl` is append-only; an unfinalized ledger/run blocks later HTTP until supervisor reconciliation. The initial budgets are author256, supervisor256, global512 cumulative attempts, including probes/errors/timeouts/repeats. These limits govern this authorized verification campaign, not future human product usage. Root may use `--role supervisor`, with output in `evidence/m6a/supervisor/api_reproduction/`; it must coordinate to avoid a concurrent campaign.

`RESULT.json` distinguishes author evidence from stage acceptance. Failed runs/source snapshots remain retained. After a source change, use a new run ID; never overwrite old evidence or reset counters. Altered/missing snapshot tests mock the fixed read in memory; the packaged positive fixture stays byte-identical. The campaign covers normal GET application behavior; arbitrary malformed transports and unsupported-method stdlib behavior are outside exact JSON-shape claims. No background service is installed.

The final author `HANDOFF.json` binds the current source, all retained trials and the cumulative ledger. Root reproduction and exact independent Review are required separately.
