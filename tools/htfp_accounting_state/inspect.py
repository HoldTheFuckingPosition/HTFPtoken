"""Strict supplied-record accounting inspection; no native or network access."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from ._constants import (
    ASSURANCE, ERROR_MESSAGES, FACT_KEYS, FINDINGS, LENGTHS, PROFILE_BYTES,
    PROFILE_NAME, PROFILE_SHA256, ROLES, SOURCE_BINDINGS,
)

_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_INPUT_LIMIT = 16384


class _Invalid(Exception):
    def __init__(self, code, path="$"):
        self.code, self.path = code, path
        super().__init__(code)


def _base_report(input_hash):
    return {
        "schema": "htfp-accounting-state-report-v1", "status": "ERROR",
        "profile": "UNCONFIGURED", "input_sha256": input_hash,
        "profile_sha256": PROFILE_SHA256, "source_bindings": dict(SOURCE_BINDINGS),
        "error": None, "accounts": None,
        "facts": {key: None for key in FACT_KEYS},
        "accounting": {"assessment": "UNASSESSED", "unbooked_spendable_base_units": None,
                       "unbooked_origin": "UNKNOWN"},
        "findings": [], "assurance": deepcopy(ASSURANCE),
    }


def _error(exc, input_hash=None):
    report = _base_report(input_hash)
    report["error"] = {"code": exc.code, "path": exc.path, "message": ERROR_MESSAGES[exc.code]}
    return report, 2


def _read_regular(path, maximum, unreadable, oversized):
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise _Invalid(unreadable)
        parts, remaining = [], maximum + 1
        while remaining:
            part = os.read(fd, remaining)
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        raw = b"".join(parts)
        if len(raw) > maximum:
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
    return json.loads(raw)


def _number(_):
    raise _Invalid("INVALID_JSON")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Invalid("INVALID_JSON")
        result[key] = value
    return result


def _parse(raw):
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _Invalid("INVALID_UTF8") from None
    if text.startswith("\ufeff"):
        raise _Invalid("INVALID_UTF8")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_number,
                           parse_float=_number, parse_constant=_number)
    except RecursionError:
        raise _Invalid("DEPTH_EXCEEDED") from None
    except (ValueError, TypeError):
        raise _Invalid("INVALID_JSON") from None
    pending, strings = [value], []
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            if any(0xD800 <= ord(ch) <= 0xDFFF for ch in item):
                raise _Invalid("INVALID_TEXT")
            strings.append(item)
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if isinstance(item, (dict, list)):
            if depth > 4:
                raise _Invalid("DEPTH_EXCEEDED")
            children = item.values() if isinstance(item, dict) else item
            pending.extend((child, depth + 1) for child in children)
    if any(len(string) > 1024 for string in strings):
        raise _Invalid("INVALID_SHAPE")
    return value


def _shape(value, fields, path):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise _Invalid("INVALID_SHAPE", path)


def _encode58(raw):
    number, text = int.from_bytes(raw, "big"), ""
    while number:
        number, remainder = divmod(number, 58)
        text = _BASE58[remainder] + text
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + text


def _pubkey(value, path):
    if not isinstance(value, str) or not 32 <= len(value) <= 44:
        raise _Invalid("INVALID_PUBKEY", path)
    number = 0
    for char in value:
        if char not in _BASE58:
            raise _Invalid("INVALID_PUBKEY", path)
        number = number * 58 + _BASE58.index(char)
    raw = (b"\0" * (len(value) - len(value.lstrip("1"))) +
           number.to_bytes((number.bit_length() + 7) // 8, "big"))
    if len(raw) != 32 or _encode58(raw) != value:
        raise _Invalid("INVALID_PUBKEY", path)


def _accounts(value):
    _shape(value, ROLES, "accounts")
    parsed = {}
    for role in ROLES:
        account, path = value[role], "accounts." + role
        _shape(account, ("address", "owner", "executable", "data_hex"), path)
        _pubkey(account["address"], path + ".address")
        _pubkey(account["owner"], path + ".owner")
        if type(account["executable"]) is not bool:
            raise _Invalid("INVALID_SHAPE", path + ".executable")
        text = account["data_hex"]
        if (not isinstance(text, str) or len(text) > 1024 or len(text) % 2 or
                re.fullmatch(r"[0-9a-f]*", text) is None):
            raise _Invalid("INVALID_DATA_HEX", path + ".data_hex")
        parsed[role] = bytes.fromhex(text)
    return parsed


def _finding(code, path):
    item = FINDINGS[code]
    return {"code": code, "path": path, "message": item["message"],
            "source_ids": list(item["source_ids"])}


def _inspect_role(role, account, data, profile, facts):
    keys = profile["public_keys"]
    key = lambda name: bytes.fromhex(keys[name]["hex"])
    findings, path = [], "accounts." + role

    def require(condition, code, field="data_hex"):
        if not condition:
            findings.append(_finding(code, path + "." + field))
        return condition

    def absent(offset, invalid, present):
        tag = int.from_bytes(data[offset:offset + 4], "little")
        # Inactive payload is deliberately ignored for native None tags.
        if tag not in (0, 1):
            require(False, invalid)
        elif tag == 1:
            require(False, present)

    require(account["address"] == keys[role]["base58"], "ADDRESS_MISMATCH", "address")
    owner = keys["program" if role in ("config", "inventory") else "token2022"]["base58"]
    require(account["owner"] == owner, "OWNER_MISMATCH", "owner")
    require(not account["executable"], "EXECUTABLE_ACCOUNT", "executable")
    exact_length = require(len(data) == LENGTHS[role], "DATA_LENGTH_MISMATCH")
    if exact_length and role == "config":
        for begin, end, expected, code in (
            (0, 8, b"HTFPCFG1", "CONFIG_HEADER_MISMATCH"),
            (8, 10, b"\x01\0", "CONFIG_VERSION_MISMATCH"),
            (10, 11, b"\x01", "CONFIG_INITIALIZED_REQUIRED"),
            (11, 15, b"\xfe\xff\xff\xff", "CONFIG_BUMPS_MISMATCH"),
            (15, 47, key("mint"), "CONFIG_MINT_MISMATCH"),
            (47, 79, key("token2022"), "CONFIG_TOKEN2022_MISMATCH"),
            (79, 111, key("reserve"), "CONFIG_RESERVE_MISMATCH"),
            (111, 143, key("program"), "CONFIG_DERIVER_MISMATCH"),
            (143, 175, bytes.fromhex(profile["genesis_commitment_hex"]), "CONFIG_COMMITMENT_MISMATCH"),
        ):
            require(data[begin:end] == expected, code)
    elif exact_length and role == "inventory":
        header = require(data[:8] == b"HTFPINV1", "INVENTORY_HEADER_MISMATCH")
        version = require(data[8:10] == b"\x01\0", "INVENTORY_VERSION_MISMATCH")
        require(data[10] == 255, "INVENTORY_BUMP_MISMATCH")
        require(data[11] in (0, 1), "INVENTORY_GUARD_UNSUPPORTED")
        facts["inventory_guard"] = str(data[11])
        if header and version:
            facts["booked_inventory_base_units"] = str(int.from_bytes(data[12:20], "little"))
    elif exact_length and role == "mint":
        padding = require(data[82:165] == bytes(83), "MINT_PADDING_MISMATCH")
        account_type = require(data[165] == 1, "MINT_ACCOUNT_TYPE_MISMATCH")
        extension = require(data[166:170] == b"\x01\0\x6c\0", "MINT_TLV_MISMATCH")
        require(data[44] == 7, "MINT_DECIMALS_MISMATCH")
        require(data[45] == 1, "MINT_INITIALIZED_REQUIRED")
        supply = int.from_bytes(data[36:44], "little")
        require(supply <= 10**19, "MINT_SUPPLY_EXCEEDS_CAP")
        absent(0, "MINT_MINT_AUTHORITY_OPTION_INVALID", "MINT_MINT_AUTHORITY_PRESENT")
        absent(46, "MINT_FREEZE_AUTHORITY_OPTION_INVALID", "MINT_FREEZE_AUTHORITY_PRESENT")
        if extension:
            require(data[170:202] == bytes(32), "MINT_FEE_AUTHORITY_PRESENT")
            require(data[202:234] == key("tax_authority"), "MINT_WITHDRAW_AUTHORITY_MISMATCH")
            for start, epoch, bps, code in ((242, 7, 0, "MINT_OLDER_SCHEDULE_MISMATCH"),
                                            (260, 9, 800, "MINT_NEWER_SCHEDULE_MISMATCH")):
                expected = epoch.to_bytes(8, "little") + (2**64 - 1).to_bytes(8, "little") + bps.to_bytes(2, "little")
                require(data[start:start + 18] == expected, code)
        if padding and account_type and extension:
            facts["supply_base_units"] = str(supply)
            facts["mint_withheld_base_units"] = str(int.from_bytes(data[234:242], "little"))
    elif exact_length and role == "custody":
        account_type = require(data[165] == 2, "CUSTODY_ACCOUNT_TYPE_MISMATCH")
        extension = require(data[166:170] == b"\x02\0\x08\0", "CUSTODY_TLV_MISMATCH")
        require(data[:32] == key("mint"), "CUSTODY_MINT_MISMATCH")
        require(data[32:64] == key("tax_authority"), "CUSTODY_TOKEN_OWNER_MISMATCH")
        require(data[108] == 1, "CUSTODY_STATE_MISMATCH")
        require(int.from_bytes(data[121:129], "little") == 0, "CUSTODY_ALLOWANCE_NONZERO")
        absent(72, "CUSTODY_DELEGATE_OPTION_INVALID", "CUSTODY_DELEGATE_PRESENT")
        absent(129, "CUSTODY_CLOSE_OPTION_INVALID", "CUSTODY_CLOSE_AUTHORITY_PRESENT")
        native = int.from_bytes(data[109:113], "little")
        if native not in (0, 1):
            require(False, "CUSTODY_NATIVE_OPTION_INVALID")
        elif native == 1:
            require(False, "CUSTODY_NATIVE_UNSUPPORTED")
        # native==0 ignores all eight inactive bytes113:121.
        if account_type and extension:
            facts["custody_spendable_base_units"] = str(int.from_bytes(data[64:72], "little"))
            facts["custody_withheld_base_units"] = str(int.from_bytes(data[170:178], "little"))
    assessed = {
        "address": account["address"], "declared_owner": account["owner"],
        "declared_executable": account["executable"], "data_bytes": str(len(data)),
        "data_sha256": hashlib.sha256(data).hexdigest(),
        "profile_conformance": "NONCONFORMANT" if findings else "CONFORMANT",
    }
    return assessed, findings


def _process(value, input_hash):
    if not isinstance(value, dict) or set(value) - {"schema", "profile", "accounts"}:
        raise _Invalid("INVALID_SHAPE")
    if value.get("schema") != "htfp-accounting-state-request-v1":
        raise _Invalid("INVALID_SCHEMA", "schema")
    if "accounts" not in value:
        raise _Invalid("INVALID_SHAPE")
    selected = value.get("profile")
    if selected is None or selected == "UNCONFIGURED":
        raise _Invalid("PROFILE_UNCONFIGURED", "profile")
    if not isinstance(selected, str):
        raise _Invalid("INVALID_SHAPE", "profile")
    if selected != PROFILE_NAME:
        raise _Invalid("UNSUPPORTED_PROFILE", "profile")
    profile = _profile()
    parsed = _accounts(value["accounts"])
    report = _base_report(input_hash)
    report.update(profile=PROFILE_NAME, accounts={})
    for role in ROLES:
        assessment, findings = _inspect_role(role, value["accounts"][role], parsed[role], profile, report["facts"])
        report["accounts"][role] = assessment
        report["findings"].extend(findings)
    if not report["findings"]:
        booked = int(report["facts"]["booked_inventory_base_units"])
        spendable = int(report["facts"]["custody_spendable_base_units"])
        if booked <= spendable:
            report["accounting"].update(assessment="COVERED", unbooked_spendable_base_units=str(spendable - booked))
        else:
            report["accounting"]["assessment"] = "UNDERCOVERED"
            report["findings"].append(_finding("INVENTORY_UNDERCOVERED", "accounting"))
    unique = {(item["path"], item["code"]): item for item in report["findings"]}
    report["findings"] = [unique[key] for key in sorted(unique)]
    report["status"] = "NONCONFORMANT" if report["findings"] else "CONFORMANT"
    return report, 1 if report["findings"] else 0


def process_bytes(raw):
    """Inspect exact request bytes, returning a fresh (report,exit_code)."""
    if type(raw) is not bytes:
        raise TypeError("process_bytes requires bytes")
    if len(raw) > _INPUT_LIMIT:
        return _error(_Invalid("INPUT_TOO_LARGE"))
    digest = hashlib.sha256(raw).hexdigest()
    try:
        return _process(_parse(raw), digest)
    except _Invalid as exc:
        return _error(exc, digest)


def process_file(path):
    """Read a single bounded regular local request, never a selected RPC."""
    try:
        raw = _read_regular(path, _INPUT_LIMIT, "INPUT_UNREADABLE", "INPUT_TOO_LARGE")
    except _Invalid as exc:
        return _error(exc)
    return process_bytes(raw)


def format_report(report):
    """Serialize an unmodified returned report; not an arbitrary validator."""
    raw = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > 65536:
        raise RuntimeError("Report exceeds the fixed output bound")
    return raw


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        return _error(_Invalid("CLI_USAGE"))
    return process_file(argv[0])
