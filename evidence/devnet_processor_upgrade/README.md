# HTFP Devnet processor release

The corrected Devnet processor was installed on 19 November 2026 at slot
**523855963**. Finalized readback at **523855973** verified all **237,888**
useful executable bytes and **32** bytes of Loader padding. The ProgramData
account and upgrade authority were retained. The buffer closed and its
**1,209,309,240-lamport** rent was refunded. The installation charged
**1,200,000 lamports** in actual transaction fees. [Public receipt](FOLLOWUP_2026-11-19.public.json)

One subsequent public `Recover → Process → Finalize` transaction finalized
at slot **523856222** and credited **one lamport** to the fixed reserve.
The exact temporary account rent was refunded. This transaction exercised
the existing experimental Raydium pool with **2,500 ppm trade and 2,500 ppm
BothToken creator fees**. [Functional receipt](FOLLOWUP_2026-11-19.public.json)

## Creator claim and Fee Key

One separate creator claim finalized at Devnet slot **523872901**. The
destinations received 50,000 wSOL lamports and 441,548,529,818 spendable HTFP
base units after 38,395,524,333 base units of native withholding. Creator
counters cleared. Effective reserves, native LP supply and the Fee Key position
were unchanged. Two associated token accounts required 3,063,240 lamports of
rent deposits and the network fee was 5,000 lamports. The wSOL stayed wrapped.
[Finalized transaction](https://explorer.solana.com/tx/5Nf5sRcKLYorawRKfYmGkYMKCZqhXyra5GoCo1x7Ap6mskURTNx9H23g38tEoEF4n7LfmeQaiBdscTt6PAYjz6KY?cluster=devnet) · [Compact claim receipt](CLAIMS_2026-11-19.public.json)

Burn & Earn locked all initial LP actually received on Devnet. A separate
**unsigned simulation** tested a direct Fee Key claim capped at **0.1 LP**.
At observation slot 523873803 the projected burn and escrow decrease were
100,000,000 LP base units. The Locker recognized 208,940,645 available units
and booked 108,940,645 as unclaimed. The quote projected 5,025 wSOL lamports
and 1,830,725,695,636 spendable HTFP base units. Both independent minimum
receipt fields were zero. The test demonstrated a native LP debit cap for
that deployment and position. Finalized state was unchanged around the unsigned
observations. The 0.1 LP cap with quote-based receipts is the selected scope for
a future Devnet review. A finalized Fee Key claim and the historical adjusted
two-atomic-LP diagnostic remain open. [Finite and boundary probes](CLAIMS_2026-11-19.public.json)

The production-target 2,500/500 ppm fee tier carries its own read-only observations
and isolated local coverage. [Production-target fee evidence](../cpmm_fee_profile/README.md)

[Source and build instructions](../../programs/htfp-devnet-processor/README.md) ·
[Bounded local runtime regression](../../tests/devnet_processor_upgrade/README.md)
