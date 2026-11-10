# Standalone local LGE and native CPMM bootstrap

Authority: the reviewed exact `evidence/LGE_POOL_TEST_SCOPE.md` (SHA256
`3cf337bc3c7d03d7c9ec4e04e5908dd31a3613106f078ca573f7cb1cb02346c8`),
plus the supervisor-reviewed post-main counterfactual clock clarification.
This new adapter imports installed solders and standard-library modules only.
It never imports or invokes an old harness, H, a locker, an API or a network.

Run serially from `/home/jerem/htfp` on weathertrades as jerem:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages \
  /usr/bin/python3 -B tests/lge_pool/native_rehearsal.py --role author --label NEW_LABEL
```

The separate supervisor uses the same final source with `--role supervisor`
only after the author has frozen its handback. Outputs are restricted to NEW
`evidence/lge_pool/native_author/LABEL/` or `native_supervisor/LABEL/`.
No existing run is overwritten. Every VM and every explicit signed native send
has a prospectively appended, fsynced `CASE_LEDGER.jsonl` entry. All prior
role attempts, including failures, consume the unchanged 3 VM / 200 send caps.
A failed or unclosed run requires diagnosis; it cannot be silently ignored.
The synthetic SOL airdrop is a separately journaled/counted API call; possible
LiteSVM internal execution is not mislabeled as an explicit signed-send packet.

The fixture uses ephemeral in-memory signers whose private material is never
printed or exported. Five native SOL contributions total eleven SOL. Exact
55/35/5/5 token allocations and the 8.8/2.2 SOL pool/reserve split are independently
specified in `PLAN.json`; the integer planner is not imported. The operations
wallet supplies separate mint/ATA/account rent, native transaction fees, the
creator's explicit one-SOL operational top-up, and a post-allocation trader
budget. Eleven contributed SOL are never reduced by those costs.

The genuine historical CPMM/Token2022/legacy binaries are loaded unchanged by
reference to `config/m4b/native_fixture.json`; actual executable getters and
the bundled ATA bytes are verified. The only synthetic nonmonetary dependencies
are the exact captured zero-supply native SOL mint bytes, unchanged captured
config0, and rent-funded zero-filled fee-receiver storage subsequently initialized
by native Token instructions. No positive token balance or pool/LP state is
injected. Mint issuance, distribution, wrapping, pool initialization and swaps
execute through genuine native instructions. H must remain absent throughout.

InitializeV2 constructs the actual token ordering, nineteen metas, three u64LE
arguments and `Some(BothToken)` suffix `0100`. Config0 is the unchanged experimental
2500/2500 ppm configuration, not final 2500/500. The initial LP receipt is
`isqrt(8800000000*3500000000000000000)-100 = 175499287747742`.
All LP is retained without a burn or Burn & Earn claim.

The main chronology is E setup, E+1 native zero-fee transfer, E+2 native 800bps
transfer while the pool is closed, pre-opening rejection, then exact-opening
buy and sell with native withholding and separate creator/protocol/fund
liabilities. Negative sends must preserve raw tracked state except the actual
fee payer's network fee. Every explicit send retains the complete signed packet,
message, instruction descriptors, inner-instruction metadata, logs and raw
before/after account bytes in lossless `events.jsonl.gz`.

`MAIN_FINAL_SNAPSHOT.json` and `MAIN_ACCEPTANCE.json` are written and journaled
before the separately labeled counterfactual. Only afterward is the synthetic
epoch rewound to E+1 while timestamp and slot advance; an actual native CPMM
swap then demonstrates zero native tax despite an open timestamp. Its separate
`COUNTERFACTUAL*` files explicitly say `NON_REAL_BANK_CHRONOLOGY`; that bank is
never substituted for the main final state. Neither the four-hour delay nor
this counterfactual predicts real-network epoch timing.

Resource checks enforce all new LGE evidence <=16 MiB and free disk >=2 GiB.
No binary copies, builds, installations, real keys or public writes occur.
Results are local engineering evidence only (`stage_acceptance:false`), pending
separate supervisor reproduction and independent review. They do not establish
source-to-public-binary equivalence, current public state, final creator500ppm,
H initialization/Recover/Redeem/Process, locker/full M5 acceptance or deployment.
