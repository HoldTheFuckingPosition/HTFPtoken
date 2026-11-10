"""Pure integer allocation for the approved LOCAL_TEST_ONLY LGE rehearsal."""

import argparse
import json

SUPPLY_BASE_UNITS = 10_000_000_000_000_000_000
PARTICIPANT_BASE_UNITS = 5_500_000_000_000_000_000
POOL_BASE_UNITS = 3_500_000_000_000_000_000
TEAM_BASE_UNITS = 500_000_000_000_000_000
MARKETING_BASE_UNITS = 500_000_000_000_000_000


def fixture():
    """Return fresh fake-ID/integer-lamport pairs totalling eleven SOL."""
    return [
        ("participant-1", 500_000_000),
        ("participant-2", 1_000_000_000),
        ("participant-3", 2_000_000_000),
        ("participant-4", 3_000_000_000),
        ("participant-5", 4_500_000_000),
    ]


def make_plan(contributors):
    """Return a fresh JSON-ready test plan from (ID,lamports) pairs.

    Positive exact Python integers are weights and lamport contributions.
    Mathematical integers are not silently converted to floating point or
    claimed executable native balances. Native callers check their own limits.
    IDs are nonempty strings, unique and sorted lexicographically. The test-only
    rounding rule awards residual units by remainder descending, then ID.
    """
    if not isinstance(contributors, (list, tuple)):
        raise TypeError("contributors must be a list or tuple of pairs")
    if not contributors:
        raise ValueError("at least one contributor is required")
    weights = {}
    for pair in contributors:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("each contributor must contain an ID and lamports")
        identifier, lamports = pair
        if type(identifier) is not str:
            raise TypeError("participant ID must be a string")
        if not identifier or identifier in weights:
            raise ValueError("participant IDs must be nonempty and unique")
        if type(lamports) is not int:
            raise TypeError("contribution lamports must be exact integers")
        if lamports <= 0:
            raise ValueError("contribution lamports must be positive")
        weights[identifier] = lamports
    total = sum(weights.values())
    floors, remainders = {}, {}
    for identifier, weight in weights.items():
        floors[identifier], remainders[identifier] = divmod(PARTICIPANT_BASE_UNITS * weight, total)
    residual = PARTICIPANT_BASE_UNITS - sum(floors.values())
    order = sorted(weights, key=lambda identifier: (-remainders[identifier], identifier))
    awarded = set(order[:residual])
    participants = [
        {
            "id": identifier,
            "contribution_lamports": str(weights[identifier]),
            "token_base_units": str(floors[identifier] + (identifier in awarded)),
            "floor_base_units": str(floors[identifier]),
            "remainder_numerator": str(remainders[identifier]),
            "rounding_bonus_base_units": "1" if identifier in awarded else "0",
        }
        for identifier in sorted(weights)
    ]
    reserve = total // 5
    return {
        "schema": "htfp-lge-rehearsal-plan-v1",
        "scope": "LOCAL_TEST_ONLY",
        "supply_base_units": str(SUPPLY_BASE_UNITS),
        "decimals": "7",
        "total_contribution_lamports": str(total),
        "token_allocations_base_units": {
            "participants": str(PARTICIPANT_BASE_UNITS), "pool": str(POOL_BASE_UNITS),
            "team": str(TEAM_BASE_UNITS), "marketing": str(MARKETING_BASE_UNITS),
        },
        "sol_allocations_lamports": {"reserve": str(reserve), "pool": str(total - reserve)},
        "participants": participants,
        "participant_rounding_residual_base_units": str(residual),
        "distributor_token_remainder_base_units": "0",
        "test_rules": {
            "participant_rounding": "FLOOR_THEN_LARGEST_REMAINDER_DESCENDING_THEN_ID_ASCENDING",
            "sol_rounding": "RESERVE_FLOOR_TOTAL_DIV_5_POOL_RESIDUAL",
            "rounding_rules_are_test_only": True,
            "ordinary_allocations_require_multiple_of_eight": False,
            "operations_budget": "SEPARATE_FROM_ALL_CONTRIBUTED_LAMPORTS",
            "wallets": "FAKE_TEST_LABELS_NO_KEYS_OR_ACCOUNTS",
        },
        "test_timing": {
            "initial_fee_basis_points": "0", "scheduled_fee_basis_points": "800",
            "maximum_fee_base_units": "18446744073709551615",
            "activation_epoch": "ACTUAL_UPDATE_EPOCH_E_PLUS_2",
            "opening_rule": "SYNTHETIC_E_PLUS_2_BOUNDARY_PLUS_TEST_DELAY",
            "opening_delay_seconds": "14400",
            "real_epoch_wall_clock_mapping": "UNSELECTED",
        },
        "assurance": {
            "native_execution_performed": False, "funds_received_or_distributed": False,
            "keys_or_accounts_created": False, "pool_created": False,
            "production_rounding_selected": False, "public_action_authorized": False,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Print the fixed local fake LGE plan; no blockchain access.")
    parser.parse_args(argv)
    print(json.dumps(make_plan(fixture()), ensure_ascii=True, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
