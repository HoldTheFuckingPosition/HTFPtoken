# Integrated local native fee lifecycle

Authority is the independently reviewed `evidence/FEE_LIFECYCLE_SCOPE.md`,
SHA256 `1be67d272968223770801e46143cb3892a3af2463fda62b3cc4ef7b475c814b3`.
This new driver imports the two exact frozen LGE modules by SHA, without editing
or monkeypatching them. No old CLI, M3/M4B harness, locker or deferred M5 code is
imported or executed. No new Rust build, installation, public network or real
key file is used.

Run serially from `/home/jerem/htfp` on weathertrades as jerem:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages \
 /usr/bin/python3 -B tests/fee_lifecycle/native_flow.py --role author --label NEW_LABEL
```

The supervisor uses `--role supervisor` after the exact author source is frozen.
All output is NEW `evidence/fee_lifecycle/ROLE/LABEL/`. Every VM/send has a
prospective fsynced ledger entry; retained prior role attempts count toward
3 VM / 160 explicit signed sends. Synthetic airdrop API calls are counted
separately, with no assertion about implementation-internal transfers. The
16 MiB new evidence cap and 2 GiB disk floor are checked throughout. Failed
campaigns remain present; an unclosed campaign cannot be skipped silently.

Only the already published RFC8032 artificial initializer/mint/genesis-owner
vectors are used for the fixed immutable local-M3 profile. Other fake wallets
are ephemeral. Signing material is never exported. H's existing current-source
155240-byte local-m3 ELF is read by reference, build/source pins checked, and
actual executable bytes verified after loading. H metadata/hashes are retained;
its executable bytes are not copied into every monetary snapshot.

Native genesis uses the exact seeded 178-byte GenesisHolding, with the entire
initial supply there before genuine H Initialize. Only afterward are tokens
moved under 0% into the founder ATA and distributed. The imported LGE bootstrap
preserves 55/35/5/5, 8.8/2.2 SOL funding and independent operational costs.
The captured config remains experimental 2500/2500 ppm BothToken; final500ppm
is not substituted or validated. LP is retained, without any Burn & Earn claim.

The coherent epoch7 ->8 ->9 scenario tests exact-opening native swaps, literal
active-tax transfers of 1, 1001 and 1000000007 base units, H batch recovery and
idempotence, permissionless native harvest followed by genuine H n0 recovery,
and the Custody donation boundary. Creator fees are genuinely collected in both
assets to ATAs of the same founder. The HTFP receipt pays 8% native tax, then H
recovers that withholding. A native close unwraps only that founder wSOL claim;
the returned account rent is separated from income. NoFeeCollect, invalid
Recover, unauthorized withdrawal and excess-minimum Redeem are real rejections
whose raw rollback excludes only the actual network fee. A successful ordinary
owner Redeem independently checks floor(V*A/S), queried Rent, actual burn and
native SOL payout, leaving Custody/R and LP unchanged.

`events.jsonl.gz` is lossless UTF-8 JSONL using the frozen LGE raw transaction
schema: full signed packets, instruction/meta descriptors, raw inner metadata,
logs, and complete tracked before/after account bytes. `CASE_LEDGER.jsonl` is
durable and prospective. `INPUTS.json` binds all reused/new source, native
programs, build/profile and authority inputs. Named `PHASE_*.json` files retain
raw monetary states and H metadata; `REPORT.json` contains claimed arithmetic
certificates for an independent auditor to check against raw rows. Those claims
are not substitutes for raw evidence. `RESULT.json` binds stored/raw trace hashes
and cumulative counts. `IDENTITIES.json` records public role associations only.

Recover credits HTFP spendable Custody and R, not native SOL. Creator revenue,
native withholding, unbooked donation surplus, protocol/fund liabilities, backing,
LP and operating costs remain distinct. Results have `stage_acceptance:false`
until separate supervisor replay and independent Review; no source/public-runtime,
production, Process, Burn & Earn or deferred/full-M5 acceptance follows.
