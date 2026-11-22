"""Finite synthetic arithmetic checks. No public state or Clock is changed."""
import unittest

from opening_duration_oracle import (
    Geometry, I64_MAX, conditional_arithmetic, effective_slot_changes,
    elapsed_duration_half_open, elapsed_duration_inclusive,
)


class OpeningDurationOracleTest(unittest.TestCase):
    def test_reductions_apply_at_next_epoch_and_keep_the_shortest(self):
        geometry = Geometry(32, 0, 0)
        changes = effective_slot_changes(geometry, 400, [(1, 350), (31, 300), (35, 250),
                                                         (65, 200), (90, 350)])
        self.assertEqual(changes, [(0, 400), (32, 300), (64, 250), (96, 200)])

    def test_agave_inclusive_and_firedancer_half_open_edges(self):
        changes = [(0, 400), (32, 200)]
        self.assertEqual(elapsed_duration_inclusive(31, 32, changes), 200)
        self.assertEqual(elapsed_duration_half_open(32, 33, changes), 200)
        self.assertEqual(elapsed_duration_inclusive(30, 32, changes), 600)
        self.assertEqual(elapsed_duration_half_open(31, 33, changes), 600)
        self.assertEqual(elapsed_duration_inclusive(32, 32, changes), 0)

    def test_skipped_slots_and_partition_additivity(self):
        changes = [(0, 400), (32, 350), (64, 200)]
        self.assertEqual(elapsed_duration_inclusive(30, 65, changes), 400 + 32 * 350 + 2 * 200)
        self.assertEqual(elapsed_duration_inclusive(30, 65, changes),
                         elapsed_duration_inclusive(30, 63, changes) + elapsed_duration_inclusive(63, 65, changes))

    def test_fee_slot_and_plus_one_after_inclusive_second(self):
        result = conditional_arithmetic(Geometry(32, 0, 0), 1, 34, 1_999_999_999, 1, 200_000_000, [])
        self.assertEqual(result['status'], 'CONDITIONAL_ARITHMETIC_ONLY')
        self.assertEqual((result['activation_slot'], result['last_pre_activation_slot']), (96, 95))
        self.assertEqual((result['inclusive_maximum_seconds'], result['minimum_conditional_opening_seconds']), (26, 27))

    def test_migration_window_and_signed_saturation_close_without_a_bound(self):
        for first, anchor, time, epoch in [(34, 34, 1, 1), (1, 31, 1, 1), (1, 95, 1, 1),
                                           (1, 96, 1, 1), (1, 34, I64_MAX - 1, 1)]:
            with self.subTest(first=first, anchor=anchor, time=time, epoch=epoch):
                with self.assertRaises(ValueError):
                    conditional_arithmetic(Geometry(32, 0, 0), first, anchor, time, epoch, 200_000_000, [])


if __name__ == '__main__':
    unittest.main()
