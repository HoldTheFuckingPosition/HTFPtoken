"""Finite independent integer/Fraction properties for the new local planner."""

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.htfp_lge_rehearsal import fixture, make_plan
from tools.htfp_lge_rehearsal.plan import main as plan_main

COUNTS = {"planner_calls": 0, "fixture_calls": 0, "CLI_fixture_calls": 0,
          "generated_input_cases": 0, "participant_fraction_checks": 0,
          "permutation_checks": 0, "scale_checks": 0, "invalid_input_checks": 0}


def invoke(contributors):
    COUNTS["planner_calls"] += 1
    return make_plan(contributors)


def fake_fixture():
    COUNTS["fixture_calls"] += 1
    return fixture()


class AllocationTests(unittest.TestCase):
    def assert_plan_properties(self, inputs, plan):
        participant_total = 5_500_000_000_000_000_000
        total = sum(weight for _, weight in inputs)
        allocations = plan["token_allocations_base_units"]
        self.assertEqual(sum(map(int, allocations.values())), 10_000_000_000_000_000_000)
        self.assertEqual(int(allocations["participants"]), participant_total)
        rows = plan["participants"]
        self.assertEqual(sum(int(row["token_base_units"]) for row in rows), participant_total)
        self.assertEqual([row["id"] for row in rows], sorted(identifier for identifier, _ in inputs))
        self.assertEqual(plan["total_contribution_lamports"], str(total))
        reserve, pool = (int(plan["sol_allocations_lamports"][key]) for key in ("reserve", "pool"))
        self.assertEqual(reserve + pool, total)
        self.assertLessEqual(reserve * 5, total)
        self.assertLess(total, (reserve + 1) * 5)
        self.assertLess(abs(Fraction(pool) - Fraction(4 * total, 5)), 1)
        weights = dict(inputs)
        upward, downward = [], []
        for row in rows:
            actual = int(row["token_base_units"])
            ideal = Fraction(participant_total * weights[row["id"]], total)
            self.assertLess(abs(actual - ideal), 1)
            floor = ideal.numerator // ideal.denominator
            self.assertEqual(int(row["floor_base_units"]), floor)
            self.assertEqual(int(row["remainder_numerator"]), (ideal - floor) * total)
            bonus = int(row["rounding_bonus_base_units"])
            self.assertIn(bonus, (0, 1))
            self.assertEqual(actual - floor, bonus)
            self.assertEqual(int(row["contribution_lamports"]), weights[row["id"]])
            if ideal.denominator != 1:
                (upward if actual > ideal else downward).append((ideal - floor, row["id"]))
            COUNTS["participant_fraction_checks"] += 1
        # Exchange condition: no rounded-up participant has a smaller ideal
        # fraction than a rounded-down participant; exact ties use the ID.
        for up_fraction, up_id in upward:
            for down_fraction, down_id in downward:
                self.assertTrue(up_fraction > down_fraction or
                                (up_fraction == down_fraction and up_id < down_id))
        self.assertEqual(sum(int(row["rounding_bonus_base_units"]) for row in rows),
                         int(plan["participant_rounding_residual_base_units"]))
        self.assertEqual(plan["scope"], "LOCAL_TEST_ONLY")
        self.assertEqual(plan["distributor_token_remainder_base_units"], "0")
        self.assertFalse(plan["test_rules"]["ordinary_allocations_require_multiple_of_eight"])
        self.assertTrue(all(value is False for value in plan["assurance"].values()))

    def test_literal_eleven_SOL_fixture(self):
        inputs = fake_fixture()
        self.assertEqual(inputs, [("participant-1", 500_000_000), ("participant-2", 1_000_000_000),
                                  ("participant-3", 2_000_000_000), ("participant-4", 3_000_000_000),
                                  ("participant-5", 4_500_000_000)])
        plan = invoke(inputs)
        self.assertEqual(plan["total_contribution_lamports"], "11000000000")
        self.assertEqual(plan["token_allocations_base_units"], {
            "participants": "5500000000000000000", "pool": "3500000000000000000",
            "team": "500000000000000000", "marketing": "500000000000000000"})
        self.assertEqual(plan["sol_allocations_lamports"], {"reserve": "2200000000", "pool": "8800000000"})
        self.assertEqual([row["token_base_units"] for row in plan["participants"]],
                         ["250000000000000000", "500000000000000000", "1000000000000000000",
                          "1500000000000000000", "2250000000000000000"])
        self.assertEqual(plan["participant_rounding_residual_base_units"], "0")
        self.assert_plan_properties(inputs, plan)

    def test_remainder_tie_and_non_Q8_allocation(self):
        inputs = [("z", 1), ("a", 1), ("m", 1)]
        plan = invoke(inputs)
        self.assertEqual([(r["id"], r["token_base_units"], r["rounding_bonus_base_units"])
                          for r in plan["participants"]],
                         [("a", "1833333333333333334", "1"),
                          ("m", "1833333333333333333", "0"),
                          ("z", "1833333333333333333", "0")])
        self.assertTrue(any(int(row["token_base_units"]) % 8 for row in plan["participants"]))
        self.assert_plan_properties(inputs, plan)

    def test_odd_lamport_policy_is_only_test_rule(self):
        for amount in (1, 2, 3, 4, 5, 6, 10_000_000_001, 12_000_000_000, 2**64 - 1):
            plan = invoke([("only", amount)])
            self.assertEqual(plan["participants"][0]["token_base_units"], "5500000000000000000")
            self.assert_plan_properties([("only", amount)], plan)
            self.assertTrue(plan["test_rules"]["rounding_rules_are_test_only"])

    def test_finite_constructive_invariants(self):
        rng = random.Random(141_2026)
        for case in range(256):
            count = case % 12 + 1
            if case % 4 == 0:
                weights = [rng.randrange(1, 100) for _ in range(count)]
            elif case % 4 == 1:
                weights = [(2**53 + rng.randrange(1, 1000)) for _ in range(count)]
            elif case % 4 == 2:
                weights = [rng.randrange(1, 10**12) for _ in range(count)]
            else:
                weights = [2**64 + rng.randrange(1, 10**8) for _ in range(count)]
            inputs = [(f"fake-{index:02d}", weight) for index, weight in enumerate(weights)]
            before = deepcopy(inputs)
            plan = invoke(inputs)
            self.assert_plan_properties(inputs, plan)
            shuffled = list(inputs)
            rng.shuffle(shuffled)
            self.assertEqual(invoke(shuffled), plan)
            COUNTS["permutation_checks"] += 1
            factor = case % 23 + 1
            scaled = invoke([(identifier, weight * factor) for identifier, weight in inputs])
            self.assertEqual({row["id"]: row["token_base_units"] for row in scaled["participants"]},
                             {row["id"]: row["token_base_units"] for row in plan["participants"]})
            COUNTS["scale_checks"] += 1
            self.assertEqual(inputs, before)
            COUNTS["generated_input_cases"] += 1

    def test_invalid_inputs(self):
        bad = [(None, TypeError), ({"a": 1}, TypeError), ([], ValueError),
               ([("a", 0)], ValueError), ([("a", -1)], ValueError),
               ([("a", True)], TypeError), ([("a", 0.5)], TypeError),
               ([("a", "1")], TypeError), ([("a", None)], TypeError),
               ([("", 1)], ValueError), ([(1, 1)], TypeError),
               ([("a", 1), ("a", 2)], ValueError), ([("a",)], ValueError),
               ([("a", 1, 2)], ValueError), (["a"], ValueError)]
        for value, error in bad:
            with self.assertRaises(error):
                invoke(value)
            COUNTS["invalid_input_checks"] += 1

    def test_fresh_objects_and_no_input_mutation(self):
        inputs = fake_fixture()
        before = deepcopy(inputs)
        first = invoke(inputs)
        pristine = deepcopy(first)
        first["participants"][0]["token_base_units"] = "0"
        first["assurance"]["native_execution_performed"] = True
        first["test_rules"]["wallets"] = "changed"
        self.assertEqual(invoke(inputs), pristine)
        self.assertEqual(inputs, before)
        altered_fixture = fake_fixture()
        altered_fixture.append(("extra", 1))
        self.assertEqual(fake_fixture(), before)

    def test_JSON_shape_and_default_CLI(self):
        plan = invoke(fake_fixture())
        pending = [plan]
        while pending:
            item = pending.pop()
            self.assertNotIsInstance(item, float)
            if isinstance(item, dict):
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
            elif type(item) is int:
                self.fail("JSON numeric field must be a decimal string")
        self.assertEqual(plan["test_timing"]["opening_delay_seconds"], "14400")
        self.assertEqual(plan["test_timing"]["real_epoch_wall_clock_mapping"], "UNSELECTED")
        stream = io.StringIO()
        COUNTS["CLI_fixture_calls"] += 1
        COUNTS["planner_calls"] += 1  # nested default CLI make_plan invocation
        COUNTS["fixture_calls"] += 1
        with redirect_stdout(stream):
            plan_main([])
        self.assertEqual(stream.getvalue(), json.dumps(plan, ensure_ascii=True, sort_keys=True, indent=2) + "\n")


def source_map():
    names = ["tools/htfp_lge_rehearsal/plan.py", "tools/htfp_lge_rehearsal/__init__.py",
             "tools/htfp_lge_rehearsal/README.md", "tests/lge_pool/test_allocation.py"]
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main():
    parser = argparse.ArgumentParser(description="Verify only the new local integer allocation planner.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    assert sys.version_info[:2] == (3, 12) and sys.dont_write_bytecode
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=False)
    before = source_map()
    for name, digest in before.items():
        raw = (ROOT / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        target = out / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AllocationTests))
    after = source_map()
    record = {"schema": "HTFP_LGE_ALLOCATION_TEST_RESULT_V1", "scope": "LOCAL_TEST_ONLY",
              "status": "PASS" if result.wasSuccessful() and before == after else "FAIL",
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skips": len(result.skipped), "counts": COUNTS, "generated_seed": 141_2026,
              "source_sha256": before, "sources_unchanged": before == after,
              "stdout": stream.getvalue(), "new_native_VM_and_sends": 0,
              "network_HTTP_signing_keys_public_actions": 0,
              "limits": "Finite256constructive inputs plus directed cases; no exhaustive/shrinking/native/public proof."}
    raw = (json.dumps(record, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()
    (out / "RESULT.json").write_bytes(raw)
    print(json.dumps({"status": record["status"], "tests_run": result.testsRun, "counts": COUNTS,
                      "result": str(out / "RESULT.json"), "sha256": hashlib.sha256(raw).hexdigest()}, sort_keys=True))
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
