"""Reconcile the published local CPMM accounting cases using integer math."""

import json
import unittest
from pathlib import Path


EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "evidence/cpmm_fee_profile/2026-11-19.public.json"
)
PPM = 1_000_000
BPS = 10_000


def ceil_ratio(amount, numerator, denominator):
    return (amount * numerator + denominator - 1) // denominator


class CpmmFeeProfileTests(unittest.TestCase):
    def test_both_token_observed_rounding(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        config = evidence["mainnet"]["config"]
        local = evidence["local"]
        self.assertEqual(
            (config["trade_fee_ppm"], config["creator_fee_ppm"], local["native_htfp_fee_bps"]),
            (2500, 500, 800),
        )
        cases = {case["case"]: case for case in local["cases"]}
        self.assertEqual(
            set(cases),
            {"wsol-to-htfp", "htfp-to-wsol", "htfp-process-finalize", "wsol-to-htfp-dust"},
        )

        combined_ppm = config["trade_fee_ppm"] + config["creator_fee_ppm"]
        native_bps = local["native_htfp_fee_bps"]
        for name, case in cases.items():
            with self.subTest(case=name):
                input_is_htfp = case["input"] == "HTFP"
                gross = int(case["gross"])
                input_withheld = ceil_ratio(gross, native_bps, BPS) if input_is_htfp else 0
                pool_input = gross - input_withheld
                combined = ceil_ratio(pool_input, combined_ppm, PPM)
                creator = combined * config["creator_fee_ppm"] // combined_ppm
                trade = combined - creator
                protocol = trade * config["protocol_share_of_trade_ppm"] // PPM
                fund = trade * config["fund_share_of_trade_ppm"] // PPM
                curve_input = pool_input - combined
                input_reserve = int(case["curve_exact_input_reserve"])
                output_reserve = int(case["curve_exact_output_reserve"])
                output = curve_input * output_reserve // (input_reserve + curve_input)
                output_withheld = 0 if input_is_htfp else ceil_ratio(output, native_bps, BPS)
                expected = {
                    "htfp_withheld_in": input_withheld,
                    "pool_input": pool_input,
                    "combined": combined,
                    "creator": creator,
                    "trade": trade,
                    "protocol": protocol,
                    "fund": fund,
                    "liquidity": trade - protocol - fund,
                    "curve_input": curve_input,
                    "curve_out": output,
                    "htfp_withheld_out": output_withheld,
                    "net_out": output - output_withheld,
                }
                self.assertEqual({key: int(case[key]) for key in expected}, expected)

        process_case = cases["htfp-process-finalize"]
        process = process_case["process"]
        lots, remainder = divmod(int(process["Q"]), 8)
        self.assertEqual(remainder, 0)
        self.assertEqual(int(process["burn"]), lots * 3)
        self.assertEqual(int(process_case["gross"]), lots * 5)
        self.assertEqual(process["reserve_delta"], process_case["net_out"])
