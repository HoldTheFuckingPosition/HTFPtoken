# HTFP Testnet program

This is the source of the deployed HTFP token/vault pilot on Solana Testnet.

- Program: `CseQKCWvi4EA2o3oa11Age4p4xKWSLuzjWCzitASrPJu`
- Mint: `rRPZUSGGDPsHKKt1zP4ZLfviW9sVZ2FYKcDgdc4j55o`
- SOL reserve: `33S4fefxDJ9Bz6KmHns37uvwcWSPQnsEyopAZ6YtJpdo`
- ELF SHA256: `2375ca3148cf5d8072420844ef74395dd7c50649970f144e73afffc5002d3055`

The program implements fixed-profile initialization, permissionless tax
recovery into canonical custody, and holder-authorized burn/redemption from
the native SOL reserve. Redemption uses the actual pre-burn supply and
spendable reserve, with the holder's minimum payout. Instruction6 is a
read-only epoch assertion used during bootstrap. Processing opcodes3–5 are
reserved and reject; Raydium conversion is outside this deployed pilot.

The native Token-2022 fee starts at0%, with800bps scheduled from epoch1086
and maximum_fee=u64::MAX. Mint, freeze and fee-configuration authorities are
None. The program's fixed tax PDA retains fee withdrawal authority. Program
upgrades and editable token metadata remain controlled by the approved
Testnet wallet4WK during trials. This is not a mainnet deployment.

Source dependencies are pinned by Cargo.lock (`solana-program=2.3.0`,
Rust1.89). The deployed build enables only `testnet-metadata`; default builds
deny profile admission. The embedded public profile binds creation/scheduling
epoch1084 and activation1086. Reusing it for another bootstrap epoch requires
a reviewed source/build/profile change; monetary operations have no
activation-wait gate. No private keys or transaction tooling are included.
