# HTFP — Hold The Fucking Position

HTFP is a Solana Token-2022 development project combining a transfer tax, permissionless tax recovery, a fixed burn-and-swap process, and proportional redemption against a native SOL reserve.

**Status: local development.** Several local milestones have been implemented and reviewed against retained execution evidence. The latest BothToken processing integration remains incomplete. This repository is a public source snapshot, not an approved public deployment or a production release. No professional security audit is claimed.

## Intended token mechanics

| Item | Current design |
| --- | --- |
| Initial supply | 1,000,000,000,000 HTFP, 7 decimals; 10,000,000,000,000,000,000 base units |
| Further issuance | None after initialization |
| Transfer tax | Initially 0%; scheduled to 8% at the update epoch E + 2 |
| Fee ceiling | `maximum_fee = u64::MAX`; no economic cap, subject to native integer rounding |
| Recovered tax processing | Burn 3/8 of the processed HTFP; sell the remaining gross 5/8 through the fixed pool |
| Sale proceeds | Actual native SOL credited to the HTFP reserve |
| Holder redemption | Burn authorized HTFP for `floor(spendable_reserve_lamports × amount / pre_burn_supply)` |

Recovering tax and processing it are separate operations. A permissionless caller cannot choose another custody account, swap pool, or proceeds destination. Recover first books actual recovered HTFP into inventory; Process applies the fixed burn/sale split and atomic settlement. Caller rewards are not part of the design. See [the protocol overview](docs/PROTOCOL.md).

## Manual launch scenario

The founder receives SOL contributions and manually distributes the participant tranche in proportion to contributed SOL. The current allocation is **55% participants, 35% initial pool, 5% team, and 5% to a separate marketing wallet**. Raised SOL is split **80% to the pool and 20% to the HTFP reserve**; operating costs require separate funding.

Pool funding and initial distribution are intended to occur while the transfer fee is 0%. Trading should open by timestamp after E + 2 plus an additional margin. The local rehearsal uses **11 SOL across five simulated contributors** and a **4-hour synthetic margin**. Real-network timing, public recipients and distribution remainder rules remain open.

The Raydium target is **0.25% ordinary fees + 0.05% creator fees**, with creator fees in `BothToken` mode. The intended initial-liquidity mechanism is official **Burn & Earn for 100% of LP tokens received**, retaining fee rights through the Fee Key. Creator income and Burn & Earn income target the same founder wallet; applicable HTFP receipts remain taxed. **The exact fee configuration and Burn & Earn lifecycle are not validated by the completed local tests.** The captured local CPMM configuration instead uses 0.25% + 0.25%.

## What the retained local evidence establishes

| Scope | Recorded result | Important boundary |
| --- | --- | --- |
| Manual LGE and captured CPMM | Separate author/supervisor runs; 88 local signed submissions in total | Synthetic funding, retained LP; no Burn & Earn proof |
| Integrated transfer-fee lifecycle | 130 local signed submissions; recovery, buys/sells, creator claims and redemption | Historical 0.25% + 0.25% fixture; no Process in this milestone |
| Latest BothToken Process | Main capture: 118 submissions, 10 Process instructions, one redemption; offline raw audit PASS | Full integration acceptance remains false |
| Computation-limit campaign | Partial 57-submission capture; rollback inspected | Expected error differs from actual error; retained failure remains a failure |
| Read-only/offline tools | Snapshot API, launch dossier checker, Recover/Redeem descriptor tools, account-state inspector | Historical profiles and supplied bytes; no live-chain assurance |

The latest lot has **175 local submissions across two VM campaigns**. A further computation-limit case and a separate supervisor compilation/native reproduction were **not run**. Agent review of retained evidence is distinct from a professional security audit. See [status and open gates](docs/STATUS.md) and the selected original records under [evidence/](evidence/README_PUBLIC_SNAPSHOT.md).

## Explore locally

The portable examples use Python 3.12 and its standard library, with no package installation:

```sh
# Print a simulated manual launch allocation; creates no wallets or accounts.
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/htfp_lge_rehearsal/plan.py

# Start the read-only API on 127.0.0.1:8765 with its fixed historical snapshot.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=api python3 -B -m htfp_readonly --profile local-historical --port 8765
```

The API exposes `GET /health`, `GET /v1/status`, and `GET /v1/redemption-preview?amount_base_units=10000000&minimum_lamports=0`. Stop it with Ctrl+C. With no explicit historical profile, its production profile is **UNCONFIGURED**. A preview is arithmetic on a bundled synthetic snapshot, not a transaction quote or a claim about current balances.

See [development and offline examples](docs/DEVELOPMENT.md). Native integration harnesses are archival source: they depend on the retained VPS toolchain and capture bundle, which are not distributed here.

## Repository map

| Path | Purpose |
| --- | --- |
| [programs/htfp/](programs/htfp/) | Earlier local Initialize, Recover, Redeem and historical processing implementation |
| [programs/htfp-both/](programs/htfp-both/) | Isolated latest BothToken processing candidate; integration incomplete |
| [programs/m4b-proof/](programs/m4b-proof/) | Local proof helpers, not production programs |
| [api/](api/) | Loopback historical-snapshot API |
| [clients/](clients/) | Offline Recover/Redeem instruction descriptor preparation and inspection; no signing or sending |
| [tools/](tools/) | Offline launch, accounting and LGE utilities |
| [config/](config/) | Explicit synthetic/historical local profiles and ABI bindings |
| [models/](models/) and [tests/](tests/) | Integer models, portable allocation tests and archival native harness source |
| [docs/](docs/) | Public protocol, status, development and publication notes |
| [SOURCE_SNAPSHOT.json](SOURCE_SNAPSHOT.json) | Per-file SHA-256 inventory and local source-checkpoint provenance |

Public mint selection, production profile, metadata/authorities, supported Raydium configuration, Burn & Earn integration, volume parameters and actual network validation remain separate gates. This snapshot does not establish current Testnet, Devnet or mainnet deployment status, a market-price floor, or manipulation resistance.

## Licensing

No project-wide license has been selected or added. Publication does not grant an additional HTFP reuse license. Third-party components retain their own terms; see [third-party notices](THIRD_PARTY_NOTICES.md). The [publication scope](docs/PUBLICATION_SCOPE.md) identifies included sources and omitted archival artifacts.
