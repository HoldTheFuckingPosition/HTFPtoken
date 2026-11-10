# Local BothToken processing integration

The new `programs/htfp-both` crate implements the reviewed S154/S156/S157 local
fixture. It leaves the original program, configuration, helpers and all older
artifacts unchanged. Production defaults remain disabled. `local-m3` and
`local-both` cannot be enabled together.

The explicit profile fixes the artificial M3 mint/program/genesis and captured
CPMM config0/pool. BothToken uses input-side creator fees, with historical
2500ppm trade plus2500ppm creator; this does not validate final creator500ppm.
Native full code and config bytes are read from retained references. H is a
fresh independently buildable artifact of the new crate. No public RPC,
deployment, signing service, actual wallet files or locker/BurnAndEarn/M5 task
is used.

From `/home/jerem/htfp`, use the installed Python and cached packages:

```
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/processing_both/build.py --role author --label build-both-002 --feature local-both
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/jerem/htfpo-v1/.venv/packages python3 -B tests/processing_both/campaign.py --role author --label native-001 --build evidence/processing_both/author/build-both-002/build.json
```

Existing labels cannot be reused. These are concrete command forms, not a
request to rerun a sealed campaign. The build command uses the direct pinned
platform1.54 Cargo/Rust1.89, offline/locked/jobs1 and the existing read-only
package-source/archive closure. New target output is role-specific. A build
ledger records every attempt, including the expected invalid-feature failure.

The native driver subclasses/imports only SHA-pinned reviewed LGE and fee-flow
helpers. New constructors, VM loader, send/payer/CU handling, caps, namespaces,
journals and final arithmetic replace incompatible inherited behavior without
monkeypatching old modules. Three unrelated ephemeral caller keypairs exist only
in memory. Their funding is operational and outside the 11SOL manual LGE. An
ordinary Process or Recover is genuinely paid and signed by the relevant caller
without an initializer co-signature. Combined two-caller/holder transactions
explicitly record all necessary signatures and fees.

The finite matrix and chronology are frozen under
`evidence/processing_both/design/` with ROOT's explicit alignment. Main produces
an immutable coherent final state; two later fresh VMs replay the genuine prefix
using the same in-memory role objects/t0 and compare raw prestate to the main
calibration before their deliberate CU cuts. No positive monetary snapshot is
copied, and no extra calibration search is assigned. Current material
precondition dispositions, if any, must be separately reviewed and retained
before dependent native execution.

Every run records source snapshots and hashes before its VM, actual post-load
program getters, full signed packets/messages/signatures/compiled reach,
requested and actual CU, logs and native inner instructions, all raw tracked
before/after accounts, actual Clock/Rent getters and bytes, and prospective
fsynced RUN/VM/SEND events. `COVERAGE.json` maps semantic IDs to actual packet
ordinals/hashes, or explicit source-only/final-phase records. Monetary raw
conservation deduplicates aliases by address. Immediate post-close state is
verified by H's actual reborrow/check/log; final host getters independently show
restored Temp. A host getter during an instruction is not claimed.

`RESULT.json` contains actual role-prior/cumulative attempts and lossless gzip
stored/raw hashes; `REPORT.json` contains bounded run assertions. Failed and
superseded attempts remain immutable and counted. The limit is6VM/400 explicit
signed submissions per role across generations; planned3VM/280. Synthetic
airdrop API calls count separately, with possible runtime-internal transfer
execution disclosed. Evidence<=48MiB, combined new targets<=1GiB, free>=2GiB.

No author result alone establishes acceptance. ROOT must separately build and
replay the exact final source after author seal, the independent auditor must
reconcile raw evidence and semantic controls, and final independent review must
pass. Successful alpha equality is infeasible under this fixed large pool and
small global bucket; callbacks and several structural/frame variants stay
source-only/NOT_RUN. New withholding left at unselected accounts is pending;
R is booked selected tax, Custody also includes an unbooked920-base-unit donation.
Native public/source/validator equivalence and final production economics remain
unproven.

The reviewed local P=1 case uses genuine native prefunding and restoration, with
no injected positive state or Rent changes. Pinned upstream LiteSVM rent checking
has an empty-data-account exception; correspondence of that source to the
installed binary remains UNKNOWN until the actual local result. Even a local
P=1 success does not prove compatibility with public validator rent rules for
new System accounts below Rent.minimum_balance(0).
