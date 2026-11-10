# Public snapshot scope

This is the initial public source publication for `HoldTheFuckingPosition/HTFPtoken`. It exports reviewed development sources from the retained local checkpoint identified in `SOURCE_SNAPSHOT.json`, plus new English public documentation. The public repository has separate publication commits; local development commit IDs embedded in historical records identify the retained archive and may not exist as public Git objects.

## Included

- First-party Rust program/proof/helper sources and lockfiles.
- Python models, API, offline clients/tools and test harness source.
- Synthetic local configuration and ABI files, including the local locker binding preimage.
- The bundled historical API snapshot and explicit offline tool profiles.
- Selected offline input contracts, documentary examples and requirements.
- Selected original completion/review/checkpoint records for the LGE, fee lifecycle and interrupted BothToken milestones.
- The existing `.gitignore` and a per-file publication inventory.

Exported implementation, configuration, test, contract and original evidence bytes are unchanged. New public documentation summarizes the current scope; it does not alter the frozen protocol or approve unfinished integration.

## Not included

The full retained archive contains roughly 395 MB of tracked payloads and its own local development history. This snapshot omits raw native capture bundles, captured third-party program binaries, upstream research-source copies, build targets, package/cache data, compiled Python bytecode, internal chat handoffs and supervisor instruction files. It also omits the archive-wide package manifest/checksums, whose complete payload set is not distributed here.

Archival paths and source hashes remain in original source/profile/contract/summary records for provenance. An archival reference is not a promise that the referenced raw file is included. In particular, selected review records summarize checks performed against the retained archive; the smaller public snapshot alone cannot reproduce or independently substantiate every native-evidence claim. Historical offline verification runners can also require omitted oracle/campaign bundles; only the explicitly listed portable examples are self-contained.

## Identities and licenses

Public RFC 8032 test vectors and deterministic artificial signers in native harnesses are deliberate fixture inputs. They must never be used as operational wallet keys. Addresses in local profiles are historical test identities, not a published HTFP mint or an assertion about current chain state.

No HTFP project-wide license has been selected. Dependencies retain their own terms. See [third-party notices](../THIRD_PARTY_NOTICES.md).

## GitHub presentation

The proposed GitHub About description is retained in [GITHUB_ABOUT.txt](GITHUB_ABOUT.txt). Publishing this file or the README does not itself modify GitHub repository metadata. Suggested topics are `solana`, `token-2022`, `raydium`, `rust`, and `python`; applying metadata depends on repository administration access.
