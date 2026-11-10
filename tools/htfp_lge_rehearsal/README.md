# Manual LGE rehearsal allocation planner

Python3.12 stdlib, **LOCAL_TEST_ONLY**. From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/htfp_lge_rehearsal/plan.py
```

The default prints the approved five-contributor fixture:0.5,1,2,3,4.5 synthetic
SOL,11 total. Fixed supply is10^19 base units at seven decimals. Participants
receive55%, pool35%, team5% and a separate marketing role5%. Literal participant
amounts are25/50/100/150/225 billion whole HTFP;2.2SOL funds the canonical reserve
and8.8SOL the pool. The fixture has no rounding residue. All monetary JSON fields
are decimal strings, never floats. This is an allocation plan, not proof of funds.

For the independently authored native rehearsal:

```python
from tools.htfp_lge_rehearsal import fixture, make_plan
plan = make_plan(fixture())
pool_tokens = int(plan["token_allocations_base_units"]["pool"])
pool_lamports = int(plan["sol_allocations_lamports"]["pool"])
reserve_lamports = int(plan["sol_allocations_lamports"]["reserve"])
```

`fixture()` returns a fresh list of `(participant_id, contribution_lamports)`
pairs. `make_plan` accepts a nonempty list/tuple of such pairs with positive exact
integer weights and unique nonempty string IDs. It does not mutate input and
returns fresh objects, sorting participant output by ID. These are test labels,
not public-key or wallet selections. Integers are mathematical; a native adapter
must check native resource/range limits separately.

Pro-rata ideals use the fixed55% tranche. Test-only indivisible allocations use
floors, then award one-unit residuals by greatest fractional numerator and
lexicographically ascending ID for ties. Returned rows expose floor, numerator
(denominator=total contribution), bonus and final allocation. This conserves
the tranche and keeps each allocation less than one base unit from its ideal.
SOL test rounding gives `floor(total_lamports/5)` to reserve and the remainder
to pool. Neither rounding convention selects the final public rounding policy.
D19's multiple-of-eight requirement applies to tax processing, not distributions.

Operations funding, rent, CPMM creation and transaction fees must be separately
funded and reconciled in a native test; none reduces contributed SOL allocations.
Native mint authority/scheduling, pool creation, LP receipts and real taxed
transfers are outside this pure planner. The new native adapter is separately
owned; the planner imports no existing HTFP/native harness or locker module.

The test-only opening rule is synthetic E+2 boundary plus14,400 seconds. The
planner supplies no real epoch duration, wall-clock date, current fee or pool
readiness guarantee. Existing native supply/authority, 0% distribution and actual
epoch activation must be observed separately. For a later integrated HTFP launch,
HTFP Initialize must precede distribution; this pure planner does not execute it.
The approved native pool fixture uses unchanged historical2500/2500 config0 and
retains initial LP for the isolated experiment; it does not prove final2500/500
or Burn & Earn requirements. Deferred M5 is untouched.

Scope: `evidence/LGE_POOL_TEST_SCOPE.md`. Finite invariant verification is in
`tests/lge_pool/test_allocation.py`; no dependencies, signing, actual keys,
network, VM, deployment, fund movement or public actions are performed here.
