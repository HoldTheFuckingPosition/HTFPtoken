# HTFP production launch manifest

**Review state: incomplete.** This manifest records approved requirements and published evidence. The release artifact, launch transactions and chain-specific inputs remain unresolved.

## Confirmed requirements

| Decision | Requirement |
| --- | --- |
| D02–D05, D20, D34 | One new Token-2022 mint, seven decimals, exactly 10,000,000,000,000,000,000 base units issued once. Start at 0%. Schedule 800 bps with maximum fee `u64::MAX`, effective at the actual scheduling epoch plus two. Remove the fee-configuration authority after scheduling. |
| D06–D07, D40 and launch option A | Complete all initial distributions and fund the official pool at active 0%. Its initial available balance must receive 3,500,000,000,000,000,000 HTFP base units. No official pool swap may execute before 800 bps is active on the authenticated mint. |
| D09–D13, D19, D28, D31, D48 | Recover native withholding into canonical custody. Select a positive multiple of eight from booked inventory. Burn 3/8, sell 5/8 gross through the authenticated pool, and credit actual proceeds to the SOL reserve. Before tax, limit the gross sale to the floor of 1% of current effective HTFP reserves. A temporary storage deposit is refundable only to the extent verified. |
| D16, D22–D23, D25, D27, D32 | Holder-authorized direct burn and proportional SOL redemption from the native reserve, with an explicit minimum. Uses pre-burn supply and spendable reserve. |
| D17 | Terminal HTFP control retains code-limited PDA custody and withholding withdrawal. Mint, freeze and fee-configuration authorities are absent. Final HTFP program authority has no human upgrade, economic override, arbitrary withdrawal or discretionary pause. |
| D18, D21, D38, D45 | The founder manually distributes 55% to participants in proportion to contributed SOL, 35% to the official pool, 5% to the team and 5% to a separate marketing wallet. Exact tranche totals are 5,500,000,000,000,000,000 / 3,500,000,000,000,000,000 / 500,000,000,000,000,000 / 500,000,000,000,000,000 base units. The distributor's final HTFP balance is zero. |
| D39, D45 | The founder manually funds the 80% pool and 20% reserve shares of raised SOL. |
| D35–D37 | Lock 100% of the LP actually received for initial funding through official Burn & Earn. Use creator-enabled BothToken with 2,500 ppm trade and 500 ppm creator. Creator collection and Fee Key receipts use the same founder wallet through distinct authorities, subject to native HTFP tax where applicable. |
| D43 | Final token metadata is immutable. Review the final fields, URI, linked content and every applicable update or pointer authority before finalization. |
| D44, D48 | The bot may revise its own quantities and timing. Production processing is permissionless. The 1% on-chain gross-sale ceiling applies at every operation. There is no shared quota, refill or minimum wait. |

The reserved D33 identity is `CseQKCWvi4EA2o3oa11Age4p4xKWSLuzjWCzitASrPJu`. Its intended SOL reserve PDA is `33S4fefxDJ9Bz6KmHns37uvwcWSPQnsEyopAZ6YtJpdo`. These are recorded design bindings. Production deployment, ProgramData, authority and reserve control still require release evidence. [Project economics](../README.md#token-and-launch-design) · [Policy constants and decision identifiers](../tools/htfp_launch_manifest/policy.py)

## Release inputs

| Release field | Value and closure requirement |
| --- | --- |
| Source, Cargo lock, toolchain, features, reproducible ELF, capacity | **Unset.** Bind the reviewed production source and stripped ELF to the actual profile and deployment program. Compare with the retained [Devnet build identity](../programs/htfp-devnet-processor/README.md) as a separate reference. |
| Chain, program, reserve and authority | **Unset.** Authenticate the intended cluster, selected deployment, D33 bindings, initializer, transitional authorities, exact revocation sequence, terminal authority and reserve account state. |
| Mint and custody layout | **Unset.** Bind the one new mint, genesis preimage, extensions, mint and fee authorities, canonical custody and book inventory. Review the final metadata content and URI, verify persistent hosting of the exact linked bytes, and account for every update or redirection path. For Token-2022 inline metadata with a pointer, review the metadata update authority and the pointer authority separately. [Token-2022 metadata](https://solana.com/docs/tokens/extensions/metadata) |
| Official market and Locker | **Unset.** Bind the CPMM, selected AmmConfig, creator-enabled BothToken pool, authorities, sorted mints, vaults, LP mint, observation, create-fee account, Locker, position, escrow and Fee Key. Authenticate actual executable and config fingerprints and external powers. [Available fee profile](../evidence/cpmm_fee_profile/README.md) |
| Destinations | **Unset.** Identify public team, separate marketing, participant and funding accounts. Verify the founder's common payout owner and both creator and Fee Key authority routes. Existing Devnet wallets are pilot identities. |
| LGE rows and rounding | **Unset.** Keep a simple final integer ledger with the contribution cutoff, recipients, funded lamports and actual HTFP base units. Reconcile the four fixed token tranches and the distributor's zero remainder. Reconcile the complementary integer SOL amounts to the full raised total. Small rounding differences were accepted, with no fixed tolerance, tie rule or dust destination selected. |
| Volume controls (O04) | **Policy confirmed. Exact release evidence open.** Admit gross F at most `floor(X / 100)` for current authenticated effective HTFP reserve X. No shared bucket or pacing rule applies. Each bot can adjust its own order size and spacing. The installed Devnet bucket and 0.1% cap remain pilot-specific. [Candidate and account compatibility](../tests/production_volume/README.md) |
| Active-zero funding | **Unset.** Demonstrate a same-transaction assertion for every affected distribution and initial pool funding. Check the observed mint fee schedule and the execution-time active rate. |
| Opening (O15) | **Unset.** Require the actual fee schedule receipt and runtime/epoch anchors, an established upper bound on pre-activation execution-bank timestamps and an admitted opening time. Hold if the approved window is missed. Earlier planning targeted a few hours after activation, with four hours used only in tests. The current decision accepts a later justified opening to preserve the confirmed economics. The production margin remains unresolved. [Timing assumptions and checker](../tools/htfp_launch_manifest/OPENING.md) |

The external Token-2022 and CPMM programs retain their own upgrade and administrative boundaries. A release must authenticate their effective executable, account identities and fee settings. The Raydium admin can change status bits and config, and the opening design assumes no admin intervention. [Observed dependency roles](../evidence/cpmm_fee_profile/README.md#authority-and-configuration-boundaries)

## Launch checklist

- Freeze the four HTFP tranches, raised-SOL split, sender and receiver bindings, program artifacts, fee tier and dependency pins. Review the exact zero-fee assertions and preserved supply. Record the final reviewed metadata and persistent assets before any irreversible authority removal.
- Hold before starting the irreversible fee clock until the initial funding and opening checks are ready. Derive the activation epoch from the fee-scheduling transaction that lands and authenticate the mint's 0% and 800-bps entries.
- Require active 0% at execution for every initial distribution and pool-funding transaction. Before pool creation, verify the opening-time bound for the mint's actual scheduled epoch and prevent stale timestamp substitution. An off-chain preliminary read is evidence for planning.
- Reconcile the simple manual ledger against actual finalized distribution sums, both funded vault balances, actual initial LP issuance and the intended Burn & Earn lock. Reuse the offline dossier checker for aggregate totals, and verify the recorded opening time and release authorities against the final chain state.
- Close exact-artifact validation of Process and redemption, and qualify the Locker and both independent payout paths. Maintain the scoped historical principal diagnostic reservation.

The [offline dossier checker](../tools/htfp_launch_manifest/README.md) checks documentary consistency. The [opening analysis](../tools/htfp_launch_manifest/OPENING.md) records the assumptions needed for the execution-bank timestamp implication. Release status depends on evidence from the selected production tuple.
