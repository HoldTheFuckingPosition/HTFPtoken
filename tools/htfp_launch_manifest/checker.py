"""Strict offline documentary checks. Importing this module performs no checks."""

import hashlib
import json
import re

from . import policy as p

U64_MAX = (1 << 64) - 1
NOMINAL_SUPPLY = 10**19
INPUT_LIMIT = 65536
REPORT_LIMIT = 131072
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class InputError(Exception):
    def __init__(self, code, path="$"):
        self.code, self.path = code, path
        super().__init__(p.ERRORS[code])


def _pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise InputError("DUPLICATE_KEY")
        obj[key] = value
    return obj


def _number(_):
    raise InputError("JSON_NUMBER_NOT_ALLOWED")


def _nonfinite(_):
    raise InputError("NONFINITE_JSON")


def _scalar_strings(obj):
    stack = [obj]
    while stack:
        value = stack.pop()
        if isinstance(value, str):
            if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
                raise InputError("INVALID_TEXT")
        elif isinstance(value, dict):
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)


def _container_bounds(obj):
    stack = [(obj, 1)]
    while stack:
        value, depth = stack.pop()
        if isinstance(value, (dict, list)):
            if depth > 4:
                raise InputError("NESTING_LIMIT")
            children = value.values() if isinstance(value, dict) else value
            stack.extend((child, depth + 1) for child in children)
    if isinstance(obj, dict) and isinstance(obj.get("assertions"), list) and len(obj["assertions"]) > 16:
        raise InputError("COLLECTION_LIMIT")


def _unknown(obj, allowed, path):
    if set(obj) - set(allowed):
        raise InputError("UNKNOWN_FIELD", path)


def _integer(value, path):
    if not isinstance(value, str):
        raise InputError("TYPE_MISMATCH", path)
    if re.fullmatch(r"0|[1-9][0-9]*", value, re.ASCII) is None:
        raise InputError("INVALID_INTEGER", path)
    if len(value) > 20 or int(value) > U64_MAX:
        raise InputError("INTEGER_OUT_OF_RANGE", path)


def _public_key(value, path):
    if not 1 <= len(value) <= 44 or any(c not in BASE58 for c in value):
        raise InputError("INVALID_PUBKEY", path)
    integer = 0
    for char in value:
        integer = integer * 58 + BASE58.index(char)
    prefix = len(value) - len(value.lstrip("1"))
    raw = bytes(prefix) + integer.to_bytes((integer.bit_length() + 7) // 8, "big")
    if len(raw) != 32:
        raise InputError("INVALID_PUBKEY", path)
    encoded = ""
    n = int.from_bytes(raw, "big")
    while n:
        n, rem = divmod(n, 58)
        encoded = BASE58[rem] + encoded
    canonical = "1" * (len(raw) - len(raw.lstrip(b"\0"))) + encoded
    if canonical != value:
        raise InputError("INVALID_PUBKEY", path)


def _field(value, kind, path):
    if kind == "bool":
        if type(value) is not bool:
            raise InputError("TYPE_MISMATCH", path)
    elif kind == "fraction":
        if type(value) is not dict:
            raise InputError("TYPE_MISMATCH", path)
        _unknown(value, ("numerator", "denominator"), path)
        if set(value) != {"numerator", "denominator"}:
            raise InputError("TYPE_MISMATCH", path)
        for key in sorted(value):
            _integer(value[key], path + "." + key)
        if int(value["denominator"]) == 0:
            raise InputError("INVALID_FRACTION", path)
    elif kind == "u64":
        _integer(value, path)
    else:
        if type(value) is not str:
            raise InputError("TYPE_MISMATCH", path)
        if kind == "pubkey":
            _public_key(value, path)
        elif kind == "sha256":
            if re.fullmatch(r"[0-9a-f]{64}", value, re.ASCII) is None:
                raise InputError("INVALID_SHA256", path)
        elif kind == "text":
            if not value or len(value.encode("utf-8")) > 512 or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise InputError("INVALID_TEXT", path)
        else:
            raise RuntimeError("Unknown frozen field kind")


def _parse(raw):
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise InputError("INVALID_UTF8") from None
    try:
        obj = json.loads(text, object_pairs_hook=_pairs, parse_int=_number,
                         parse_float=_number, parse_constant=_nonfinite)
    except RecursionError:
        raise InputError("NESTING_LIMIT") from None
    except json.JSONDecodeError:
        raise InputError("INVALID_JSON") from None
    _scalar_strings(obj)
    _container_bounds(obj)
    if type(obj) is not dict:
        raise InputError("TYPE_MISMATCH")
    if obj.get("schema") != "HTFP_LAUNCH_DOSSIER_V1":
        raise InputError("SCHEMA_MISMATCH", "schema")
    _unknown(obj, set(p.GROUPS) | {"schema", "assertions"}, "$")
    values, assertions = {}, []
    for group in sorted(set(p.GROUPS) | {"assertions"}):
        section = obj.get(group)
        if group == "assertions":
            if section is None:
                continue
            if type(section) is not list:
                raise InputError("TYPE_MISMATCH", group)
            for index, assertion in enumerate(section):
                path = "assertions[" + str(index) + "]"
                if type(assertion) is not dict:
                    raise InputError("TYPE_MISMATCH", path)
                _unknown(assertion, ("subject", "claim", "citation", "claimed_status"), path)
                if not {"subject", "claim"} <= set(assertion):
                    raise InputError("TYPE_MISMATCH", path)
                for key in sorted(assertion):
                    if assertion[key] is None and key in ("citation", "claimed_status"):
                        continue
                    _field(assertion[key], "text", path + "." + key)
                assertions.append(assertion)
            continue
        if section is not None and type(section) is not dict:
            raise InputError("TYPE_MISMATCH", group)
        if section is None:
            section = {}
        _unknown(section, p.GROUPS[group], group)
        for field, kind in sorted(p.GROUPS[group].items()):
            value = section.get(field)
            path = group + "." + field
            if value is not None:
                _field(value, kind, path)
            values[path] = value
    return values, assertions


def _base(digest):
    return {"schema": "HTFP_LAUNCH_REPORT_V1", "scope": "DOCUMENTARY_ONLY",
            "policy_sources": dict(p.POLICY_SOURCES), "input_sha256": digest,
            "outcome": "NO_DOCUMENTARY_CONTRADICTION_FOUND", "production_readiness": "NOT_ASSESSED",
            "public_verification": "NOT_PERFORMED", "approval": "NOT_ESTABLISHED", "error": None,
            "checks": [], "contradictions": [], "open_items": [], "unverified_assertions": [], "derived": {}}


def error_report(code, path="$", digest=None):
    report = _base(digest)
    report["outcome"] = "INPUT_INVALID"
    report["error"] = {"code": code, "path": path, "message": p.ERRORS[code]}
    return 2, report


def _finding(code, path, sources):
    return {"code": code, "path": path, "source_ids": list(sources), "message": p.MESSAGES[code]}


def _assess(values, assertions, digest):
    report = _base(digest)
    checks, contradictions, opened = report["checks"], report["contradictions"], report["open_items"]
    derived = report["derived"]
    for path, value in sorted(values.items()):
        group = path.split(".", 1)[0]
        if value is None:
            opened.append(_finding("MISSING_INPUT", path, p.GROUP_SOURCES[group]))
        elif path in p.OPEN_PATHS:
            opened.append(_finding("OPEN_CHOICE", path, p.GROUP_SOURCES[group]))
        elif path in p.PROVISIONAL_PATHS:
            opened.append(_finding("PROVISIONAL_CHOICE", path, p.GROUP_SOURCES[group]))
    for path, rule in sorted(p.EXPECTED.items()):
        value = values[path]
        result = "MISSING" if value is None else "MATCH" if value == rule["expected"] else "CONTRADICTION"
        if result == "CONTRADICTION":
            contradictions.append(_finding("POLICY_MISMATCH", path, rule["source_ids"]))
        checks.append({"rule_id": path, "path": path, "result": result})

    def number(path):
        value = values[path]
        return int(value) if value is not None else None

    for relation in p.RELATIONSHIPS:
        before = len(contradictions)
        rule_id, sources = relation["id"], relation["source_ids"]
        result = "MISSING"

        def contradict(code, path):
            contradictions.append(_finding(code, path, sources))

        if rule_id == "ALLOCATION_TOTAL":
            amounts = [number("allocation." + key + "_base_units") for key in ("pool", "lge", "team", "marketing")]
            present = [a for a in amounts if a is not None]
            complete = values["allocation.complete"]
            if present:
                known = sum(present)
                derived["allocation_known_sum_base_units"] = str(known)
                if known > NOMINAL_SUPPLY:
                    derived["allocation_overallocated_base_units"] = str(known - NOMINAL_SUPPLY)
                    contradict("ALLOCATION_OVER_NOMINAL", "allocation")
                else:
                    derived["allocation_unallocated_from_provided_base_units"] = str(NOMINAL_SUPPLY - known)
                    result = "MATCH"
                    if known < NOMINAL_SUPPLY:
                        if complete is True and len(present) == 4:
                            contradict("COMPLETED_ALLOCATION_SHORTFALL", "allocation")
                        elif complete is not True:
                            opened.append(_finding("PARTIAL_ALLOCATION", "allocation", sources))
                            result = "OPEN"
            if complete is True and len(present) != 4:
                contradict("COMPLETION_MISSING_AMOUNTS", "allocation.complete")
        elif rule_id == "FUNDING_TOTAL":
            n, pool, reserve = (number("funding." + field) for field in ("raised_lamports", "pool_lamports", "reserve_lamports"))
            if pool is not None and reserve is not None:
                derived["funding_sum_lamports"] = str(pool + reserve)
            if n is not None and pool is not None and reserve is not None:
                result = "MATCH"
                if pool + reserve != n:
                    contradict("FUNDING_TOTAL_MISMATCH", "funding")
        elif rule_id == "FUNDING_RATIO":
            n, pool, reserve = (number("funding." + field) for field in ("raised_lamports", "pool_lamports", "reserve_lamports"))
            if n is not None:
                derived["funding_expected_pool_lamports"] = {"numerator": str(4 * n), "denominator": "5"}
                derived["funding_expected_reserve_lamports"] = {"numerator": str(n), "denominator": "5"}
                if pool is not None:
                    derived["funding_pool_difference_numerator"] = str(5 * pool - 4 * n)
                if reserve is not None:
                    derived["funding_reserve_difference_numerator"] = str(5 * reserve - n)
                if n % 5:
                    result = "ROUNDING_UNRESOLVED"
                    opened.append(_finding("ROUNDING_UNRESOLVED", "funding", sources))
                else:
                    result = "MATCH" if pool is not None and reserve is not None else "MISSING"
                    if pool is not None and pool != 4 * (n // 5):
                        contradict("FUNDING_RATIO_MISMATCH", "funding.pool_lamports")
                    if reserve is not None and reserve != n // 5:
                        contradict("FUNDING_RATIO_MISMATCH", "funding.reserve_lamports")
        elif rule_id == "ACTIVATION_EPOCH":
            epoch, activation = number("mint.scheduling_epoch"), number("mint.activation_epoch")
            if epoch is not None:
                expected = epoch + 2
                derived["activation_expected_epoch"] = str(expected)
                if expected > U64_MAX:
                    contradict("EPOCH_RELATION_OVERFLOW", "mint.scheduling_epoch")
                elif activation is not None:
                    result = "MATCH"
                    if activation != expected:
                        contradict("ACTIVATION_EPOCH_MISMATCH", "mint.activation_epoch")
        elif rule_id == "LP_LOCK_FRACTION":
            fraction = values["market.initial_received_lp_lock_fraction"]
            if fraction is not None:
                result = "MATCH"
                if int(fraction["numerator"]) != int(fraction["denominator"]):
                    contradict("LP_LOCK_FRACTION_MISMATCH", relation["report_path"])
        elif rule_id == "PERSONAL_WALLET_MATCH":
            a, b = values["market.creator_personal_wallet"], values["market.burn_earn_personal_wallet"]
            if a is not None and b is not None:
                result = "MATCH"
                if a != b:
                    contradict("PERSONAL_WALLET_MISMATCH", "market")
        elif rule_id == "INITIAL_CREDIT_CAPACITY":
            credit = number("volume.initial_credit_gross_base_units")
            capacity = number("volume.capacity_gross_base_units")
            if credit is not None and capacity is not None:
                result = "MATCH"
                if credit > capacity:
                    contradict("INITIAL_CREDIT_EXCEEDS_CAPACITY", "volume.initial_credit_gross_base_units")
        else:
            raise RuntimeError("Unknown frozen relationship")
        if len(contradictions) > before:
            result = "CONTRADICTION"
        checks.append({"rule_id": rule_id, "path": relation["report_path"], "result": result})
    report["contradictions"].sort(key=lambda finding: (finding["path"], finding["code"]))
    report["open_items"].sort(key=lambda finding: (finding["path"], finding["code"]))
    report["unverified_assertions"] = [_finding("EXTERNAL_GATE_UNVERIFIED", gate, p.EXTERNAL_SOURCES[gate]) for gate in p.EXTERNAL_GATES]
    report["unverified_assertions"].extend(_finding("ATTRIBUTED_ASSERTION_UNVERIFIED", "assertions[" + str(i) + "]", ("S98", "S99")) for i in range(len(assertions)))
    if contradictions:
        report["outcome"] = "CONTRADICTIONS_PRESENT"
        return 1, report
    return 0, report


def check_bytes(raw):
    """Assess exact input bytes; all data is intent/claims, never external truth."""
    if type(raw) is not bytes:
        raise TypeError("check_bytes requires bytes")
    if len(raw) > INPUT_LIMIT:
        return error_report("INPUT_TOO_LARGE")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        values, assertions = _parse(raw)
    except InputError as exc:
        return error_report(exc.code, exc.path, digest)
    return _assess(values, assertions, digest)


def serialize(report):
    raw = (json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(raw) > REPORT_LIMIT:
        raise RuntimeError("Documentary report exceeded frozen bound")
    return raw
