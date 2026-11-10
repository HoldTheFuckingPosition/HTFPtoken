# HTFP protocol overview

This document describes the intended mechanics embodied in the local development checkpoint. Implementation and evidence coverage are recorded separately in [STATUS.md](STATUS.md). It does not select a public mint, production configuration, recipient, or deployment.

## Units and initialization

The initial supply is 10^12 HTFP at seven decimals, or 10^19 base units. Monetary calculations use integer token base units and SOL lamports, with checked wide intermediate products. No later issuance is intended.

The Token-2022 transfer fee begins at zero. An update executed at epoch E schedules 800 basis points for E + 2, with `maximum_fee = 18446744073709551615`. This removes an economic ceiling while preserving native Token-2022 integer rounding. The intended final state removes minting, freezing and fee-configuration discretion. Production initialization, metadata and authority verification remain open; a local fixture is not evidence of those public actions.

## Recover: permissionless tax collection

Recover harvests native withheld transfer fees into the program's fixed HTFP custody account. The actual verified increase is added to the accounted inventory R. An ordinary spendable HTFP donation to custody is not booked into R. Recover stores HTFP; it does not itself sell it or produce SOL.

The caller supplies the accounts to inspect but cannot redirect custody, take recovered tokens or claim a reward. The fixed program/mint/owner/PDA/account relationships and allowed aliases must be authenticated. Pending withholding on accounts not supplied remains pending. Permissionless access does not imply an automatic collector or complete discovery of all taxed accounts.

## Process: atomic burn, swap and reserve settlement

For an admissible positive quantity Q of accounted recovered HTFP, Q must be divisible by eight:

```
burn_base_units       = 3 × (Q / 8)
gross_sale_base_units = 5 × (Q / 8)
```

Processing burns the first portion and sells the second through the fixed official pool. The gross sale transfer remains subject to the HTFP transfer fee; its net pool receipt is therefore distinct from gross sale input. Actual native SOL proceeds go to the fixed HTFP reserve. A caller cannot replace the AMM, mint, custody, reserve or proceeds destination with an arbitrary account.

Accounting, burn, swap, settlement and capacity effects must commit atomically. Failure must not leave a partial burn, committed reserve credit, consumed capacity or payout. New withholding created by processing is not recursively drained within the same operation.

Processing uses the authenticated pool's current execution price and native/AMM fees. There is no mandatory historical reference price, TWAP, oracle or additional price-deviation guard in the approved design. Per-call and shared global volume controls are separate requirements; final production values, refill and initial allowance are unresolved. This design provides no manipulation-resistance or market-price guarantee.

There is no caller reward, network-fee reimbursement or operating allocation. Necessary temporary wSOL settlement may be used internally. Only the verified temporary storage deposit is returned to its payer, separately from actual native SOL proceeds.

## Redeem: holder-authorized burn against the SOL reserve

For actual token supply S before burning, authorized amount A, and spendable native SOL reserve V above required maintenance:

```
payout_lamports = floor(V × A / S)
```

Redeem burns all authorized A and pays the explicit authorized SOL destination atomically. It rejects zero output, invalid amounts and payouts below the signed minimum. It does not depend on an AMM swap or pool-opening time. An ordinary owner, a compatible program-derived owner or a valid native SPL multisig threshold can authorize redemption; delegate-only authority is insufficient.

Redeeming A = S pays all spendable V while preserving precisely required maintenance. When actual supply is zero, redemption is blocked; subsequent SOL is immobilized under the intended no-reissuance/no-sweep rules. Direct SOL received above maintenance contributes to backing while S is positive.

The ratio is a reserve-accounting mechanism. It is not an independently guaranteed market floor, a constant exchange rate, or a promise of profitability.

## Manual LGE and pool income

The founder manually receives SOL and allocates 55% of initial HTFP pro rata to contributors. Initial pool, team and separate marketing tranches are 35%, 5% and 5%. Raised SOL goes 80% to the pool and 20% to the HTFP reserve. Contributions, allocation rounding/remainders, receipts, recipients and operating budget need a final public launch ledger.

The target pool is HTFP versus SOL/wSOL through Raydium CPMM. Ordinary fees target 2500 ppm (0.25%); creator fees target 500 ppm (0.05%) in BothToken mode, for nominal combined fees of 3000 ppm (0.30%), separate from HTFP's transfer tax. The captured local fixture uses 2500/2500 ppm and does not prove availability of the final target configuration.

The intended initial LP mechanism is official Burn & Earn for 100% of LP tokens received, with the Fee Key retaining fee rights. Creator and Burn & Earn income target the same founder personal wallet; HTFP income transfers remain subject to the applicable 8% tax. These personal income streams are separate from HTFP tax custody and reserve proceeds. External AMM/locker powers and the exact Fee Key/claim lifecycle require verification.

Funding occurs during the 0% phase. Trading opens by timestamp after expected E + 2 activation and an additional margin. Four hours is only the synthetic local rehearsal value; real-network synchronization and contingency rules have not been selected.
