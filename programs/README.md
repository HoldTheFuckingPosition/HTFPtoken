# HTFP program source

- [`htfp-testnet/`](htfp-testnet/) contains the deployed Testnet token/vault source for initialization, permissionless recovery and holder redemption.
- [`htfp-devnet-processor/`](htfp-devnet-processor/) contains the installed Devnet processor, including the correction for unrelated native SOL credits to the pool's wSOL vault. [Devnet upgrade and validation](../evidence/devnet_processor_upgrade/README.md)
- [`htfp-both/`](htfp-both/) contains the older local development candidate with a synthetic BothToken profile.

Token-2022, Raydium CPMM, Raydium Burn & Earn, System and SPL Token are external Solana programs. Their roles and interactions are shown in the [project overview](../README.md).

Monetary entry points require the corresponding build profile. Production identities, configuration and final integration remain pending.
