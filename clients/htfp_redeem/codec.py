"""Strict offline Redeem descriptor codec; no execution or authorization proof."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from ._constants import (
    ASSURANCE, ERROR_MESSAGES, FINDING_CATALOG, PROFILE_BYTES, PROFILE_NAME,
    PROFILE_SHA256, SOURCE_BINDINGS,
)

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_ROUTES = ("owner", "pda", "native_multisig")
_HEADER = bytes.fromhex("485446500102")
_ROLES = ("config", "inventory", "mint", "source", "reserve", "recipient",
          "authority", "token2022", "system")
_FIXED = {0: "config", 1: "inventory", 2: "mint", 4: "reserve",
          7: "token2022", 8: "system"}
_LIMIT = 16384


class _Invalid(Exception):
    def __init__(self, code, path="$"):
        self.code, self.path = code, path
        super().__init__(code)


def _base_report(input_hash):
    return {
        "schema": "htfp-redeem-report-v1", "status": "ERROR",
        "operation": None, "profile": "UNCONFIGURED", "input_sha256": input_hash,
        "profile_sha256": PROFILE_SHA256, "source_bindings": dict(SOURCE_BINDINGS),
        "error": None,
        "validation": {"body": "UNASSESSED", "descriptor": "UNASSESSED",
                       "intent": "UNASSESSED"},
        "descriptor": None, "intent": None, "account_requirements": [], "findings": [],
        "assurance": deepcopy(ASSURANCE),
    }


def _error(exc, input_hash=None):
    report = _base_report(input_hash)
    report["error"] = {"code": exc.code, "path": exc.path,
                       "message": ERROR_MESSAGES[exc.code]}
    return report, 2


def _read_regular(path, limit, unreadable, oversized):
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise _Invalid(unreadable)
        chunks, remaining = [], limit + 1
        while remaining:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > limit:
            raise _Invalid(oversized)
        return raw
    except (OSError, ValueError, TypeError):
        raise _Invalid(unreadable) from None
    finally:
        if fd is not None:
            os.close(fd)


def _profile():
    raw = _read_regular(Path(__file__).with_name("PROFILE.json"), PROFILE_BYTES,
                        "SOURCE_BINDING_ERROR", "SOURCE_BINDING_ERROR")
    if len(raw) != PROFILE_BYTES or hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise _Invalid("SOURCE_BINDING_ERROR")
    # Exact trusted bytes have already been authenticated; no source/public fetch.
    return json.loads(raw)["public_keys"]


def _reject_number(_):
    raise _Invalid("INVALID_JSON")


def _object_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise _Invalid("INVALID_JSON")
        obj[key] = value
    return obj


def _parse(raw):
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _Invalid("INVALID_UTF8") from None
    if text.startswith("\ufeff"):
        raise _Invalid("INVALID_UTF8")
    try:
        obj = json.loads(text, object_pairs_hook=_object_pairs,
                         parse_int=_reject_number, parse_float=_reject_number,
                         parse_constant=_reject_number)
    except (ValueError, TypeError):
        raise _Invalid("INVALID_JSON") from None
    except RecursionError:
        raise _Invalid("DEPTH_EXCEEDED") from None
    # Check all Unicode scalars first, including object keys. Iterative walks
    # keep pathological nesting from exhausting the Python call stack.
    strings, stack = [], [obj]
    while stack:
        value = stack.pop()
        if isinstance(value, str):
            if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
                raise _Invalid("INVALID_TEXT")
            strings.append(value)
        elif isinstance(value, dict):
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    stack = [(obj, 1)]
    while stack:
        value, depth = stack.pop()
        if isinstance(value, (dict, list)):
            if depth > 4:
                raise _Invalid("DEPTH_EXCEEDED")
            children = value.values() if isinstance(value, dict) else value
            stack.extend((child, depth + 1) for child in children)
    if any(len(value) > 1024 for value in strings):
        raise _Invalid("INVALID_SHAPE")
    return obj


def _shape(obj, keys, path, optional=()):
    if not isinstance(obj, dict) or set(obj) - set(keys) or set(keys) - set(optional) - set(obj):
        raise _Invalid("INVALID_SHAPE", path)


def _u64(value, path):
    if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]{0,19}", value):
        raise _Invalid("INVALID_U64", path)
    number = int(value)
    if number > 18446744073709551615:
        raise _Invalid("INVALID_U64", path)
    return number


def _base58(raw):
    number, text = int.from_bytes(raw, "big"), ""
    while number:
        number, digit = divmod(number, 58)
        text = _ALPHABET[digit] + text
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + text


def _pubkey(value, path):
    if not isinstance(value, str) or not 32 <= len(value) <= 44:
        raise _Invalid("INVALID_PUBKEY", path)
    number = 0
    for character in value:
        if character not in _ALPHABET:
            raise _Invalid("INVALID_PUBKEY", path)
        number = number * 58 + _ALPHABET.index(character)
    raw = (b"\0" * (len(value) - len(value.lstrip("1"))) +
           number.to_bytes((number.bit_length() + 7) // 8, "big"))
    if len(raw) != 32 or _base58(raw) != value:
        raise _Invalid("INVALID_PUBKEY", path)
    return raw


def _route(value, path, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or value not in _ROUTES:
        raise _Invalid("INVALID_SHAPE", path)


def _finding(code, path):
    item = FINDING_CATALOG[code]
    return {"code": code, "path": path, "message": item["message"],
            "source_ids": list(item["source_ids"])}


def _external_findings(intent, protected, operation):
    findings = []
    positions = {"source": 3, "recipient": 5, "authority": 6}
    for role, index in positions.items():
        if intent[role] in protected:
            path = f"intent.{role}" if operation == "encode" else f"descriptor.accounts[{index}].pubkey"
            findings.append(_finding("PROTECTED_KEY", path))
    seen = set()
    for j, signer in enumerate(intent["signers"]):
        path = f"intent.signers[{j}]" if operation == "encode" else f"descriptor.accounts[{9+j}].pubkey"
        if signer in protected:
            findings.append(_finding("PROTECTED_KEY", path))
        if signer in seen:
            findings.append(_finding("DUPLICATE_SIGNER", path))
        if signer == intent["authority"]:
            findings.append(_finding("AUTHORITY_IN_SUFFIX", path))
        seen.add(signer)
    return findings


def _requirements(accounts, kind):
    union = {}
    for meta in accounts:
        writable, signer = union.get(meta["pubkey"], (False, False))
        union[meta["pubkey"]] = (writable or meta["is_writable"], signer or meta["is_signer"])
    result = []
    for index, meta in enumerate(accounts):
        required_writable = index in (1, 2, 3, 4, 5)
        required_signer = index >= 9 or (index == 6 and kind == 0)
        writable, signer = union[meta["pubkey"]]
        result.append({
            "index": str(index), "role": _ROLES[index] if index < 9 else f"signer[{index-9}]",
            "pubkey": meta["pubkey"], "required_is_writable": required_writable,
            "required_is_signer": required_signer, "effective_is_writable": writable,
            "effective_is_signer": signer,
            "privileges_satisfied": (not required_writable or writable) and (not required_signer or signer),
        })
    return result


def _encode(obj, keys):
    fields = ("source", "authority", "recipient", "amount_base_units", "minimum_lamports",
              "authorization_route", "signers")
    _shape(obj, fields, "intent")
    raw_keys = {role: _pubkey(obj[role], f"intent.{role}")
                for role in ("source", "authority", "recipient")}
    amount = _u64(obj["amount_base_units"], "intent.amount_base_units")
    minimum = _u64(obj["minimum_lamports"], "intent.minimum_lamports")
    _route(obj["authorization_route"], "intent.authorization_route")
    signers = obj["signers"]
    if not isinstance(signers, list) or len(signers) > 12:
        raise _Invalid("INVALID_SHAPE", "intent.signers")
    for j, signer in enumerate(signers):
        _pubkey(signer, f"intent.signers[{j}]")
    kind, n = int(obj["authorization_route"] == "native_multisig"), len(signers)
    intent = {**obj, "signers": list(signers), "authorization_kind": str(kind),
              "supplied_signer_count": str(n)}
    protected = {entry["base58"] for entry in keys.values()}
    findings = _external_findings(intent, protected, "encode")
    if amount == 0:
        findings.append(_finding("AMOUNT_ZERO", "intent.amount_base_units"))
    if kind == 0 and n:
        findings.append(_finding("ROUTE_SIGNERS_FORBIDDEN", "intent.signers"))
    if kind == 1 and n == 0:
        findings.append(_finding("SIGNERS_REQUIRED", "intent.signers"))
    if kind == 1 and n > 11:
        findings.append(_finding("SIGNERS_TOO_MANY", "intent.signers"))
    if findings:
        return None, intent, [], findings
    role_keys = [keys[_FIXED[i]]["base58"] if i in _FIXED else obj[_ROLES[i]] for i in range(9)]
    role_keys.extend(signers)
    accounts = [{"pubkey": key, "is_writable": i in (1, 2, 3, 4, 5),
                 "is_signer": i >= 9 or (i == 6 and kind == 0)} for i, key in enumerate(role_keys)]
    body = (_HEADER + amount.to_bytes(8, "little") + minimum.to_bytes(8, "little") +
            raw_keys["recipient"] + bytes((kind, n)))
    descriptor = {"program_id": keys["program"]["base58"], "accounts": accounts,
                  "data_hex": body.hex()}
    return descriptor, intent, _requirements(accounts, kind), findings


def _decode(obj, route, keys):
    _route(route, "route_claim", nullable=True)
    _shape(obj, ("program_id", "accounts", "data_hex"), "descriptor")
    _pubkey(obj["program_id"], "descriptor.program_id")
    accounts = obj["accounts"]
    if not isinstance(accounts, list) or len(accounts) > 21:
        raise _Invalid("INVALID_SHAPE", "descriptor.accounts")
    for i, meta in enumerate(accounts):
        path = f"descriptor.accounts[{i}]"
        _shape(meta, ("pubkey", "is_signer", "is_writable"), path)
        _pubkey(meta["pubkey"], path + ".pubkey")
        for flag in ("is_signer", "is_writable"):
            if type(meta[flag]) is not bool:
                raise _Invalid("INVALID_SHAPE", path + "." + flag)
    text = obj["data_hex"]
    if (not isinstance(text, str) or len(text) > 512 or len(text) % 2 or
            re.fullmatch(r"[0-9a-f]*", text) is None):
        raise _Invalid("INVALID_DATA_HEX", "descriptor.data_hex")
    body = bytes.fromhex(text)
    if len(body) != 56:
        raise _Invalid("INVALID_WIRE_LENGTH", "descriptor.data_hex")
    if body[:6] != _HEADER:
        raise _Invalid("INVALID_WIRE_HEADER", "descriptor.data_hex")
    kind, n = body[54], body[55]
    if kind not in (0, 1):
        raise _Invalid("INVALID_WIRE_KIND", "descriptor.data_hex")
    if n > 11 or (kind == 0 and n != 0):
        raise _Invalid("INVALID_WIRE_COUNT", "descriptor.data_hex")
    if len(accounts) != 9 + n:
        raise _Invalid("INVALID_ACCOUNT_COUNT", "descriptor.accounts")
    amount, minimum = int.from_bytes(body[6:14], "little"), int.from_bytes(body[14:22], "little")
    intent = {"source": accounts[3]["pubkey"], "authority": accounts[6]["pubkey"],
              "recipient": _base58(body[22:54]), "amount_base_units": str(amount),
              "minimum_lamports": str(minimum), "authorization_route": route,
              "authorization_kind": str(kind), "supplied_signer_count": str(n),
              "signers": [meta["pubkey"] for meta in accounts[9:]]}
    # Source protection applies to the actual account roles. The wire recipient
    # remains separately visible and may differ from the actual payee meta.
    external = {**intent, "recipient": accounts[5]["pubkey"]}
    findings = _external_findings(external, {entry["base58"] for entry in keys.values()}, "decode")
    if obj["program_id"] != keys["program"]["base58"]:
        findings.append(_finding("PROGRAM_ID_MISMATCH", "descriptor.program_id"))
    for i, name in _FIXED.items():
        if accounts[i]["pubkey"] != keys[name]["base58"]:
            findings.append(_finding("FIXED_KEY_MISMATCH", f"descriptor.accounts[{i}].pubkey"))
    if intent["recipient"] != accounts[5]["pubkey"]:
        findings.append(_finding("RECIPIENT_MISMATCH", "descriptor.accounts[5].pubkey"))
    requirements = _requirements(accounts, kind)
    for role in requirements:
        if not role["privileges_satisfied"]:
            findings.append(_finding("MISSING_PRIVILEGE", f"descriptor.accounts[{role['index']}]"))
    if amount == 0:
        findings.append(_finding("AMOUNT_ZERO", "descriptor.data_hex"))
    if kind == 1 and n == 0:
        findings.append(_finding("SIGNERS_REQUIRED", "descriptor.accounts"))
    if route is None:
        findings.append(_finding("ROUTE_UNRESOLVED", "route_claim"))
    elif int(route == "native_multisig") != kind:
        findings.append(_finding("ROUTE_KIND_MISMATCH", "route_claim"))
    return deepcopy(obj), intent, requirements, findings


def _process(obj, input_hash):
    if not isinstance(obj, dict) or set(obj) - {"schema", "operation", "profile", "intent", "descriptor", "route_claim"}:
        raise _Invalid("INVALID_SHAPE")
    if obj.get("schema") != "htfp-redeem-request-v1":
        raise _Invalid("INVALID_SCHEMA", "schema")
    operation = obj.get("operation")
    if operation not in ("encode", "decode"):
        raise _Invalid("INVALID_SHAPE", "operation")
    branch = ("intent",) if operation == "encode" else ("descriptor", "route_claim")
    _shape(obj, ("schema", "operation", "profile", *branch), "$", optional=("profile",))
    profile = obj.get("profile")
    if profile is None or profile == "UNCONFIGURED":
        raise _Invalid("PROFILE_UNCONFIGURED", "profile")
    if not isinstance(profile, str):
        raise _Invalid("INVALID_SHAPE", "profile")
    if profile != PROFILE_NAME:
        raise _Invalid("UNSUPPORTED_PROFILE", "profile")
    keys = _profile()
    if operation == "encode":
        descriptor, intent, requirements, findings = _encode(obj["intent"], keys)
    else:
        descriptor, intent, requirements, findings = _decode(obj["descriptor"], obj["route_claim"], keys)
    unique = {(finding["path"], finding["code"]): finding for finding in findings}
    findings = [unique[key] for key in sorted(unique)]
    status = ("NONCONFORMANT" if any(f["code"] != "ROUTE_UNRESOLVED" for f in findings)
              else "UNRESOLVED" if findings else "CONFORMANT")
    report = _base_report(input_hash)
    report.update(status=status, operation=operation, profile=PROFILE_NAME,
                  descriptor=descriptor, intent=intent, account_requirements=requirements, findings=findings)
    report["validation"] = {
        "body": "NOT_PRODUCED" if descriptor is None else "VALID_INITIAL_BODY",
        "descriptor": ("NOT_PRODUCED" if descriptor is None else
                       "NONCONFORMANT" if any(FINDING_CATALOG[f["code"]]["layer"] == "descriptor" for f in findings)
                       else "CONFORMANT"),
        "intent": status,
    }
    return report, 0 if status == "CONFORMANT" else 1


def process_bytes(raw):
    """Return (report, exit_code) for exact request bytes; no output or writes.

    The fixed packaged profile is authenticated afresh for each selected local
    request. A conformant result establishes no authorization or execution.
    """
    if not isinstance(raw, bytes):
        raise TypeError("process_bytes requires bytes")
    if len(raw) > _LIMIT:
        return _error(_Invalid("INPUT_TOO_LARGE"))
    input_hash = hashlib.sha256(raw).hexdigest()
    try:
        return _process(_parse(raw), input_hash)
    except _Invalid as exc:
        return _error(exc, input_hash)


def process_file(path):
    """Read one bounded regular request file and apply process_bytes."""
    try:
        raw = _read_regular(path, _LIMIT, "INPUT_UNREADABLE", "INPUT_TOO_LARGE")
    except _Invalid as exc:
        return _error(exc)
    return process_bytes(raw)


def format_report(report):
    """Canonical reviewed stdout representation; never an execution receipt."""
    data = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(data) > 32768:
        raise RuntimeError("Report exceeds the fixed output bound")
    return data


def main(argv):
    """One explicit request pathname, stdout only for contracted outcomes."""
    if len(argv) != 1 or argv[0].startswith("-"):
        return _error(_Invalid("CLI_USAGE"))
    return process_file(argv[0])
