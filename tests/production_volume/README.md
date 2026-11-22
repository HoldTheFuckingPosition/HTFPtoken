# Local production volume-policy candidate

D48 fixes the on-chain limit at `F <= floor(X / 100)`. Each `Process` reads
the authenticated official pool, its HTFP vault's spendable amount and all
three fee liabilities. It compares the gross sale `F = 5 × (Q/8)` before
native transfer tax. Q is caller-selected and subject to the existing
positive, multiple-of-eight and booked-inventory checks. The ceiling
measures token volume. Spot-price movement, average execution price and
slippage from a prior quote are distinct measures. The bot can select
smaller lots and its own intervals. Other callers may proceed immediately.

The `production-volume-policy` feature selects the candidate handler
policy with an explicit compile-time binding. Its official-market fee
values are 2,500/500 ppm in BothToken. An isolated fixture retains the
historical genesis-side bindings and the observed pinned CPI images and
AmmConfig. A launch release needs its own selected mint/genesis profile,
official pool and dependencies. The `devnet-tax-processor` feature keeps
the legacy admission rules and binding. Combining the two profiles fails
compilation.

## State and wire compatibility

Process, InitializeProcessing and Finalize retain their tags, account
order and instruction lengths. The Volume PDA seeds and 89-byte layout
remain. The production binding uses `HTFP_TAX_PRD_V02`, schema 2 and a new
commitment. Its quota-specific preimage bytes 1096 through 1127 are zero.
The fixture retains both initial-vault fields as binding data.

The account uses `HTFPVOL2` and version 2. Bytes 43 through 58, formerly
credit and last-refill time, are reserved zero bytes. The old version,
nonzero reserved bytes and wrong commitments are refused. A fresh
production initialization creates the new account. No conversion of
legacy Devnet state is provided. Events keep their former lengths and
use zero for the retired quota words. Production clients should use
the new profile commitment and treat those positions as reserved.

The sequence, per-call temporary PDA and terminal top-level Finalize
remain active. Two calls may share one Finalize with the initial
call's nonce and distinct sequence-based temporary accounts. Each
call obtains the reserves after earlier operations in the same
transaction. Any failure rolls back the whole transaction. Verify
exact rent, native tax, custody, burn and reserve deltas on the
selected release.

## Reproduce the focused local evidence

Use the locked crate and platform-tools v1.54 from the
[Devnet build guide](../../programs/htfp-devnet-processor/README.md).
Supply the retained November 19 2,500/500 fixture root separately.
The fixture generator verifies its source and binding digests. The
runtime test verifies the existing fixture loader, source state and
CPI images before use. The only new state assumptions are isolated
synthetic inventory and reserve balances that make the exact limits
observable. Runtime transaction signatures are zero bytes, with
signature checks and duplicate-signature history disabled. The
program's replay and settlement checks still execute as native code.

```sh
fixture=${HTFP_RETAINED_CPMM_FIXTURE:?Set the November 19 retained fixture root}
build_dir=$(mktemp -d)
export HTFP_PRODUCTION_POLICY_PROFILE="$build_dir/profile.rs"
export CARGO_TARGET_DIR="$build_dir/target"
python3 -B tests/production_volume/prepare_profile.py \
  --fixture-root "$fixture" --output "$HTFP_PRODUCTION_POLICY_PROFILE"
cargo test --locked --offline --no-default-features --features production-volume-policy \
  --manifest-path programs/htfp-devnet-processor/Cargo.toml --lib --target x86_64-unknown-linux-gnu
cargo build --locked --offline --no-default-features --features production-volume-policy \
  --manifest-path programs/htfp-devnet-processor/Cargo.toml --release --target sbpf-solana-solana
llvm-objcopy --strip-all "$CARGO_TARGET_DIR/sbpf-solana-solana/release/htfp_devnet_processor.so" \
  "$build_dir/local-production-policy.so"
python3 -B tests/production_volume/test_local_process.py \
  --fixture-root "$fixture" --candidate "$build_dir/local-production-policy.so"
```

The local runtime uses the same pinned Solders 0.26.0 build as the
[previous fixture](../devnet_processor_upgrade/README.md).
