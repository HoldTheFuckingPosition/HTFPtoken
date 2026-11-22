"""Check current launch policy through the offline documentary CLI."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ALLOCATIONS = {
    "lge_base_units": 5_500_000_000_000_000_000,
    "pool_base_units": 3_500_000_000_000_000_000,
    "team_base_units": 500_000_000_000_000_000,
    "marketing_base_units": 500_000_000_000_000_000,
}


class LaunchManifestPolicyTests(unittest.TestCase):
    def run_checker(self, **sections):
        dossier = {"schema": "HTFP_LAUNCH_DOSSIER_V1", **sections}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dossier.json"
            path.write_text(json.dumps(dossier), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", "-m", "htfp_launch_manifest", str(path)],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "tools")},
                capture_output=True,
                text=True,
                timeout=10,
            )
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def check_funding(self, raised, pool, reserve):
        return self.run_checker(funding={
            "raised_lamports": str(raised),
            "pool_lamports": str(pool),
            "reserve_lamports": str(reserve),
        })

    def findings(self, report, field):
        return {(finding["code"], finding["path"]) for finding in report[field]}

    def test_production_volume_is_gross_one_percent_without_a_bucket(self):
        options = {
            "alpha": {"numerator": "1", "denominator": "100"},
            "global_control": False,
            "per_call_control": True,
            "structure": "PER_CALL_GROSS_EFFECTIVE_RESERVE_ONLY",
        }
        status, report = self.run_checker(volume=options)
        self.assertEqual(status, 0)
        self.assertFalse(any(item["path"].startswith("volume.") for item in report["open_items"]))
        status, _ = self.run_checker(volume={**options, "alpha": {"numerator": "2", "denominator": "200"}})
        self.assertEqual(status, 0)

        status, report = self.run_checker(volume={
            **options, "alpha": {"numerator": "1", "denominator": "1000"},
            "global_control": True, "refill_start_timestamp": "0",
        })
        self.assertEqual(status, 1)
        self.assertEqual(self.findings(report, "contradictions"), {
            ("POLICY_MISMATCH", "volume.alpha"),
            ("POLICY_MISMATCH", "volume.global_control"),
            ("POLICY_MISMATCH", "volume.refill_start_timestamp"),
        })

    def test_final_metadata_rejects_mutability_but_requires_separate_evidence(self):
        path = "identity.metadata_mutability"
        status, report = self.run_checker(identity={"metadata_mutability": "MUTABLE"})
        self.assertEqual(status, 1)
        self.assertIn(("POLICY_MISMATCH", path), self.findings(report, "contradictions"))

        status, report = self.run_checker(identity={"metadata_mutability": "IMMUTABLE"})
        self.assertEqual(status, 0)
        checks = {check["path"]: check["result"] for check in report["checks"]}
        self.assertEqual(checks[path], "MATCH")
        self.assertIn(("MISSING_INPUT", "identity.metadata_reference"),
                      self.findings(report, "open_items"))
        self.assertEqual(report["production_readiness"], "NOT_ASSESSED")

        status, report = self.run_checker(identity={"metadata_mutability": None})
        self.assertEqual(status, 0)
        self.assertIn(("MISSING_INPUT", path), self.findings(report, "open_items"))

    def test_confirmed_allocations_match_and_participant_ledger_remains_open(self):
        allocation = {name: str(amount) for name, amount in ALLOCATIONS.items()}
        status, report = self.run_checker(allocation={"complete": True, **allocation})
        self.assertEqual(status, 0)
        checks = {check["path"]: check["result"] for check in report["checks"]}
        opened = self.findings(report, "open_items")
        for name in allocation:
            with self.subTest(name=name):
                self.assertEqual(checks.get(f"allocation.{name}"), "MATCH")
                self.assertNotIn(("PROVISIONAL_CHOICE", f"allocation.{name}"), opened)
        self.assertIn(("MISSING_INPUT", "allocation.entitlement_reference"), opened)
        self.assertIn(("MISSING_INPUT", "allocation.remainder_reference"), opened)

    def test_equal_total_cannot_hide_wrong_allocations(self):
        for recipient, donor in (("lge_base_units", "team_base_units"),
                                 ("marketing_base_units", "pool_base_units")):
            with self.subTest(recipient=recipient, donor=donor):
                amounts = dict(ALLOCATIONS)
                amounts[recipient] += 1
                amounts[donor] -= 1
                allocation = {name: str(amount) for name, amount in amounts.items()}
                status, report = self.run_checker(allocation={"complete": True, **allocation})
                self.assertEqual(status, 1)
                self.assertEqual(self.findings(report, "contradictions"), {
                    ("POLICY_MISMATCH", f"allocation.{recipient}"),
                    ("POLICY_MISMATCH", f"allocation.{donor}"),
                })

    def test_both_complementary_roundings_are_possible(self):
        for pool, reserve in ((8, 3), (9, 2)):
            with self.subTest(pool=pool, reserve=reserve):
                status, report = self.check_funding(11, pool, reserve)
                self.assertEqual(status, 0)
                self.assertIn(("ROUNDING_UNRESOLVED", "funding"), self.findings(report, "open_items"))

    def test_deviation_beyond_rounding_is_a_contradiction(self):
        status, report = self.check_funding(11, 6, 5)
        self.assertEqual(status, 1)
        self.assertEqual(self.findings(report, "contradictions"), {
            ("FUNDING_RATIO_MISMATCH", "funding.pool_lamports"),
            ("FUNDING_RATIO_MISMATCH", "funding.reserve_lamports"),
        })
        self.assertNotIn(("ROUNDING_UNRESOLVED", "funding"), self.findings(report, "open_items"))

    def test_individually_adjacent_shares_must_conserve_total(self):
        for pool, reserve in ((8, 2), (9, 3)):
            with self.subTest(pool=pool, reserve=reserve):
                status, report = self.check_funding(11, pool, reserve)
                self.assertEqual(status, 1)
                self.assertEqual(self.findings(report, "contradictions"), {
                    ("FUNDING_TOTAL_MISMATCH", "funding"),
                })

    def test_exact_ratio_and_partial_input(self):
        status, report = self.check_funding(10, 8, 2)
        self.assertEqual(status, 0)
        self.assertNotIn(("ROUNDING_UNRESOLVED", "funding"), self.findings(report, "open_items"))

        status, report = self.run_checker(funding={"raised_lamports": "11", "pool_lamports": "6"})
        self.assertEqual(status, 1)
        self.assertEqual(self.findings(report, "contradictions"), {
            ("FUNDING_RATIO_MISMATCH", "funding.pool_lamports"),
        })
        self.assertIn(("MISSING_INPUT", "funding.reserve_lamports"), self.findings(report, "open_items"))


if __name__ == "__main__":
    unittest.main()
