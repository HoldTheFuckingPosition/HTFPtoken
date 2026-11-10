# Working with the public source snapshot

## Portable offline entry points

Use Python 3.12 from the repository root. The following examples need only the standard library. The bundled profiles are explicitly historical/synthetic; default production profiles are UNCONFIGURED.

Print the simulated five-contributor, 11 SOL launch plan:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/htfp_lge_rehearsal/plan.py
```

The result uses decimal strings for monetary values. It creates no keys, accounts, pool or transfers. Its largest-remainder allocation and SOL remainder handling are test conventions, not finalized public launch policy.

Run the portable allocation checks, using a new output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/lge_pool/test_allocation.py --out /tmp/htfp-allocation-check
```

This command intentionally refuses an existing output directory. It runs seven methods including 256 generated allocation inputs, writes a result and source snapshots, and performs no native VM or blockchain operation. These finite checks do not prove the whole protocol.

Start the historical-snapshot API in the foreground:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=api python3 -B -m htfp_readonly --profile local-historical --port 8765
```

It binds to `127.0.0.1:8765`; Ctrl+C stops it. `GET /health`, `GET /v1/status`, and `GET /v1/redemption-preview?amount_base_units=10000000&minimum_lamports=0` return JSON. Without `--profile local-historical`, no snapshot is selected. See [API behavior and limits](../api/README.md).

Inspect an explicitly supplied, documentary accounting example:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m htfp_accounting_state evidence/m6e/design/EXAMPLE.json
```

The input is a counterfactual collection of bytes, not a current bank or authenticated chain snapshot. A conformant result verifies only the supplied-byte/accounting contract. See [the inspector](../tools/htfp_accounting_state/README.md).

Check the intentionally incomplete documentary launch dossier:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m htfp_launch_manifest evidence/m6b/design/revision-001/EXAMPLE.json
```

Its report preserves missing choices. Exit 0 means no documentary contradiction was found, not that the dossier is complete or launch-approved. Exit 1 denotes contradictions; exit 2 denotes invalid input/usage. See [the checker](../tools/htfp_launch_manifest/README.md).

[Recover](../clients/htfp_recover/README.md) and [Redeem](../clients/htfp_redeem/README.md) clients prepare or inspect instruction descriptors offline. They do not sign, send, fetch blockchain state or verify execution. Their input examples and contracts are included under `evidence/m6d/design/` and `evidence/m6c/design/` respectively.

## Rust and native harness boundaries

The program crates pin `solana-program = "=2.3.0"` and retain their lockfiles. The local crates use Rust 1.89 requirements where declared. Default monetary entry points are disabled; explicit local features recognize synthetic profiles only. Inspect each `Cargo.toml` rather than assuming a generic deploy command.

The native integration harnesses under `tests/m3`, `tests/m4b*`, `tests/m5*`, `tests/lge_pool`, `tests/fee_lifecycle` and `tests/processing_both` are retained for source inspection. They refer to captured program binaries, raw evidence, cached tools, installed package containers and VPS-specific paths. These dependencies are **not bundled in this public snapshot**, and some scripts check the original host explicitly. This publication is not a portable native-test distribution. A blanket test discovery command is not a supported quickstart. Historical offline verification runners under `tests/m6*` also require omitted oracle/campaign bundles. Only the portable entry points and allocation test explicitly listed above are presented as self-contained examples.

Older nested README files describe their original milestone. Their historical status and archive paths do not supersede [current status](STATUS.md). Default production configuration remains disabled; local build artifacts must not be mistaken for a public deployment candidate.

## Inspect snapshot integrity

[SOURCE_SNAPSHOT.json](../SOURCE_SNAPSHOT.json) lists the included payload paths, sizes and SHA-256 digests, excluding itself. It identifies the retained local checkpoint, unchanged exported files, and new public documentation. Hashes establish snapshot integrity, not correctness or live-chain provenance.

The original complete capture/history package remains separate. References to omitted evidence in historical source, contracts or summary records are archival references; see [publication scope](PUBLICATION_SCOPE.md).
