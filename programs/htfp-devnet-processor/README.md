# HTFP Devnet processor

This crate builds the Devnet processor with the `devnet-tax-processor`
feature. It preserves the installed Devnet profile, instruction encoding and
account layouts. The experimental Raydium profile uses 2,500 ppm trade and
2,500 ppm BothToken creator fees. The default build leaves processing disabled.

The correction keeps a native SOL credit to the pool's Legacy Token wSOL
vault separate from its recorded token amount. Pool quotes continue to use
the recorded token balance. The processor verifies the exact token movement
and unchanged unrelated native surplus after the swap.

The [Devnet ABI and profile](../../config/devnet-processor/) fix the program,
mint, pool and account bindings. Processing burns 3/8 of the recovered gross
tax, sells 5/8 gross through the pinned pool, and settles the resulting
native SOL to the fixed reserve. Volume, storage reimbursement and the
transaction fence retain their existing checks.

## Build and host tests

Use [Solana platform-tools v1.54](https://github.com/anza-xyz/platform-tools/releases/tag/v1.54)
on Linux x86-64 with Rust 1.89.0-dev, Cargo 1.89.0 (`d96b80636`) and LLVM
20.1.7. The released Linux archive SHA-256 is
`fcc41631c7f77561bf5412218bf297501dccf0305ea280f338f0ace2aab9f31e`.
From the repository root, set `HTFP_PLATFORM_TOOLS` to the extracted
directory containing `rust/bin` and `llvm/bin`. Prepare the Cargo cache
from the checked-in lockfile first. If dependencies are missing, use the
pinned toolchain to fetch them with
`cargo fetch --locked --manifest-path programs/htfp-devnet-processor/Cargo.toml`.

```sh
platform=${HTFP_PLATFORM_TOOLS:?Set HTFP_PLATFORM_TOOLS to the v1.54 platform-tools directory}
export PATH="$platform/rust/bin:$platform/llvm/bin:$PATH"
export RUSTC="$platform/rust/bin/rustc" RUSTDOC="$platform/rust/bin/rustdoc"
export CARGO_TARGET_DIR="$PWD/target/htfp-devnet-processor"
export NO_DNA=1 CARGO_NET_OFFLINE=true CARGO_INCREMENTAL=0
mkdir -p "$CARGO_TARGET_DIR/artifacts"
cargo build --offline --locked --jobs 1 --no-default-features \
  --features devnet-tax-processor --manifest-path programs/htfp-devnet-processor/Cargo.toml \
  --release --target sbpf-solana-solana
llvm-objcopy --strip-all \
  "$CARGO_TARGET_DIR/sbpf-solana-solana/release/htfp_devnet_processor.so" \
  "$CARGO_TARGET_DIR/artifacts/htfp-devnet-processor.so"
wc -c "$CARGO_TARGET_DIR/artifacts/htfp-devnet-processor.so"
sha256sum "$CARGO_TARGET_DIR/artifacts/htfp-devnet-processor.so"
cargo test --offline --locked --jobs 1 --no-default-features \
  --features devnet-tax-processor --manifest-path programs/htfp-devnet-processor/Cargo.toml \
  --lib --target x86_64-unknown-linux-gnu
cargo test --offline --locked --jobs 1 --no-default-features \
  --manifest-path programs/htfp-devnet-processor/Cargo.toml --lib --target x86_64-unknown-linux-gnu
```

The qualified stripped ELF is **237,888 bytes** with SHA-256
`24a69877a349f365cec15c840b8b924779a0f9ec6621248b4f0aa2db93f3150d`.
The Cargo.lock SHA-256 is
`ccc1b2ee6bcef788786d371a6c3367fcc1cda389a4f14bdd4aeb71c5293de0fb`.
The source and profile were introduced on the public branch in
[`06889d9`](https://github.com/HoldTheFuckingPosition/HTFPtoken/commit/06889d981984e8e0e219928f3e0ba55e5d89030f).
A clean public checkout reproduced the installed ELF byte for byte and
passed seven enabled and two default-feature host checks. The
[finalized receipt](../../evidence/devnet_processor_upgrade/FOLLOWUP_2026-11-19.public.json)
identifies the installed cluster, program and ProgramData.

The [external-wSOL regression](../../tests/devnet_processor_upgrade/README.md)
uses a separately retained, digest-bound LiteSVM fixture. The build and both
host test commands above need only public source, the toolchain and locked
dependencies.
