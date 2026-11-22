# HTFP V2 isolated Devnet validation profile

This review package binds the corrected HTFP V2 code at `ac9980a10003dd76d00a61285f035676893dd455` to a new Devnet instance. The stripped SBPF artifact is **237,904 bytes** with SHA-256 `924ca1e2c7a6921c751a6549bf66bc1f2da76d88ea633b351fef480a160e7898`. Two fresh target directories reproduced those bytes. A focused local check initialized and reconciled the exact 89-byte Volume V2 account through native System CPIs. Fee and reserve arithmetic uses the selected tier. Public installation and application evidence belong in a subsequent receipt record.

| Field | Devnet binding |
| --- | --- |
| Cluster genesis | `EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG` |
| Program and ProgramData | `EhBgdnHGhqpis7RruUvfo65yYFMTwsQE2i2K7ZrL1Svt`, `7fiXo2ekC835cQqYgxHdppFkCURzvcNJdPSVkXv74WZz` |
| Mint and reserve | `CEBdMYWyxAQDA7DsntZbqunriZW2TarGyLL4rnZvYYah`, `2p6pnV9C7PvemJTdezWVGBGqouFhXxJsgU6B3ow6edU1` |
| Official CPMM and prospective canonical pool | `DRaycpLY18LhpbydsBWbVJtxpNv9oXPgjRSfpF2bWpYb`, `9DVKa2Sd8kSrhaVLwzXowgQ5JNAeooxcDrqS8XqV8Zuf` |
| AmmConfig and mode | Index 0 `5MxLgy9oPdTC3YgkiePHqr3EoCRD9uLVYRQS2ANAs7wy`, raw SHA-256 `3b5ca2f3187261cc048e2353789242067c3aff19cab67168f86dbbd29d99f21c`, native `initialize_v2(Some(BothToken))` |
| Fees | Trade 2,500 ppm, creator 2,500 ppm, trade protocol 120,000 ppm, trade fund 40,000 ppm, creator-protocol share observed at zero for the selected creator |
| Proposed epoch binding | Mint creation, scheduling and bootstrap E=1216, native fee activation E+2=1218, each subject to authentic execution-bank conditions |

The isolated source changes rebind the metadata and market commitments and accept exactly the authenticated Devnet creator rate. The confirmed Mainnet trade/creator fee policy remains 2,500/500 ppm in [HTFPtoken PR #1](https://github.com/HoldTheFuckingPosition/HTFPtoken/pull/1). The previously installed HTFP Devnet program, historical mint, pool, Volume V1 and fee rights retain their historical authorities. This branch carries a distinct Devnet-only release identity. Raydium CPMM and its administration remain external. Before any market action, confirm current dependencies, active-zero funding and the exact enforceable opening condition. Fee scheduling, native tax activation, pool creation and trading need their own finalized evidence. Keep M4 `OPEN_UNWAIVED` and D-114 `OPEN` and platform-paused.

## Offline reproduction

Use the v1.54 Anza platform-tools directory as `HTFP_SBF_TOOLS`. Run from the repository root with the locked Cargo dependencies available locally.

```sh
sha256sum -c <<'CHECKSUMS'
8979a612c351539e4ced5d19d156086b7ee2bb38cebcaeb65abb00c977a3c9fd  programs/htfp-devnet-processor/src/devnet_profile.rs
0f0a4181289e74179771177070b85d0a4af2a9a1ad3110501c6945c0f425c951  programs/htfp-devnet-processor/src/processing.rs
62fd3474093bf2796a393f256711ca5395d221875525a70efb682ca709656c99  programs/htfp-devnet-processor/profiles/isolated-devnet-v2-2500-2500.rs
ccc1b2ee6bcef788786d371a6c3367fcc1cda389a4f14bdd4aeb71c5293de0fb  programs/htfp-devnet-processor/Cargo.lock
CHECKSUMS
export PATH="$HTFP_SBF_TOOLS/rust/bin:$HTFP_SBF_TOOLS/llvm/bin:$PATH"
export RUSTC="$HTFP_SBF_TOOLS/rust/bin/rustc"
export RUSTDOC="$HTFP_SBF_TOOLS/rust/bin/rustdoc"
export HTFP_PRODUCTION_POLICY_PROFILE="$PWD/programs/htfp-devnet-processor/profiles/isolated-devnet-v2-2500-2500.rs"
export CARGO_TARGET_DIR=$(mktemp -d)
export NO_DNA=1 CARGO_NET_OFFLINE=true CARGO_INCREMENTAL=0
cargo build --offline --locked --jobs 1 --no-default-features \
  --features production-volume-policy --manifest-path programs/htfp-devnet-processor/Cargo.toml \
  --release --target sbpf-solana-solana
llvm-objcopy --strip-all "$CARGO_TARGET_DIR/sbpf-solana-solana/release/htfp_devnet_processor.so" \
  "$CARGO_TARGET_DIR/htfp-v2-devnet.so"
printf '%s  %s\n' 924ca1e2c7a6921c751a6549bf66bc1f2da76d88ea633b351fef480a160e7898 \
  "$CARGO_TARGET_DIR/htfp-v2-devnet.so" | sha256sum -c
```
