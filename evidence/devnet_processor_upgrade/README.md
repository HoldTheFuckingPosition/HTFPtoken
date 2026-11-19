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

The separately specified production target is 2,500 ppm trade and 500 ppm
BothToken creator fees. Fee Key and creator-fee claims are independent
operations. The native Fee Key route has unsigned Devnet simulation evidence,
and its finalized claim and the separate creator-fee collection remain pending.
This publication records the Devnet installation and scoped validation.

[Source and build instructions](../../programs/htfp-devnet-processor/README.md) ·
[Bounded local runtime regression](../../tests/devnet_processor_upgrade/README.md)
