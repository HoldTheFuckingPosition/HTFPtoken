# HTFP production V2 technical SOL reserve

## Confirmed accounting

The rent paid to establish the permanent zero-data SOL reserve is technical funding. The fixed reserve PDA stays the same. A separate, program-owned record stores the technical amount funded at fresh initialization. Normal received SOL and finalized Process proceeds increase redemption backing. Falling network rent never increases backing.

With gross SOL `B`, the authenticated technical basis `T`, and the runtime zero-data minimum `L`, backing is `B − T`. Redeem refuses before burning when `B < T` or `L > T`. Otherwise it pays `floor((B − T) × tokens_burned / actual_pre_burn_supply)`, subject to the holder's minimum. Full redemption leaves the technical deposit. The native 800-bps transfer tax, existing 3/8 burn and 5/8 gross sale split, and 1% gross sale cap remain in force in the production target. [Reserve and sponsor code](../programs/htfp-devnet-processor/src/reserve_storage.rs) · [Redeem](../programs/htfp-devnet-processor/src/lib.rs) · [Launch rules](PRODUCTION-LAUNCH-MANIFEST.md)

## Production ABI

The canonical record uses seeds `htfp-reserve-storage` and the fixed mint. Its 17 bytes hold the eight-byte marker `HTFPRNT1`, the canonical bump and the funded technical lamports as a little-endian u64. Fresh Initialize adds the writable record at index 10. The existing reserve is writable. Redeem uses the readonly record at index 9, before any multisig signer roles.

Top-up uses 22 data bytes: `HTFP`, version `1`, opcode `7`, expected technical basis as a little-endian u64, and exact amount as a little-endian u64. Accounts in order are a distinct writable signing System payer, the writable canonical zero-data reserve, the writable canonical record and the executable readonly System Program. Require `B ≥ T`, a matching expected basis and the exact positive gap `A = L − T` from runtime Rent. The native transfer and record update are atomic. Exact deltas leave `(B + A) − (T + A) = B − T`. A payer acquires zero ownership, governance, withdrawal or refund rights. Competing, stale, zero, wrongly funded or already satisfied quotes fail. Existing covered rent needs no top-up.

## Candidate and installed releases

The local production-profile candidate with the test-market binding is **237,904 bytes**, SHA-256 `cb4af1cd9983872691a74c4eb11e03ce6967ac9f8c044a55b1fed730968f56bc`. Its reproducible inputs include the reviewed gross-volume source `e486cf164a1768ab05598d823764abb8ec26efaa` and this reserve update.

The historical Testnet pilot was installed at slot **463113698** and the historical full Devnet processor at **523855963**. The latter public fee cycle uses Volume V1 and the experimental 2,500/2,500 ppm profile. The local V2 candidate requires a fresh state, including Volume V2. Historical reserve quotes must be interpreted under the historical rules. Public installation and actual production mint/market/authority bindings remain open. The exact zero-rate funding, native 800-bps activation and official opening constraints remain release gates. [Installed Devnet evidence](../evidence/devnet_processor_upgrade/README.md) · [Official opening policy](../tools/htfp_launch_manifest/OPENING.md)

## Reproduce the local candidate

Use platform-tools v1.54 and the exact Cargo lock. The included deterministic market binding SHA-256 is `9b02a742992787656ea704993b33f027d0e36215e6aef26e85a179044d2d162e`. It represents a local 2,500/500 ppm test market, with its own genesis binding.

```sh
platform=${HTFP_PLATFORM_TOOLS:?Select the Anza platform-tools v1.54 directory}
out="$PWD/target/reserve-release"
export PATH="$platform/rust/bin:$platform/llvm/bin:$PATH"
export RUSTC="$platform/rust/bin/rustc" RUSTDOC="$platform/rust/bin/rustdoc"
export CARGO_TARGET_DIR="$out"
export HTFP_PRODUCTION_POLICY_PROFILE="$PWD/tests/production_volume/fixtures/test-market-profile.rs"
export NO_DNA=1 CARGO_NET_OFFLINE=true CARGO_INCREMENTAL=0
mkdir -p "$out"
cargo build --offline --locked --jobs 1 --no-default-features \
  --features production-volume-policy --manifest-path programs/htfp-devnet-processor/Cargo.toml \
  --release --target sbpf-solana-solana
llvm-objcopy --strip-all "$out/sbpf-solana-solana/release/htfp_devnet_processor.so" \
  "$out/htfp-v2-exact-rent-top-up.so"
sha256sum "$out/htfp-v2-exact-rent-top-up.so"
```

Two locked offline builds produced matching ELF bytes. The native LiteSVM 0.26.0 top-up evidence records six successes and 12 intended refusals, including independent sponsors, stale/repeated quotes, full redemption, exact custody and rollback. The retained predecessor 16-check reserve suite and Process/Finalize proof cover their exact candidate and unchanged paths. The test sources require a separately retained, digest-checked public-data fixture and executable inputs. [Native result](../tests/production_volume/fixtures/rent-top-up-result.json) · [Tests and fixture requirements](../tests/production_volume/README.md)

With LiteSVM 0.26.0 through the pinned `solders` package, the focused top-up runner accepts the retained fixture root and the reproduced ELF. The predecessor reserve runner accepts the same arguments with the predecessor ELF and its digest when reproducing the historical check.

```sh
fixture=${HTFP_RETAINED_CPMM_FIXTURE:?Select the retained public-data fixture root}
python3 -B tests/production_volume/test_reserve_top_up.py \
  --fixture-root "$fixture" --candidate "$out/htfp-v2-exact-rent-top-up.so" \
  --sha256 cb4af1cd9983872691a74c4eb11e03ce6967ac9f8c044a55b1fed730968f56bc
```
