# HTFP program source

[`htfp-both/`](htfp-both/) contains the current Rust development candidate for the single custom HTFP program. It handles initialization, permissionless recovery, recovered-tax processing and holder-authorized redemption.

Token-2022, Raydium CPMM, Raydium Burn & Earn, System and SPL Token are external Solana programs. Their roles and interactions are shown in the [project overview](../README.md).

The retained source includes synthetic local profiles; default monetary entry points are disabled. Production configuration and final integration remain pending. This directory does not publish a production mint or deployment configuration.
