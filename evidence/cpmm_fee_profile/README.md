# Raydium CPMM production-target fee evidence

**19 November 2026.** The 2,500 ppm trade and 500 ppm creator tier was observed
on Mainnet at finalized slot 471192559. Canonical AmmConfig index 0 was enabled
for creation, and separate pools with that config were observed with the
creator fee enabled and BothToken mode. These are independent fields in each
pool. `InitializeV2` permits a creator-enabled public pool. The actual HTFP
production pool remains a release input. [Observed accounts and identities](2026-11-19.public.json) · [Official program registry](https://docs.raydium.io/reference/program-addresses) · [InitializeV2 reference](https://docs.raydium.io/reference/changelog/2026-10-30-cpmm-initialize-v2)

In the isolated signed **local** runtime, the observed Mainnet CPMM, Token-2022
and Legacy Token payloads ran with a synthetic HTFP pool, clock and signer.
Both swap directions, dust rounding and `Process → Finalize` matched exact
tax and AMM balances. Both swap directions accepted the projected net minimum
and refused net minimum plus one. `Process` recovered 11 lamports of actual
native SOL proceeds to the fixture reserve from a gross sale of 5,000,000,005
HTFP base units. The fixture ELF has digest
`7260c4b62b1361353d7d5b3a6edd5622c53543c9a8f1cef876a47f7e8f64e1c5` and is
local-only. [Compact runtime results](2026-11-19.public.json) · [Devnet deployment scope](../devnet_processor_upgrade/README.md)

For either swap direction, native HTFP input tax is deducted first where
applicable. The combined AMM fee rounds up on spendable input, the creator
fraction rounds down, and the residual trade fee is split among protocol,
fund and LPs. The constant-product curve floors gross output using effective
reserves. Native HTFP output tax rounds up before the net minimum comparison.
The 3,000 ppm nominal fee describes the AMM tariff. Creator collection has a
separate protocol share, and creator HTFP receipts can incur native tax.
[Pinned curve calculation](https://github.com/raydium-io/raydium-cp-swap/blob/3d69122790e97cd6aff24e8ba95940793773f58c/programs/cp-swap/src/curve/calculator.rs) · [Official CPMM fee reference](https://docs.raydium.io/products/cpmm/fees) · [Creator fee share](https://docs.raydium.io/reference/changelog/2026-09-19-cpmm-creator-fee-protocol-share)

## Offline review

From the repository root, recompute the four published cases with Python's
standard library. This checks the accounting against the compact fixture.

```sh
python3 -B -m unittest discover -s tests -p test_cpmm_fee_profile.py -v
```

The exact retained native comparison checks account writes, cap admission,
compute units and minimum-output refusals on its captured dependency images.
The compact local record identifies the tested images and observed results.

## Authority and configuration boundaries

The captured upgrade and configuration authorities are listed in the
[compact record](2026-11-19.public.json). The CPMM hardcoded admin can update
fee configuration and pool status. Its upgrade authority and the Token-2022
upgrade authority are external. Protocol and fund owners can collect their
respective accrual. The default creator collection share was **5% of accrued
creator fees**, subject to the creator/config override on the selected pool.
Dependency identity, fee configuration and the actual creator arrangement
must be verified again on the selected release. [Raydium authority reference](https://docs.raydium.io/security/admin-and-multisig) · [Production manifest](../../docs/PRODUCTION-LAUNCH-MANIFEST.md)
