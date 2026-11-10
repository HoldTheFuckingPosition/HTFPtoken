"""Deterministic generated and exhaustive finite checks; no auto-shrinking.

Expected results use inequalities, conservation, cross-products and a separate
Decimal ceiling oracle rather than restating the implementation. No filtering.
"""
import random
import unittest
from decimal import Decimal, ROUND_CEILING, localcontext

from models.monetary import (
    INITIAL_SUPPLY, U64_MAX, U128_MAX, DomainError, RedemptionState,
    allocate, checked_product, decode_u64, encode_u64, external_burn,
    native_donation, quote, redeem, round_inventory, sale_accounting, transfer_fee,
)

SEED = 0x48544650
COUNTS = {}


def count(name, n):
    COUNTS[name] = COUNTS.get(name, 0) + n


class ExactIntegerTests(unittest.TestCase):
    def test_issuance_and_u64_codec(self):
        self.assertEqual(INITIAL_SUPPLY, 10_000_000_000_000_000_000)
        self.assertLessEqual(INITIAL_SUPPLY, U64_MAX)
        self.assertGreater(INITIAL_SUPPLY, (1 << 63) - 1)
        self.assertGreater(INITIAL_SUPPLY, (1 << 53) - 1)
        self.assertEqual(encode_u64(U64_MAX), b"\xff" * 8)
        self.assertEqual(encode_u64((1 << 53) + 1).hex(), "0100000000002000")
        self.assertEqual(encode_u64(1 << 63).hex(), "0000000000000080")
        self.assertEqual(encode_u64(INITIAL_SUPPLY).hex(), "0000e8890423c78a")
        rng = random.Random(SEED)
        values = [0, 1, 255, 256, (1 << 53) + 1, (1 << 63), INITIAL_SUPPLY, U64_MAX]
        values += [rng.randrange(U64_MAX + 1) for _ in range(2000)]
        for value in values:
            raw = encode_u64(value)
            self.assertEqual(decode_u64(raw), value)
            # Independent wire constraint through hex positional expansion.
            self.assertEqual(sum(byte * 256**i for i, byte in enumerate(raw)), value)
        count("codec_roundtrips", len(values))

    def test_strict_domains_and_checked_products(self):
        for bad in [True, False, 1.0, float("nan"), "1", None, -1, U64_MAX + 1]:
            for fn in [encode_u64, lambda x: transfer_fee(x, 800), allocate]:
                with self.subTest(value=repr(bad), function=repr(fn)):
                    with self.assertRaises(DomainError):
                        fn(bad)
            with self.assertRaises(DomainError):
                RedemptionState(bad, 10, 0, 0)
        for bad in [b"", b"\0" * 7, b"\0" * 9, bytearray(8), "00000000", 1, True]:
            with self.assertRaises(DomainError):
                decode_u64(bad)
        for bps in [-1, True, 1.0, 10001]:
            with self.assertRaises(DomainError):
                transfer_fee(100, bps)
        for cap in [-1, True, 1.0, U64_MAX + 1]:
            with self.assertRaises(DomainError):
                transfer_fee(100, 800, cap)
        self.assertEqual(checked_product(U64_MAX, U64_MAX), U64_MAX**2)
        self.assertEqual(checked_product(U128_MAX, 1), U128_MAX)
        for a, b in [(U128_MAX, 2), (-1, 1), (True, 1), (1.0, 1), (U128_MAX + 1, 0)]:
            with self.assertRaises(DomainError):
                checked_product(a, b)
        for args in [(1, 9, 10, 1), (1, 10, 0, 2)]:
            with self.assertRaises(DomainError):
                RedemptionState(*args)

    def test_fee_ceiling_exhaustive_residues_and_generated_oracle(self):
        rng = random.Random(SEED + 1)
        pairs = [(a, 800) for a in range(12_501)]
        pairs += [(a, b) for a in [0, 1, 12, 13, 24, 25, 26, INITIAL_SUPPLY, U64_MAX]
                  for b in [0, 1, 799, 800, 9999, 10000]]
        pairs += [(rng.randrange(U64_MAX + 1), rng.randrange(10001)) for _ in range(2500)]
        with localcontext() as context:
            context.prec = 80
            for amount, bps in pairs:
                fee = transfer_fee(amount, bps)
                # Unique integer ceiling, independent of implementation division.
                self.assertGreaterEqual(fee * 10000, amount * bps)
                self.assertLess(fee * 10000 - amount * bps, 10000)
                self.assertLessEqual(fee, amount)  # For every tested bps<=10000.
                oracle = int((Decimal(amount) * Decimal(bps) / Decimal(10000))
                             .to_integral_value(rounding=ROUND_CEILING))
                self.assertEqual(fee, oracle)
                cap = rng.randrange(U64_MAX + 1)
                self.assertLessEqual(transfer_fee(amount, bps, cap), cap)
                self.assertEqual(transfer_fee(amount, bps, cap), min(oracle, cap))
        self.assertEqual(transfer_fee(1, 800), 1)
        self.assertEqual(transfer_fee(25, 800), 2)
        count("fee_inequality_and_decimal_oracle", len(pairs))

    def test_allocation_conservation_and_residual_bound(self):
        rng = random.Random(SEED + 2)
        inventory = list(range(4096)) + [U64_MAX, INITIAL_SUPPLY]
        inventory += [rng.randrange(U64_MAX + 1) for _ in range(2500)]
        for recovered in inventory:
            q, residual = round_inventory(recovered)
            self.assertEqual(q + residual, recovered)
            self.assertIn(residual, range(8))
            self.assertEqual(q % 8, 0)
            if q:
                burn, gross = allocate(q)
                self.assertEqual(burn + gross, q)
                self.assertEqual(5 * burn, 3 * gross)
                self.assertEqual(burn * 8, q * 3)
                self.assertEqual(gross * 8, q * 5)
                b, f, withheld, net = sale_accounting(q)
                self.assertEqual((b, f), (burn, gross))
                self.assertEqual(net + withheld + burn, q)
                self.assertLessEqual(withheld, gross)
        for q in [0, 1, 7, 9, U64_MAX]:
            with self.assertRaises(DomainError):
                allocate(q)
        self.assertEqual(sale_accounting(800), (300, 500, 40, 460))
        # The new 40 withheld units are not included in the original processed Q.
        count("inventory_residue_and_allocation", len(inventory))


class RedemptionModelTests(unittest.TestCase):
    def check_transition(self, state, amount):
        before = state
        v, s = state.spendable, state.supply
        if v * amount < s:
            with self.assertRaises(DomainError):
                redeem(state, amount)
            self.assertEqual(state, before)
            return
        after, payout = redeem(state, amount)
        remainder = v * amount - payout * s
        self.assertGreaterEqual(remainder, 0)
        self.assertLess(remainder, s)  # Independent characterization of floor.
        self.assertEqual(after.supply + amount, s)
        self.assertEqual(after.holder_balance + amount, state.holder_balance)
        self.assertEqual(after.reserve + payout, state.reserve)
        self.assertGreaterEqual(after.reserve, state.maintenance)
        if amount < s:
            self.assertGreaterEqual(after.spendable * s, v * after.supply)
        else:
            self.assertEqual(after.reserve, state.maintenance)
            self.assertEqual(payout, v)
        self.assertEqual(quote(state, amount, payout), payout)
        with self.assertRaises(DomainError):
            redeem(state, amount, payout + 1)
        self.assertEqual(state, before)

    def test_exhaustive_small_and_generated_large_states(self):
        n = 0
        for s in range(1, 33):
            for v in range(33):
                for a in range(1, s + 1):
                    self.check_transition(RedemptionState(s, v + 11, 11, s), a)
                    n += 1
        rng = random.Random(SEED + 3)
        for _ in range(3000):
            s = rng.randint(1, U64_MAX)
            holder = rng.randint(1, s)
            a = rng.randint(1, holder)
            maintenance = rng.randint(0, 1_000_000)
            reserve = rng.randint(maintenance, U64_MAX)
            self.check_transition(RedemptionState(s, reserve, maintenance, holder), a)
            n += 1
        for s, v in [(1, U64_MAX), (INITIAL_SUPPLY, U64_MAX), (U64_MAX, U64_MAX)]:
            self.check_transition(RedemptionState(s, v, 0, s), s)
            self.check_transition(RedemptionState(s, v, 0, s), 1)
            n += 2
        count("redemption_transitions", n)

    def test_invalid_inputs_never_change_modeled_state(self):
        state = RedemptionState(100, 1100, 100, 50)
        for amount, minimum in [(0, 0), (51, 0), (101, 0), (-1, 0),
                                (True, 0), (1.0, 0), (1, 11), (1, -1),
                                (1, True), (1, 1.0), (1, U64_MAX + 1)]:
            with self.assertRaises(DomainError):
                redeem(state, amount, minimum)
            self.assertEqual(state, RedemptionState(100, 1100, 100, 50))
        with self.assertRaises(DomainError):
            redeem(RedemptionState(100, 100, 100, 100), 100)
        with self.assertRaises(DomainError):
            redeem(RedemptionState(100, 101, 100, 100), 1)

    def test_preburn_supply_includes_withheld_and_donations(self):
        # 60 holder, 20 pool/custody, 20 withheld = actual supply 100.
        state = RedemptionState(100, 1100, 100, 60)
        self.assertEqual(quote(state, 10), 100)
        # External native burn changes the actual denominator once.
        burned = external_burn(state, 10)
        self.assertEqual((burned.supply, burned.reserve), (90, 1100))
        self.assertEqual(quote(burned, 9), 100)
        # Native SOL becomes backing; token donation/withholding is already in S.
        donated = native_donation(state, 100)
        self.assertEqual((donated.supply, donated.holder_balance), (100, 60))
        self.assertEqual(quote(donated, 10), 110)
        with self.assertRaises(DomainError):
            external_burn(state, 61)

    def test_terminal_redemption_and_external_extinction(self):
        state = RedemptionState(INITIAL_SUPPLY, U64_MAX, 12345, INITIAL_SUPPLY)
        terminal, payout = redeem(state, INITIAL_SUPPLY)
        self.assertEqual((terminal.supply, terminal.reserve), (0, 12345))
        self.assertEqual(payout + terminal.reserve, state.reserve)
        external = RedemptionState(INITIAL_SUPPLY, 1_000_000, 12345, INITIAL_SUPPLY)
        for empty in [terminal, external_burn(external, INITIAL_SUPPLY)]:
            later = native_donation(empty, 789)
            self.assertEqual(later.supply, 0)
            self.assertEqual(later.reserve, empty.reserve + 789)
            for amount in [0, 1, INITIAL_SUPPLY]:
                with self.assertRaises(DomainError):
                    redeem(later, amount)
        with self.assertRaises(DomainError):
            native_donation(state, 1)
