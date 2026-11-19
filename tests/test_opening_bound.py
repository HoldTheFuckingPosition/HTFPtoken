"""Focused offline checks for the launch bound, with synthetic input only."""

import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.htfp_launch_manifest import opening

HASH = "a" * 64
MINT = "1" * 31 + "2"


def dossier():
    return {
        "schema": opening.SCHEMA,
        "genesis_hash": "1" * 31 + "3",
        "market_identity_sha256": HASH,
        "runtime": {
            "profile": opening.PROFILE,
            "agave_commit": opening.AGAVE_COMMIT,
            "max_slot_duration_ns": "400000000",
            "covered_from_slot": "128", "covered_through_slot": "191",
            "coverage_evidence_sha256": HASH,
        },
        "epoch_schedule": {
            "first_normal_slot": "0", "first_normal_epoch": "0",
            "slots_per_epoch": "32", "warmup": False, "evidence_sha256": HASH,
        },
        "fee_schedule_receipt": {
            "landed_slot": "128", "signature": "1" * 63 + "2", "evidence_sha256": HASH,
            "mint": MINT, "successful_and_finalized": True,
            "basis_points": "800", "maximum_fee_base": str(opening.U64_MAX),
        },
        "anchor": {
            "slot": "129", "epoch": "4", "epoch_start_timestamp_s": "100",
            "unix_timestamp_s": "110", "clock_evidence_sha256": HASH, "finalized": True,
            "official_pool_absent": True,
        },
        "mint": {
            "address": MINT, "program": opening.TOKEN_2022, "decimals": "7",
            "observed_slot": "129", "older_basis_points": "0", "newer_basis_points": "800",
            "newer_epoch": "6", "newer_maximum_fee_base": str(opening.U64_MAX),
            "fee_configuration_authority": None, "evidence_sha256": HASH,
        },
    }


class OpeningBoundTest(unittest.TestCase):
    def test_closed_bound_and_first_permissible_second(self):
        doc = dossier()
        doc["proposed_open_time_s"] = "195"
        doc["funding_observation"] = {"slot": "191", "unix_timestamp_s": "194"}
        result = opening.calculate(doc)
        self.assertEqual(result["status"], "CONDITIONAL_OFFLINE_BOUND")
        self.assertEqual(result["mint"], MINT)
        self.assertEqual(result["market_identity_sha256"], HASH)
        self.assertRegex(result["dossier_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual(result["maximum_pre_activation_clock_s"], "194")
        self.assertEqual(result["minimum_open_time_s"], "195")
        self.assertTrue(result["funding_observation_consistent"])
        doc["proposed_open_time_s"] = "194"
        with self.assertRaisesRegex(opening.OpeningError, "OPEN_TIME_OUTSIDE_PROVED_RANGE"):
            opening.calculate(doc)

    def test_later_finalized_anchor_uses_one_epoch(self):
        doc = dossier()
        doc["anchor"].update(slot="161", epoch="5", epoch_start_timestamp_s="117",
                             unix_timestamp_s="118")
        doc["mint"]["observed_slot"] = "161"
        result = opening.calculate(doc)
        self.assertEqual(result["scheduling_epoch"], "4")
        self.assertEqual(result["first_activation_slot"], "192")
        self.assertEqual(result["minimum_open_time_s"], "149")

    def test_actual_later_landing_rebinds_activation(self):
        doc = dossier()
        doc["fee_schedule_receipt"]["landed_slot"] = "160"
        doc["anchor"].update(slot="161", epoch="5")
        doc["mint"]["observed_slot"] = "161"
        doc["runtime"]["covered_through_slot"] = "223"
        with self.assertRaisesRegex(opening.OpeningError, "FEE_SCHEDULE_MISMATCH"):
            opening.calculate(doc)
        doc["mint"]["newer_epoch"] = "7"
        result = opening.calculate(doc)
        self.assertEqual(result["activation_epoch"], "7")
        self.assertEqual(result["first_activation_slot"], "224")

    def test_late_initialization_even_if_timestamp_has_not_advanced(self):
        doc = dossier()
        doc["funding_observation"] = {"slot": "192", "unix_timestamp_s": "110"}
        with self.assertRaisesRegex(opening.OpeningError, "FUNDING_OUTSIDE_ACTIVE_ZERO_WINDOW"):
            opening.calculate(doc)
        doc["funding_observation"]["slot"] = "128"
        with self.assertRaisesRegex(opening.OpeningError, "FUNDING_OUTSIDE_ACTIVE_ZERO_WINDOW"):
            opening.calculate(doc)

    def test_stale_time_or_impossible_clock_profile(self):
        doc = dossier()
        doc["proposed_open_time_s"] = "195"
        # Contradictory input. This Clock is unreachable under the admitted bound.
        doc["funding_observation"] = {"slot": "191", "unix_timestamp_s": "195"}
        with self.assertRaisesRegex(opening.OpeningError, "STALE_OPEN_TIME"):
            opening.calculate(doc)
        del doc["proposed_open_time_s"]
        with self.assertRaisesRegex(opening.OpeningError, "CLOCK_OUTSIDE_PROVED_RANGE"):
            opening.calculate(doc)
        doc["funding_observation"] = {"slot": "129", "unix_timestamp_s": "111"}
        with self.assertRaisesRegex(opening.OpeningError, "CLOCK_OUTSIDE_PROVED_RANGE"):
            opening.calculate(doc)

    def test_no_runtime_guess_or_incomplete_coverage(self):
        doc = dossier()
        doc["runtime"]["profile"] = "alpenglow"
        with self.assertRaisesRegex(opening.OpeningError, "UNSUPPORTED_RUNTIME_PROFILE"):
            opening.calculate(doc)
        doc["runtime"]["profile"] = opening.PROFILE
        doc["runtime"]["covered_through_slot"] = "190"
        with self.assertRaisesRegex(opening.OpeningError, "RUNTIME_COVERAGE_ENDS_BEFORE_ACTIVATION"):
            opening.calculate(doc)
        doc["runtime"]["covered_through_slot"] = "191"
        doc["runtime"]["covered_from_slot"] = "129"
        with self.assertRaisesRegex(opening.OpeningError, "RUNTIME_COVERAGE_STARTS_AFTER_EPOCH_ORIGIN"):
            opening.calculate(doc)

    def test_geometry_must_match_canonical_warmup(self):
        doc = dossier()
        doc["epoch_schedule"].update(slots_per_epoch="64", warmup=True, first_normal_epoch="1",
                                     first_normal_slot="0")
        with self.assertRaisesRegex(opening.OpeningError, "EPOCH_GEOMETRY_MISMATCH"):
            opening.calculate(doc)
        doc["epoch_schedule"]["first_normal_slot"] = "32"
        doc["fee_schedule_receipt"]["landed_slot"] = "31"
        with self.assertRaisesRegex(opening.OpeningError, "UNSUPPORTED_WARMUP_EPOCH"):
            opening.calculate(doc)

    def test_requires_pool_absence_and_complete_exact_mint_binding(self):
        doc = dossier()
        doc["anchor"]["official_pool_absent"] = False
        with self.assertRaisesRegex(opening.OpeningError, "OFFICIAL_POOL_ALREADY_EXISTS"):
            opening.calculate(doc)
        doc["anchor"]["official_pool_absent"] = True
        del doc["mint"]["fee_configuration_authority"]
        with self.assertRaisesRegex(opening.OpeningError, "MISSING_INPUT"):
            opening.calculate(doc)
        doc["mint"]["fee_configuration_authority"] = MINT
        with self.assertRaisesRegex(opening.OpeningError, "FEE_CONFIGURATION_AUTHORITY_PRESENT"):
            opening.calculate(doc)
        doc["mint"]["fee_configuration_authority"] = None
        doc["mint"]["address"] = "1" * 31 + "4"
        with self.assertRaisesRegex(opening.OpeningError, "MINT_ANCHOR_MISMATCH"):
            opening.calculate(doc)

    def test_bad_units_and_overflow(self):
        doc = dossier()
        doc["runtime"]["max_slot_duration_ns"] = "0.4"
        with self.assertRaises(opening.InputError):
            opening.calculate(doc)
        doc["runtime"]["max_slot_duration_ns"] = "400"
        with self.assertRaisesRegex(opening.OpeningError, "UNSUPPORTED_SLOT_DURATION_NS"):
            opening.calculate(doc)
        doc["runtime"]["max_slot_duration_ns"] = "400000000"
        doc["anchor"]["unix_timestamp_s"] = str(opening.I64_MAX)
        with self.assertRaisesRegex(opening.OpeningError, "OPEN_TIME_OVERFLOW"):
            opening.calculate(doc)
        doc["anchor"]["unix_timestamp_s"] = "110"
        doc["epoch_schedule"]["slots_per_epoch"] = str(opening.U64_MAX)
        with self.assertRaisesRegex(opening.OpeningError, "SLOT_OVERFLOW"):
            opening.calculate(doc)

    def test_cli_validates_types_and_does_not_report_admission(self):
        with TemporaryDirectory() as temp:
            path = Path(temp, "dossier.json")
            path.write_text(json.dumps(dossier()), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(opening.main([str(path)]), 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "CONDITIONAL_OFFLINE_BOUND")
            path.write_text('{"schema": "one", "schema": "two"}', encoding="utf-8")
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(opening.main([str(path)]), 2)
            self.assertIn("DUPLICATE_KEY", errors.getvalue())

    def test_bound_dominates_every_small_skipped_slot_trace(self):
        # Exhaust the choices of where a new Bank appears and whether it
        # inherits the parent or takes the maximum admissible estimate.
        # Maximizing both timestamp and anchor suffices for the other estimates.
        for width in range(1, 6):
            for duration in (1, 399_999_999, 400_000_000, 400_000_001, 1_300_000_000):
                for anchor_slot in range(2 * width):
                    for inherited in (12, 19):
                        boundary = width
                        last = 2 * width - 1
                        start = 0 if anchor_slot < boundary else boundary
                        upper = opening.tower_clock_upper_bound(
                            {"epoch_start_timestamp_s": 12, "unix_timestamp_s": inherited},
                            start, boundary if start == 0 else None, last, duration,
                        )
                        states = {anchor_slot: {(inherited, 12)}}
                        for slot in range(anchor_slot + 1, last + 1):
                            states[slot] = set()
                            for parent in range(anchor_slot, slot):
                                parent_start = 0 if parent < boundary else boundary
                                for timestamp, epoch_start in states[parent]:
                                    nominal_ns = (slot - parent_start) * duration
                                    debit = (nominal_ns + nominal_ns * 150 // 100) // 10**9
                                    for current in (timestamp, max(timestamp, epoch_start + debit)):
                                        next_start = current if parent < boundary <= slot else epoch_start
                                        states[slot].add((current, next_start))
                        maximum = max(stamp for at_slot in states.values() for stamp, _ in at_slot)
                        self.assertGreater(upper + 1, maximum)


if __name__ == "__main__":
    unittest.main()
