# HTFP V2 isolated Devnet E1216 finalized receipts

24 November 2026 · Isolated Devnet test scope

**Official pool funding finalized at slot 525,613,577.** The 832-byte transaction executed a native expected-zero fee assertion immediately before official Raydium `InitializeV2(Some(BothToken))`. The HTFP vault received 350,000,000,000 HTFP and the wSOL vault received 400,000,000 lamports. Native withholding was zero. The 800-bps fee was already scheduled and was inactive at funding.

- Program `EhBgdnHGhqpis7RruUvfo65yYFMTwsQE2i2K7ZrL1Svt`, ProgramData `7fiXo2ekC835cQqYgxHdppFkCURzvcNJdPSVkXv74WZz`, installed ELF `924ca1e2c7a6921c751a6549bf66bc1f2da76d88ea633b351fef480a160e7898` from slot `525194904`. No rebuild, epoch rebind or Loader write occurred.
- Mint `CEBdMYWyxAQDA7DsntZbqunriZW2TarGyLL4rnZvYYah` issued `10000000000000000000` base units with seven decimals. The scheduling original revoked the mint and fee-configuration authorities. The canonical PDA retained withheld-withdrawal authority.
- Pool `9DVKa2Sd8kSrhaVLwzXowgQ5JNAeooxcDrqS8XqV8Zuf` has the approved **2,500/2,500 ppm** Devnet test tier, **BothToken** creator mode and **37,416,573,867,639** initial LP base units issued to the bound creator. The initial LP remains in that account. Production intent remains **2,500/500 ppm**.
- The isolated 55/35/5/5 token allocations used the active zero fee. The 80/20 SOL split funded the pool with **0.4 SOL** and the economic reserve with **0.1 SOL**. The reserve also holds **650,240 separately recorded technical lamports**. Tax custody and booked inventory were zero and Volume V2 was idle.

## Finalized originals

| Action | Finalized slot | Network fee in lamports | Verified signature |
| --- | ---: | ---: | --- |
| Fund dedicated roles | 525612361 | 5,000 | [4FzWnCKUw1Ea…](https://explorer.solana.com/tx/4FzWnCKUw1EaqLCUKwFqmwZe9X36CXn6v8csbstpAan4oxKW7xNJ6ELYWx9hUERLut94eTh9sPKSg8Ry7H1TxqmH?cluster=devnet) |
| Create the native Token-2022 mint | 525612899 | 5,000 | [47KDk6Lp8swm…](https://explorer.solana.com/tx/47KDk6Lp8swmtYV5QM4GpuNXkjjsGwjeVgyHYnBgabVYvTfdqQpHijoprHF9MpxdcDcvMkadkRw32AvjL1Mj6Njd?cluster=devnet) |
| Issue the fixed supply | 525612914 | 5,000 | [5v8AQ1mZig7Z…](https://explorer.solana.com/tx/5v8AQ1mZig7ZHpwNer1XGUMxc4aKZePLrzCndMdJqVWLfhURugTHeEjqCMdf3bx3uFeuXTRJ3NcTi9uJgjzgTVXs?cluster=devnet) |
| Schedule 800 bps and revoke the two economic authorities | 525612956 | 5,000 | [2JBk82GYPsUu…](https://explorer.solana.com/tx/2JBk82GYPsUuMTSTNx8eJxNanbt4KionUS8K9Bz9BK37o5vQkttwe9MGbfgNxRvo8sqxCPKRkUJvwXpGW1U7hYjk?cluster=devnet) |
| Initialize HTFP and the technical reserve | 525613420 | 5,000 | [MpRZj7YNAyBR…](https://explorer.solana.com/tx/MpRZj7YNAyBRXzqjhzr5wqYdNLYki3vVDP98iMCf63122jdLWg8xVFK3chiNaa2b966TsNcAwRx1ThSbjdMAXYc?cluster=devnet) |
| Initialize Volume V2 | 525613436 | 5,000 | [4LbXkD3SqRNv…](https://explorer.solana.com/tx/4LbXkD3SqRNvMmJYtxkvawSUk81YBt3FqdcUtMNAXrT856hK1fqNaezzBrMWSG8KHpjEWYEUFgNmyXbNJGXTyFtg?cluster=devnet) |
| Record two isolated contributions | 525613450 | 15,000 | [PWrxeL54dZGV…](https://explorer.solana.com/tx/PWrxeL54dZGVuQdAVkmpHSHqBZQgoshrdMHg2QdqPv5pC8TgwQwqiwZQh8y5c81LS1voFghK6ASSNDHyN8Sz94Z?cluster=devnet) |
| Allocate 65% at native zero fee | 525613467 | 5,000 | [2UpGbutQVu9L…](https://explorer.solana.com/tx/2UpGbutQVu9LVr9L22dXsYjHhLxyqz5BsfGTBE3eUKLiRHaimK69uV6fGB2tDBMes7VDG4WLqPRbG8yB1YRT9dFf?cluster=devnet) |
| Fund the native economic reserve | 525613483 | 5,000 | [3cBM6Uhn5a79…](https://explorer.solana.com/tx/3cBM6Uhn5a79htbh4j6Es1QG7S3hMNnhgvUxjiYaLUWLxgLW1nLvVWWUzh4UNWijb2HpvqQyTFwLNENGXepvHHwM?cluster=devnet) |
| Wrap the 80% liquidity share | 525613498 | 5,000 | [4ahgjJmbYiFB…](https://explorer.solana.com/tx/4ahgjJmbYiFB4ZbJ9359SJqiMbd7QmfKt5B169fA29RZxnRHsAjFkuDGmcVD51xvBoi3jnQRc46b7Xh1osi8ETSU?cluster=devnet) |
| Initialize and fund official CPMM at native zero fee | 525613577 | 5,000 | [3cuzFTF1mP1q…](https://explorer.solana.com/tx/3cuzFTF1mP1qaPKpCz2aCCuEFtqBptMv4yn3YekappZZnooeJ2bePs1LvmLa1gnNVTKCUCENdizbVLP2gjezphno?cluster=devnet) |

The initial mint-creation original `3dFaSBGFvooWG4bAKURf7UY3PX3mYGWaMFvya5f2vkaUFNG7jjy7sNdoH3FDf8GegEvT2CDeVo5rCBPjztALiKcK` expired. The finalized blockhash was invalid, its signature was absent from the relevant finalized account histories, the mint was still absent and the creator balance was unchanged. Only then was a fresh original signed. The expired original incurred zero debit.

## Opening and remaining scope

The genuine E1216 scheduling original finalized at slot **525,612,956**. Native activation is scheduled for the first eligible E1218 Bank, beginning at slot **526,176,000**. The finalized Clock/footer anchor at slot **525,613,563** yields a 200-ms model limit of `1795705843` and a 250-ms model limit of `1795762087`. The Devnet-only margin uses the 250-ms model plus one hour and one second. Raydium stored **`open_time = 1795765688`** (**2026-11-27 07:48:08 UTC**, interpreted as Unix time). The execution Clock and native swap status determine when the stored threshold is reached.

The founder accepted the unproved effective-stake coverage premise for this isolated experiment. Residual early-opening risk for third-party swaps remains if the prospective Clock or duration assumptions fail. The full production opening guarantee remains mandatory. Intentional economic tests wait for verified native active 800 bps and actual Raydium eligibility. No Recover, Process, burn, swap, Finalize, Redeem, creator claim or LP lock is recorded in this checkpoint.

## Financial reconciliation

| Item | Lamports |
| --- | ---: |
| Prior gross commitments | 3,633,104,320 |
| New gross commitments | 2,307,368,360 |
| New network fees, included above | 65,000 |
| New technical storage and technical reserve deposits, included above | 49,494,440 |
| Pool creation charge, included above | 150,000,000 |
| Cumulative gross commitments | 5,940,472,680 |
| Remaining authorization on the original 10 SOL cap | **4,059,527,320** |
| New refunds | 0 |

The gross ledger charges each reviewed movement, including the later transfer of the wrapped market contribution. The historical Buffer refund remains separate. Each finalized receipt was reconciled against its signed original, actual fee, native account deltas and finalized program or token state. The pool readback preserves the historic deployment controls and verifies the exact recorded technical reserve basis.
