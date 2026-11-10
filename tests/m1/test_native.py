"""Real native instruction scenarios inside installed solders 0.26.0 LiteSVM.

No test uses set_account to construct mint/token state. Synthetic sysvars,
airdrop and standard bundled programs are the only runtime setup shortcuts.
"""
import unittest

from models.monetary import INITIAL_SUPPLY, U64_MAX, transfer_fee
from native_fixture import (
    NativeFixture, TOKEN_2022, burn, meta, mint_to, native, set_fee, transfer,
)


class BundledNativeTests(unittest.TestCase):
    def test_exact_issuance_schedule_revocations_and_forbidden_changes(self):
        f = NativeFixture(self.id())
        initial = f.state("mint")
        self.assertEqual(initial["supply"], INITIAL_SUPPLY)
        self.assertEqual(initial["decimals"], 7)
        self.assertTrue(initial["is_initialized"])
        self.assertIsNone(initial["freeze_authority"])
        self.assertEqual(initial["withdraw_authority"], str(f.withdraw.pubkey()))
        self.assertEqual(initial["older"], {"epoch": 7, "maximum_fee": U64_MAX, "bps": 0})
        self.assertEqual(initial["newer"], initial["older"])
        f.schedule_and_revoke()
        scheduled = f.state("mint")
        self.assertIsNone(scheduled["mint_authority"])
        self.assertIsNone(scheduled["fee_authority"])
        self.assertEqual(scheduled["newer"], {"epoch": 9, "maximum_fee": U64_MAX, "bps": 800})
        self.assertEqual(scheduled["older"], initial["older"])
        self.assertEqual(scheduled["withdraw_authority"], initial["withdraw_authority"])
        f.send("forbidden_fee_change_after_revocation",
               [set_fee(f.mint.pubkey(), f.authority.pubkey(), 0)], [f.authority],
               expected_error=29, error_instruction=0)  # NoAuthorityExists, error.rs.
        f.send("forbidden_issuance_after_revocation",
               [mint_to(f.mint.pubkey(), f.source.pubkey(), f.minter.pubkey(), 1)], [f.minter],
               expected_error=5, error_instruction=0)  # FixedSupply.
        f.clock(9)
        self.assertEqual(f.state("mint"), scheduled)

    def assert_transfer(self, f, amount, rate):
        before = {role: f.state(role) for role in ["mint", "source", "destination"]}
        expected = transfer_fee(amount, rate)
        f.send("epoch_transfer", [transfer(f.source.pubkey(), f.mint.pubkey(),
               f.destination.pubkey(), f.holder.pubkey(), amount, expected)], [f.holder])
        after = {role: f.state(role) for role in before}
        self.assertEqual(before["source"]["spendable"] - after["source"]["spendable"], amount)
        withheld_delta = after["destination"]["withheld"] - before["destination"]["withheld"]
        credit = after["destination"]["spendable"] - before["destination"]["spendable"]
        self.assertEqual(credit + withheld_delta, amount)
        self.assertEqual(withheld_delta, expected)
        self.assertGreaterEqual(withheld_delta * 10000, amount * rate)
        self.assertLess(withheld_delta * 10000 - amount * rate, 10000)
        self.assertEqual(after["mint"], before["mint"])  # No native supply burn.
        self.assertEqual(after["source"]["withheld"], before["source"]["withheld"])
        from native_fixture import EVENTS, exact_json
        EVENTS[-1]["asserted_expected_vs_actual"] = exact_json({
            "source_debit": {"expected": amount, "actual":
                            before["source"]["spendable"] - after["source"]["spendable"]},
            "destination_credit": {"expected": amount - expected, "actual": credit},
            "withheld_increment": {"expected": expected, "actual": withheld_delta},
            "supply": {"expected": before["mint"]["supply"], "actual": after["mint"]["supply"]},
            "rate_bps": rate, "gross_amount": amount,
            "native_ceiling_inequality_verified": True})

    def test_actual_transfers_E_Eplus1_Eplus2_with_rounding(self):
        f = NativeFixture(self.id())
        f.schedule_and_revoke()
        for epoch, rate in [(7, 0), (8, 0), (9, 800)]:
            f.clock(epoch)
            for amount in [0, 1, 12, 13, 24, 25, 26, 499, 500, 501, INITIAL_SUPPLY // 10]:
                with self.subTest(epoch=epoch, amount=amount):
                    self.assert_transfer(f, amount, rate)
        self.assertEqual(f.state("mint")["supply"], INITIAL_SUPPLY)
        self.assertEqual(f.state("mint")["newer"]["epoch"], 9)

    def test_native_missing_authority_and_wrong_expected_fee(self):
        f = NativeFixture(self.id())
        f.send("missing_fee_authority_signature",
               [set_fee(f.mint.pubkey(), f.authority.pubkey(), signer=False)],
               expected_error="MissingRequiredSignature", error_instruction=0)
        f.send("missing_token_owner_signature",
               [transfer(f.source.pubkey(), f.mint.pubkey(), f.destination.pubkey(),
                         f.holder.pubkey(), 25, 0, signer=False)],
               expected_error="MissingRequiredSignature", error_instruction=0)
        f.send("wrong_fee_before_activation",
               [transfer(f.source.pubkey(), f.mint.pubkey(), f.destination.pubkey(),
                         f.holder.pubkey(), 25, 1)], [f.holder],
               expected_error=32, error_instruction=0)  # FeeMismatch.
        f.schedule_and_revoke()
        f.clock(9)
        f.send("wrong_fee_after_activation",
               [transfer(f.source.pubkey(), f.mint.pubkey(), f.destination.pubkey(),
                         f.holder.pubkey(), 1, 0)], [f.holder],
               expected_error=32, error_instruction=0)

    def test_late_native_failure_rolls_back_prior_mint_and_transfer(self):
        f = NativeFixture(self.id())
        prefix = [
            mint_to(f.mint.pubkey(), f.source.pubkey(), f.minter.pubkey(), 17),
            transfer(f.source.pubkey(), f.mint.pubkey(), f.destination.pubkey(),
                     f.holder.pubkey(), 25, 0),
        ]
        before = {role: f.state(role) for role in ["mint", "source", "destination"]}
        f.send("positive_control_mint_then_transfer", prefix, [f.minter, f.holder])
        self.assertEqual(f.state("mint")["supply"] - before["mint"]["supply"], 17)
        self.assertEqual(f.state("source")["spendable"] - before["source"]["spendable"], -8)
        self.assertEqual(f.state("destination")["spendable"] - before["destination"]["spendable"], 25)
        bad = transfer(f.source.pubkey(), f.mint.pubkey(), f.destination.pubkey(),
                       f.holder.pubkey(), 1, 1)
        # Earlier mint + transfer really run, then intended instruction2 fails.
        f.send("late_fee_failure_rolls_back_mint_and_transfer", [*prefix, bad],
               [f.minter, f.holder], expected_error=32, error_instruction=2)
        # The success logs show earlier native instructions completed; raw bytes
        # and balances in send() must nevertheless match pre-transaction values.
        from native_fixture import EVENTS
        logs = EVENTS[-1]["logs"]
        self.assertGreaterEqual(sum(line == f"Program {TOKEN_2022} success" for line in logs), 2)

    def test_native_withholding_harvest_withdraw_and_burn_are_distinct(self):
        f = NativeFixture(self.id())
        f.schedule_and_revoke()
        f.clock(9)
        self.assert_transfer(f, 500, 800)
        self.assertEqual(f.state("destination")["withheld"], 40)
        # Native permissionless harvest (26,4), authorized withdraw from mint (26,2).
        f.send("harvest_withheld_to_mint", [native(bytes([26, 4]),
               [meta(f.mint.pubkey(), writable=True), meta(f.destination.pubkey(), writable=True)])])
        self.assertEqual(f.state("mint")["mint_withheld"], 40)
        self.assertEqual(f.state("destination")["withheld"], 0)
        self.assertEqual(f.state("mint")["supply"], INITIAL_SUPPLY)
        f.send("withdraw_harvested_without_transfer_tax", [native(bytes([26, 2]),
               [meta(f.mint.pubkey(), writable=True), meta(f.custody.pubkey(), writable=True),
                meta(f.withdraw.pubkey(), True)])], [f.withdraw])
        self.assertEqual(f.state("custody")["spendable"], 40)
        self.assertEqual(f.state("custody")["withheld"], 0)
        self.assertEqual(f.state("mint")["mint_withheld"], 0)
        self.assertEqual(f.state("mint")["supply"], INITIAL_SUPPLY)
        f.send("native_burn_reduces_supply", [burn(f.custody.pubkey(), f.mint.pubkey(),
                                                  f.holder.pubkey(), 40)], [f.holder])
        self.assertEqual(f.state("custody")["spendable"], 0)
        self.assertEqual(f.state("mint")["supply"], INITIAL_SUPPLY - 40)

    def test_runtime_u64_max_transfer_has_nonbinding_cap(self):
        # Separate codec/range fixture, not additional HTFP issuance policy.
        f = NativeFixture(self.id(), issuance=U64_MAX)
        self.assertEqual(f.state("mint")["supply"], U64_MAX)
        f.schedule_and_revoke()
        f.clock(9)
        self.assert_transfer(f, U64_MAX, 800)
        self.assertEqual(f.state("source")["spendable"], 0)
        self.assertEqual(f.state("mint")["supply"], U64_MAX)

    def test_signature_verification_and_replay_history_remain_enabled(self):
        f = NativeFixture(self.id())
        ix = transfer(f.source.pubkey(), f.mint.pubkey(), f.destination.pubkey(),
                      f.holder.pubkey(), 1, 0)
        transaction = f.send("valid_transaction_for_replay_control", [ix], [f.holder])
        f.send("exact_replay_rejected", [ix], replay=transaction, expected_error="AlreadyProcessed")
        f.send("corrupt_signature_rejected", [ix], [f.holder],
               expected_error="SignatureFailure", corrupt_signature=True)
