"""Offline calculation for the supported official-pool opening profile."""

import argparse
import hashlib
import json
import os
import stat
import sys

from .checker import (
    BASE58, INPUT_LIMIT, InputError, U64_MAX, _field, _nonfinite, _number, _pairs,
)

SCHEMA = "HTFP_OPENING_BOUND_V1"
PROFILE = "agave-v4.4.1-stable-tower"
AGAVE_COMMIT = "5bb304027fe1a166b02cb26dc8c161593f416fca"
TOKEN_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
I64_MAX = (1 << 63) - 1
NS_PER_SECOND = 10**9
MIN_SUPPORTED_DURATION_NS = 400_000_000
MINIMUM_SLOTS_PER_EPOCH = 32


class OpeningError(ValueError):
    def __init__(self, code, field):
        super().__init__(f"{code}: {field}")


def record(value, path, fields, optional=()):
    if value is None:
        raise OpeningError("MISSING_INPUT", path)
    if type(value) is not dict:
        raise OpeningError("EXPECTED_OBJECT", path)
    for key in sorted(set(value) - set(fields) - set(optional)):
        raise OpeningError("UNKNOWN_FIELD", f"{path}.{key}")
    data = {key: value.get(key) for key in fields}
    for key, kind in fields.items():
        item = data[key]
        field = f"{path}.{key}"
        if kind == "absent":
            if key not in value:
                raise OpeningError("MISSING_INPUT", field)
            if item is not None:
                raise OpeningError("FEE_CONFIGURATION_AUTHORITY_PRESENT", field)
            continue
        if item is None:
            raise OpeningError("MISSING_INPUT", field)
        if kind == "signature":
            number = 0
            if not isinstance(item, str) or not 64 <= len(item) <= 88:
                raise OpeningError("INVALID_SIGNATURE_ENCODING", field)
            for char in item:
                if char not in BASE58:
                    raise OpeningError("INVALID_SIGNATURE_ENCODING", field)
                number = number * 58 + BASE58.index(char)
            leading_zeroes = len(item) - len(item.lstrip("1"))
            if leading_zeroes + (number.bit_length() + 7) // 8 != 64 or number == 0:
                raise OpeningError("INVALID_SIGNATURE_ENCODING", field)
            continue
        _field(item, kind, field)
        if kind == "u64":
            data[key] = int(item)
    return data


def first_slot(epoch, geometry):
    value = geometry["first_normal_slot"] + (
        epoch - geometry["first_normal_epoch"]
    ) * geometry["slots_per_epoch"]
    if value > U64_MAX:
        raise OpeningError("SLOT_OVERFLOW", "epoch_schedule")
    return value


def epoch_for_slot(slot, geometry):
    before_normal = slot - geometry["first_normal_slot"]
    if before_normal < 0:
        raise OpeningError("UNSUPPORTED_WARMUP_EPOCH", "epoch_schedule")
    epoch = geometry["first_normal_epoch"] + before_normal // geometry["slots_per_epoch"]
    if epoch > U64_MAX:
        raise OpeningError("EPOCH_OVERFLOW", "epoch_schedule")
    return epoch


def check_epoch_geometry(geometry):
    slots = geometry["slots_per_epoch"]
    if slots < MINIMUM_SLOTS_PER_EPOCH:
        raise OpeningError("INVALID_EPOCH_LENGTH", "epoch_schedule.slots_per_epoch")
    first_epoch, first_slot = 0, 0
    if geometry["warmup"]:
        exponent = (slots - 1).bit_length()
        next_power_of_two = 1 << exponent
        if next_power_of_two > U64_MAX:
            raise OpeningError("SLOT_OVERFLOW", "epoch_schedule.slots_per_epoch")
        first_epoch = exponent - 5
        first_slot = next_power_of_two - MINIMUM_SLOTS_PER_EPOCH
    if (geometry["first_normal_epoch"], geometry["first_normal_slot"]) != (first_epoch, first_slot):
        raise OpeningError("EPOCH_GEOMETRY_MISMATCH", "epoch_schedule")


def tower_clock_upper_bound(anchor, start, next_start, last, max_slot_duration_ns):
    """Return an inclusive bound for descendant banks ending at last."""
    def drift_ceiling(first):
        # The Tower estimate is at most nominal elapsed duration + 150%.
        divisor = 2 * NS_PER_SECOND
        elapsed = (last - first) * max_slot_duration_ns
        return (5 * elapsed + divisor - 1) // divisor

    upper = max(anchor["unix_timestamp_s"], anchor["epoch_start_timestamp_s"] + drift_ceiling(start))
    if next_start is not None:
        # Reanchoring can occur as late as last if the boundary slots are skipped.
        upper += drift_ceiling(next_start)
    if upper >= I64_MAX:
        raise OpeningError("OPEN_TIME_OVERFLOW", "anchor")
    return upper


def calculate(dossier):
    root = record(dossier, "$", {
        "schema": "text", "genesis_hash": "pubkey", "market_identity_sha256": "sha256",
    }, ("runtime", "epoch_schedule", "fee_schedule_receipt", "anchor", "mint",
        "proposed_open_time_s", "funding_observation"))
    if root["schema"] != SCHEMA:
        raise OpeningError("UNSUPPORTED_SCHEMA", "schema")

    runtime = record(dossier.get("runtime"), "runtime", {
        "profile": "text", "agave_commit": "text", "max_slot_duration_ns": "u64",
        "covered_from_slot": "u64", "covered_through_slot": "u64",
        "coverage_evidence_sha256": "sha256",
    })
    if runtime["profile"] != PROFILE or runtime["agave_commit"] != AGAVE_COMMIT:
        raise OpeningError("UNSUPPORTED_RUNTIME_PROFILE", "runtime")
    if runtime["max_slot_duration_ns"] < MIN_SUPPORTED_DURATION_NS:
        raise OpeningError("UNSUPPORTED_SLOT_DURATION_NS", "runtime.max_slot_duration_ns")

    geometry = record(dossier.get("epoch_schedule"), "epoch_schedule", {
        "first_normal_slot": "u64", "first_normal_epoch": "u64",
        "slots_per_epoch": "u64", "warmup": "bool", "evidence_sha256": "sha256",
    })
    check_epoch_geometry(geometry)
    receipt = record(dossier.get("fee_schedule_receipt"), "fee_schedule_receipt", {
        "landed_slot": "u64", "signature": "signature", "evidence_sha256": "sha256",
        "mint": "pubkey", "successful_and_finalized": "bool",
        "basis_points": "u64", "maximum_fee_base": "u64",
    })
    if not receipt["successful_and_finalized"]:
        raise OpeningError("SCHEDULING_NOT_FINALIZED", "fee_schedule_receipt")
    scheduled_epoch = epoch_for_slot(receipt["landed_slot"], geometry)
    activation = scheduled_epoch + 2
    if activation > U64_MAX:
        raise OpeningError("EPOCH_OVERFLOW", "fee_schedule_receipt.landed_slot")
    activation_slot = first_slot(activation, geometry)
    last = activation_slot - 1
    if runtime["covered_through_slot"] < last:
        raise OpeningError("RUNTIME_COVERAGE_ENDS_BEFORE_ACTIVATION", "runtime.covered_through_slot")

    anchor = record(dossier.get("anchor"), "anchor", {
        "slot": "u64", "epoch": "u64", "epoch_start_timestamp_s": "u64",
        "unix_timestamp_s": "u64", "clock_evidence_sha256": "sha256", "finalized": "bool",
        "official_pool_absent": "bool",
    })
    anchor_epoch = epoch_for_slot(anchor["slot"], geometry)
    if not anchor["finalized"] or anchor["slot"] == 0 or anchor["slot"] < receipt["landed_slot"]:
        raise OpeningError("ANCHOR_NOT_FINALIZED_AFTER_SCHEDULING", "anchor")
    if not anchor["official_pool_absent"]:
        raise OpeningError("OFFICIAL_POOL_ALREADY_EXISTS", "anchor.official_pool_absent")
    if anchor["epoch"] != anchor_epoch:
        raise OpeningError("CLOCK_EPOCH_DOES_NOT_MATCH_SLOT", "anchor.epoch")
    if anchor_epoch >= activation:
        raise OpeningError("ACTIVE_ZERO_WINDOW_CLOSED", "anchor.epoch")
    if not 0 < anchor["epoch_start_timestamp_s"] <= anchor["unix_timestamp_s"] <= I64_MAX:
        raise OpeningError("INVALID_CLOCK_SECONDS", "anchor")

    mint = record(dossier.get("mint"), "mint", {
        "address": "pubkey", "program": "pubkey", "decimals": "u64", "observed_slot": "u64",
        "older_basis_points": "u64", "newer_basis_points": "u64", "newer_epoch": "u64",
        "newer_maximum_fee_base": "u64", "fee_configuration_authority": "absent",
        "evidence_sha256": "sha256",
    })
    if (mint["address"] != receipt["mint"] or mint["program"] != TOKEN_2022
            or mint["decimals"] != 7 or mint["observed_slot"] != anchor["slot"]):
        raise OpeningError("MINT_ANCHOR_MISMATCH", "mint")
    if (receipt["basis_points"] != 800 or receipt["maximum_fee_base"] != U64_MAX
            or mint["older_basis_points"] != 0 or mint["newer_basis_points"] != 800
            or mint["newer_maximum_fee_base"] != U64_MAX or mint["newer_epoch"] != activation):
        raise OpeningError("FEE_SCHEDULE_MISMATCH", "mint")

    start = first_slot(anchor_epoch, geometry)
    if runtime["covered_from_slot"] > start:
        raise OpeningError("RUNTIME_COVERAGE_STARTS_AFTER_EPOCH_ORIGIN", "runtime.covered_from_slot")
    next_start = first_slot(anchor_epoch + 1, geometry) if anchor_epoch == scheduled_epoch else None
    upper = tower_clock_upper_bound(anchor, start, next_start, last, runtime["max_slot_duration_ns"])
    proposed = None
    if dossier.get("proposed_open_time_s") is not None:
        _field(dossier["proposed_open_time_s"], "u64", "proposed_open_time_s")
        proposed = int(dossier["proposed_open_time_s"])
        if not upper < proposed <= I64_MAX:
            raise OpeningError("OPEN_TIME_OUTSIDE_PROVED_RANGE", "proposed_open_time_s")

    funding_checked = dossier.get("funding_observation") is not None
    if funding_checked:
        funding = record(dossier["funding_observation"], "funding_observation", {
            "slot": "u64", "unix_timestamp_s": "u64",
        })
        if funding["slot"] < anchor["slot"] or funding["slot"] >= activation_slot:
            raise OpeningError("FUNDING_OUTSIDE_ACTIVE_ZERO_WINDOW", "funding_observation.slot")
        current_time = funding["unix_timestamp_s"]
        if proposed is not None and current_time >= proposed:
            raise OpeningError("STALE_OPEN_TIME", "funding_observation.unix_timestamp_s")
        if funding["slot"] == anchor["slot"]:
            observed_upper = anchor["unix_timestamp_s"]
        else:
            boundary = next_start if next_start is not None and funding["slot"] >= next_start else None
            observed_upper = tower_clock_upper_bound(
                anchor, start, boundary, funding["slot"], runtime["max_slot_duration_ns"],
            )
        if not anchor["unix_timestamp_s"] <= current_time <= observed_upper:
            raise OpeningError("CLOCK_OUTSIDE_PROVED_RANGE", "funding_observation.unix_timestamp_s")

    return {
        "status": "CONDITIONAL_OFFLINE_BOUND",
        "dossier_sha256": hashlib.sha256(json.dumps(
            dossier, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest(),
        "genesis_hash": root["genesis_hash"],
        "market_identity_sha256": root["market_identity_sha256"],
        "mint": mint["address"],
        "scheduling_epoch": str(scheduled_epoch),
        "activation_epoch": str(activation),
        "first_activation_slot": str(activation_slot),
        "last_pre_activation_slot": str(last),
        "maximum_pre_activation_clock_s": str(upper),
        "minimum_open_time_s": str(upper + 1),
        "proposed_open_time_s": str(proposed) if proposed is not None else None,
        "funding_observation_consistent": True if funding_checked else None,
    }


def load_dossier(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise OpeningError("EXPECTED_REGULAR_FILE", "dossier")
        raw = source.read(INPUT_LIMIT + 1)
    if len(raw) > INPUT_LIMIT:
        raise OpeningError("INPUT_TOO_LARGE", "dossier")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_int=_number,
                      parse_float=_number, parse_constant=_nonfinite)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", help="Path to the normalized opening inputs in JSON")
    args = parser.parse_args(argv)
    try:
        report = calculate(load_dossier(args.dossier))
    except InputError as exc:
        print(f"{exc.code}: {exc.path}", file=sys.stderr)
        return 2
    except OpeningError as exc:
        print(exc, file=sys.stderr)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        print("INVALID_OR_UNREADABLE_DOSSIER", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
