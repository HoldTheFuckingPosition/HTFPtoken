# Third-party notices

No project-wide HTFP license has been selected or added. Neither this file nor publication of the repository grants a new license to HTFP-authored code.

The Rust crates declare external dependencies and retain exact resolution in their `Cargo.toml` and `Cargo.lock` files, including `solana-program = "=2.3.0"`. Those dependencies are governed by their respective upstream terms. Their source trees are not vendored in this public snapshot.

Local native harnesses reference Token-2022, Raydium CPMM, locker programs, runtime packages and captured artifacts retained separately in the development archive. This source publication does not distribute those external program binaries, runtime packages or copied upstream research snapshots, and does not claim authorship of them. Their original licenses and provenance must accompany any later redistribution.

The historical native harnesses use public RFC 8032 Ed25519 test vectors as deterministic artificial signer inputs. These are test fixtures, not operational credentials.

Pinned configurations and observed external behavior do not establish a source-to-binary match, an upstream endorsement, or final protocol compatibility. Repository-specific records and [current development status](docs/STATUS.md) state the limits of the retained evidence.
