# Official pool opening at the native 8% rate

The approved launch funds the official pool at the active 0% transfer fee with 350 billion spendable HTFP. The same pool must admit no swap before the native 800-bps rate applies. Hold before fee scheduling and revocation when the prerequisites are missing. Hold before pool initialization when the opening proof or atomic zero-rate funding check is missing. Once initialized, the pool's stored time governs trading. An announcement has no effect on eligibility. A missed funding window grants no rescheduling or authority change.

**Status.** The bound is established for the pinned stable TowerBFT and stable Alpenglow profiles below and tested offline with synthetic inputs. The production runtime, identities, fee schedule, protected funding messages and opening time are still unset. The checker has no network, signer or transaction functionality. A result is conditional on the authenticated dossier and the exact program behavior. The proof addresses the rate in a bank that can execute a swap. It does not establish that an operator has already observed a finalized 800-bps bank before the first swap.

## Exact source and line reconciliation

The lightweight Agave `v4.4.1` tag resolves to `5bb304027fe1a166b02cb26dc8c161593f416fca`. The previously cited `bank.rs` lines 2446–2495 cover transaction execution and quiescing in the original bytes. The relevant function starts at line 2589. The SHA-256 values below hash the unmodified raw files at the full commit. Use the raw GitHub file at that commit to reproduce the SHA-256 and `nl -ba` excerpts.

| Source and function | Raw SHA-256 |
| --- | --- |
| [`bank.rs` · `update_clock`, 2589–2645](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/bank.rs#L2589-L2645), [`get_timestamp_estimate`, 3178–3211](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/bank.rs#L3178-L3211) and [execution path, 2127–2137](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/bank.rs#L2127-L2137) | `700acfd8b09632f1d7a4dbf28447815e77d4a1f4ec8b1cbaee8c45efc1517797` |
| [`stake_weighted_timestamp.rs` · drift clamp, 68–95](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/stake_weighted_timestamp.rs#L68-L95) | `061a84bc2f90995ae1301c2e3f525542f878ffd9d3af4f7934d52ef394a7e61e` |
| [`slot_params.rs` · inclusive nominal duration, 297 onward](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/slot_params.rs#L297) | `22adb5694fdb6ceda701389a94ec6e1f8f84f1fbe440c65e9044603b759ea86b` |
| [`block_component_processor.rs` · Alpenglow footer verification, 715–781](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/block_component_processor.rs#L715-L781) | `98acd86626de00ae6c966daed604a2ad9865bb288e2c8b064f8f3bf131c7a5b3` |
| [`solana-epoch-schedule` 3.3.0 · `src/lib.rs`, geometry and epoch/slot mapping](https://github.com/anza-xyz/solana-sdk/blob/309a177c3618c1c8e04d5c026ff9fc68195a340a/epoch-schedule/src/lib.rs#L111-L212) | `9380636f059ac95afea4c984c4954f5648a30e90bb03e3186aee9c8fec0dc1c1` |

The EpochSchedule crate archive matches the checksum in Agave's lockfile, `a1633cfd10cde127f2caf8f12021b4f8e9a425e7e4eea4326e428c422376d6fd`. Its constructor requires at least 32 slots per normal epoch. For a warm-up schedule, the first normal epoch and slot are derived from the next power of two of the epoch length. The checker validates both shapes and requires the landed scheduling slot and the Clock anchor to be in the normal regime. [Agave lockfile](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/Cargo.lock#L8308-L8312) · [Published crate](https://crates.io/crates/solana-epoch-schedule/3.3.0)

In the pinned CPMM, `InitializeV2` funds the vaults in the initializer and stores the opening time. A timestamp at or before its execution time is replaced by `now + 1`. Both exact-input and exact-output swaps require the timestamp to have arrived and the swap bit to be enabled. The swap code has no 800-bps eligibility check. The executable, config and account identities selected for release must preserve these semantics. [Pinned initializer](https://github.com/raydium-io/raydium-cp-swap/blob/3d69122790e97cd6aff24e8ba95940793773f58c/programs/cp-swap/src/instructions/initialize.rs#L267-L289) · [Exact input](https://github.com/raydium-io/raydium-cp-swap/blob/3d69122790e97cd6aff24e8ba95940793773f58c/programs/cp-swap/src/instructions/swap_base_input.rs#L75-L86) · [Exact output](https://github.com/raydium-io/raydium-cp-swap/blob/3d69122790e97cd6aff24e8ba95940793773f58c/programs/cp-swap/src/instructions/swap_base_output.rs#L13-L24)

## Mainnet status and Alpenglow implementation pins

The Solana Foundation reports activation in epoch 1064 on 21 October 2026 and the consensus handoff at slot 459,653,000. It lists the 200 ms target slot duration as live. The feature gate activated before the consensus handoff. A release reviewer must establish the actual migration and epoch/schedule state for the selected chain. The announced nominal duration and client version strings alone cannot prove the future launch interval. [Solana activation and handoff](https://solana.com/upgrades/alpenglow) · [Slot-time status](https://solana.com/upgrades) · [Solana multi-client release model](https://solana.com/news/solana-1-0-dropping-beta-and-what-comes-next)

The named stable profile uses the parent-footer Clock and terminal-footer behavior in the pinned Agave commit above and Firedancer's Mainnet v26.10.8 tag, commit `ccf8664261dc8091bc9b97ab1e7a64f91c87d6e2`. The following SHA-256 hashes cover the original Firedancer files. [Mainnet release](https://github.com/firedancer-io/firedancer/releases/tag/v26.10.8) · [Official release overview](https://solana.com/news/solana-changelog-november-12-2026)

| Source and function | Raw SHA-256 |
| --- | --- |
| [Firedancer pre-execution dispatch](https://github.com/firedancer-io/firedancer/blob/ccf8664261dc8091bc9b97ab1e7a64f91c87d6e2/src/flamenco/runtime/fd_runtime.c#L841-L859) and [footer bounds](https://github.com/firedancer-io/firedancer/blob/ccf8664261dc8091bc9b97ab1e7a64f91c87d6e2/src/flamenco/runtime/fd_runtime.c#L1822-L1892) | `f8731a5feaca737c63d5496aaa39f8d35d882e8a022f433bf64ef1d36ada9a2d` |
| [Firedancer pre-execution Clock](https://github.com/firedancer-io/firedancer/blob/ccf8664261dc8091bc9b97ab1e7a64f91c87d6e2/src/flamenco/runtime/sysvar/fd_sysvar_clock.c#L323-L349) | `54104abee212c2970ade2e3cb8d3a0808296f77174cc98fb52bddbd7208629e6` |
| [Firedancer nominal duration](https://github.com/firedancer-io/firedancer/blob/ccf8664261dc8091bc9b97ab1e7a64f91c87d6e2/src/flamenco/runtime/fd_slot_params.c#L109) | `c7eabb06b329ebb171c0171cd5b98f3aed85a515c758279f8b190c6270f93a3a` |

## Conditional proof

Let E be the epoch of the successful finalized `SetTransferFee` instruction for the official mint. Derive E from its landed slot using the authenticated cluster's epoch schedule. Verify that the mint's older rate is zero and the newer record is 800 bps with `u64::MAX` maximum fee at exactly E+2, and that its fee-configuration authority is absent. Token-2022 uses the newer fee from that epoch. [Token-2022 scheduling](https://github.com/solana-program/token-2022/blob/3350a3ba856f5997c4ade91fd1e5c8b515e5df33/program/src/extension/transfer_fee/processor.rs#L88-L111) · [Native transfer-fee semantics](https://solana.com/docs/tokens/extensions/transfer-fees)

Choose a finalized Clock anchor in E or E+1 after the schedule has landed, while the official pool is absent. Let `A` be that epoch's stored start timestamp, `T0` its current timestamp, and `r` the slot immediately before the first slot of E+2. Let `S_i` denote the first scheduled slot of epoch i. For slots `i <= j`, define

```text
U(i,j) = ceil(5 × (j - i) × proven_max_slot_duration_ns / 2,000,000,000)
```

Tower's estimator clamps the forward offset to at most 2.5 times the sum of effective nominal durations on `(i,j]`. Missing estimates and estimate regressions inherit the parent timestamp. At the first produced bank in E+1, Tower still uses the previous epoch's anchor for the estimate, then stores the result as E+1's new anchor. If boundary slots are skipped, that bank may be as late as r. Thus the inclusive upper bound B for all pre-activation descendant banks is

```text
anchor in E:     B = max(T0, A + U(S_E,r)) + U(S_E+1,r)
anchor in E+1:   B = max(T0, A + U(S_E+1,r))
```

The first term includes the reanchor and any inherited timestamp. The second covers all later banks in E+1. Skipping directly into E+2 selects the new fee immediately. With an exact stored `open_time > B`, every pre-activation swap fails the time check. Future nonnegative signed Clock seconds are ensured by the admitted nonnegative anchor and Tower's parent floor. The checker rejects a threshold that cannot be represented as a signed Clock second. A successful zero-rate initialization in this envelope also keeps the exact supplied time because its own Clock is at most B. Read back the exact stored time and vault credits as evidence after any separately authorized initialization.

Applicability requires evidence for every reachable descendant execution bank in the interval and its actual feature path. The named checker profile covers stable TowerBFT matching the pinned code. It requires a positive, externally justified nanosecond bound on nominal **per-slot** duration from the anchor epoch's scheduled origin through r. A value below the supported 400,000,000 ns floor is refused to catch common unit mistakes. There is no default. A faster configuration may supply a larger proven bound, and any duration bias or parameter change must be included in the evidence. Nominal durations are runtime parameters. Epoch duration estimates, wall time and single-node version strings do not establish coverage. Evidence also has to establish the intended chain, the authenticated anchor and market, and continuity of the Token-2022 and CPMM behavior. External executable upgrades can invalidate this claim.

### Stable Alpenglow

Anchor at a finalized bank p strictly after the first migrated bank. Use the exact accepted footer value `F(p)` in nanoseconds, associated with p and independently reconciled to its canonical finalized Clock and nanosecond clock state. For a parent h and a descendant bank s immediately building on it, each accepted footer satisfies

```text
F(s) <= min(i64::MAX, F(h) + 2 × D(h,s))
```

where `D(h,s)` sums the effective nominal nanoseconds on `(h,s]`, including skipped slots. The lower bound is the parent's value plus one nanosecond with signed saturation. On execution the child uses the parent's footer in whole seconds, while its epoch is derived from its own slot. Finalized Clock at the child's bank has the child's footer value in seconds. These values can differ. [Agave execution Clock](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/bank.rs#L2656-L2676) · [Agave terminal footer stage](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/block_component_processor.rs#L219-L234) · [Agave footer validation and write](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/block_component_processor.rs#L715-L790) · [Firedancer post-footer entry refusal](https://github.com/firedancer-io/firedancer/blob/ccf8664261dc8091bc9b97ab1e7a64f91c87d6e2/src/discof/replay/fd_sched.c#L2432-L2435)

The duration intervals telescope along every accepted chain of descendant banks. With r the last pre-activation slot and d an evidenced upper bound on each nominal slot duration in nanoseconds, an inclusive integer bound is

```text
B = floor(min(i64::MAX, F(p) + 2 × (r - p) × d) / 1,000,000,000)
open_time >= B + 1
```

This intentionally bounds even the last pre-activation bank's **own** footer, one slot looser than the parent-only execution bound. It covers skipped slots and epoch boundaries without using either epoch's timestamp anchor. For an actual funding execution observation at slot s, the checker can tighten the calculation to its latest possible parent slot s−1. A finalized post-execution timestamp or standard block-time RPC value cannot substitute for that observation. Use an authenticated execution Clock or validated parent footer for the observed bank.

The profile refuses a transition inside its bound. Agave's first Alpenglow bank can still use the legacy execution Clock and the first footer can use that as its base. The covered interval must extend from the finalized anchor through the last pre-activation slot and cover all relevant bank paths, including allowed feature changes, integer semantics and canonical ancestry. Admit d only with that evidence, including the effective timing rules on clients that can contribute accepted banks. The checker rejects duration bounds below 200,000,000 ns, a nanos/seconds mismatch, signed-nanosecond saturation that leaves no later representable opening, and an anchor too late for any later zero-rate bank. A locally named profile does not establish those production inputs. [Agave first-bank dispatch](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/bank.rs#L2123-L2139) · [First-footer fallback](https://github.com/anza-xyz/agave/blob/5bb304027fe1a166b02cb26dc8c161593f416fca/runtime/src/block_component_processor.rs#L715-L737)

## Offline use and evidence boundary

Run from the repository root.

```sh
python3 -B -m tools.htfp_launch_manifest.opening /path/to/reviewed-opening-dossier.json
python3 -B -m unittest discover -s tests -p test_opening_bound.py -v
```

Use ordinary UTF-8 JSON. Numbers are canonical decimal strings. Booleans use JSON booleans, and the explicit revoked fee authority is JSON null. Hashes are lowercase SHA-256 strings of the cited evidence. The tests provide synthetic input and an exhaustive small state-space check of skipped slots, inherited timestamps and boundary reanchoring. Their negative Clock inputs check refusal of inconsistent evidence.

| Group | Normalized input and required external verification |
| --- | --- |
| Root | `schema=HTFP_OPENING_BOUND_V1`, `genesis_hash`, `market_identity_sha256`. The market record must bind the official pool address, creator, mint order, actual CPMM config and both Token-2022/CPMM executable identities, as well as the rule for refusing prior initialization. Same-pair third-party pools have a separate approved scope. |
| `runtime` | `profile=agave-v4.4.1-stable-tower` or `agave-v4.4.1-firedancer-v26.10.8-stable-alpenglow`, `agave_commit` from the table, `max_slot_duration_ns`, `covered_from_slot`, `covered_through_slot`, `coverage_evidence_sha256`. Stable Alpenglow also needs the pinned `firedancer_commit` and `first_alpenglow_bank_slot`. Authenticate the actual applicable implementations, migration, feature activations and duration envelope for the interval. |
| `epoch_schedule` | `warmup`, `first_normal_slot`, `first_normal_epoch`, `slots_per_epoch`, `evidence_sha256`. Decode the canonical EpochSchedule from the intended chain. |
| `fee_schedule_receipt` | `landed_slot`, `signature`, `evidence_sha256`, `mint`, `successful_and_finalized`, `basis_points`, `maximum_fee_base`. Inspect the actual finalized transaction, its successful scheduling instruction, exact mint and inputs, and the reviewed fee-authority revocation. |
| `anchor` | `slot`, `epoch`, `epoch_start_timestamp_s`, `unix_timestamp_s`, `clock_evidence_sha256`, `finalized`, `official_pool_absent`. Read the canonical Clock in the finalized bank on that chain and independently establish the selected official pool's absence. For stable Alpenglow add `footer_unix_timestamp_ns` and `footer_evidence_sha256`, bound to the same finalized bank as the Clock. |
| `mint` | `address`, `program`, `decimals`, `observed_slot`, `older_basis_points`, `newer_basis_points`, `newer_epoch`, `newer_maximum_fee_base`, `fee_configuration_authority`, `evidence_sha256`. Read and verify the actual mint owner and TransferFeeConfig bytes at the same finalized anchor. |
| Optional | `proposed_open_time_s` checks the exact proposed instruction time. `funding_observation` with `slot` and `unix_timestamp_s` checks one observation against the admitted window and bound. For Alpenglow use the inherited execution timestamp of a later slot. Repeat the documented check for each relevant receipt. Preflight evidence is advisory. |

The reviewer authenticates the normalized records and their evidence references. The program checks consistency and computes a bound. A digest-format check does not authenticate RPC provenance, finality, transaction signatures, feature continuity, actual signed bytes, or the deployed executables. Exit 0 returns `CONDITIONAL_OFFLINE_BOUND` and binds the result to the normalized dossier digest. Missing, inconsistent or unsupported inputs return exit 2. Production launch eligibility stays open until the inputs and exact release behavior are verified.

## Atomic active-zero funding

Require that every affected HTFP funding or distribution transaction enforces 0% in its own execution bank. Direct distributions can use the Token-2022 `TransferCheckedWithFee` instruction with expected fee zero on each positive allocation. It calculates the actual native fee using that bank's epoch. An expected-fee mismatch aborts the transaction. A distinct SOL transfer has no HTFP mint fee, but official pool funding and initialization remain subject to the zero-rate gate. An RPC observation before a transaction cannot prevent late execution. [Native expected-fee check](https://solana.com/docs/tokens/extensions/transfer-fees)

CPMM funding uses ordinary `TransferChecked` inside its initializer. The source-supported candidate is an additional native `TransferCheckedWithFee` ahead of initialization in the **same atomic transaction**, with identical source and destination and a nonzero amount of 10,000 base units. On the inspected Token-2022 source, fee calculation and comparison on the genuine mint precede the self-transfer return. After validating the owner and other account conditions, the self-transfer returns before debiting, crediting or withholding. With a nonbinding cap the calculated fee is 0 at the old rate and 800 base units at the new rate. The comparison therefore refuses any such late initialization at 800 bps if the deployed code matches and the source remains valid. [CPMM transfer code](https://github.com/raydium-io/raydium-cp-swap/blob/3d69122790e97cd6aff24e8ba95940793773f58c/programs/cp-swap/src/utils/token.rs#L17-L42) · [Token-2022 fee and self-transfer order](https://github.com/solana-program/token-2022/blob/3350a3ba856f5997c4ade91fd1e5c8b515e5df33/program/src/processor.rs#L351-L490) · [Solana transaction atomicity](https://solana.com/docs/core/transactions)

The exact Token-2022 processor source at `3350a3ba856f5997c4ade91fd1e5c8b515e5df33` has raw SHA-256 `521f56eef21ef07ac6991eef04ded4966fd79f3b13618bf42c8be837da296aeb`. This source analysis still requires exact release evidence. Verify the deployed Token-2022 image and mint layout, source ownership and balance for the assertion before funding, account meta duplication and extensions, instruction order, exact signed message and packet limits, zero balance/withholding movement from the assertion, successful 0% credits, and whole-transaction refusal when the active rate is 800 bps. No alternate signer or mint authority is introduced by this proposal. Until those checks and the runtime bound are established for release, leave the official pool uninitialized.

### Wire-size feasibility

A single-authority expected-fee assertion has 19 instruction-data bytes (two discriminators, eight amount bytes, one decimal byte, eight expected-fee bytes), four compiled account indices including the duplicate source, and three one-byte compiled instruction fields. It adds 26 bytes when the existing packet already has the Token-2022 program, source, mint and signer, and no compact-array length crosses an encoding boundary. The retained Devnet initializer shape finalized at slot 522002353 had one signer, 21 static keys, three instructions and 847 bytes. The corresponding size-only calculation is 873 bytes, below the legacy 1,232-byte limit. This calculation establishes space on that shape. Mainnet may select a different pool-state signer, account set, lookup scheme or transaction version. Check its actual complete message, signer requirements, compute and transaction success or rollback separately. [Token-2022 expected-fee instruction format](https://github.com/solana-program/token-2022/blob/3350a3ba856f5997c4ade91fd1e5c8b515e5df33/program/src/extension/transfer_fee/instruction.rs) · [Solana transaction wire format](https://solana.com/docs/core/transactions/transaction-structure)
