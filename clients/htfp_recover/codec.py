"""Strict Recover instruction descriptor codec. No transaction or native calls."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from ._constants import (
    ASSURANCE, ERROR_MESSAGES, FINDINGS, FIXED_ROLES, PROFILE_BYTES,
    PROFILE_NAME, PROFILE_SHA256, SOURCE_BINDINGS,
)

_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_HEADER = b"HTFP\x01\x01"
_INPUT_LIMIT = 16384


class _Invalid(Exception):
    def __init__(self, code, path="$"):
        self.code, self.path = code, path
        super().__init__(code)


def _base_report(input_hash):
    return {
        "schema": "htfp-recover-report-v1", "status": "ERROR", "operation": None,
        "profile": "UNCONFIGURED", "input_sha256": input_hash,
        "profile_sha256": PROFILE_SHA256, "source_bindings": dict(SOURCE_BINDINGS),
        "error": None,
        "validation": {"body": "UNASSESSED", "descriptor": "UNASSESSED", "intent": "UNASSESSED"},
        "descriptor": None, "intent": None, "account_requirements": [], "findings": [],
        "assurance": deepcopy(ASSURANCE),
    }


def _error(exc, input_hash=None):
    report = _base_report(input_hash)
    report["error"] = {"code": exc.code, "path": exc.path, "message": ERROR_MESSAGES[exc.code]}
    return report, 2


def _regular_bytes(path, maximum, io_error, size_error):
    """Bound IO on the opened descriptor, including nonregular replacements."""
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise _Invalid(io_error)
        parts, left = [], maximum + 1
        while left:
            part = os.read(fd, left)
            if not part:
                break
            parts.append(part)
            left -= len(part)
        raw = b"".join(parts)
        if len(raw) > maximum:
            raise _Invalid(size_error)
        return raw
    except (OSError, ValueError, TypeError):
        raise _Invalid(io_error) from None
    finally:
        if fd is not None:
            os.close(fd)


def _profile_keys():
    raw = _regular_bytes(Path(__file__).with_name("PROFILE.json"), PROFILE_BYTES,
                         "SOURCE_BINDING_ERROR", "SOURCE_BINDING_ERROR")
    if len(raw) != PROFILE_BYTES or hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise _Invalid("SOURCE_BINDING_ERROR")
    # This exact artifact has been authenticated against compiled trust pins.
    return json.loads(raw)["public_keys"]


def _no_number(_):
    raise _Invalid("INVALID_JSON")


def _pairs(items):
    result = {}
    for key, value in items:
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
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_no_number,
                           parse_float=_no_number, parse_constant=_no_number)
    except (ValueError, TypeError):
        raise _Invalid("INVALID_JSON") from None
    except RecursionError:
        raise _Invalid("DEPTH_EXCEEDED") from None
    strings, pending = [], [value]
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
    if any(len(text) > 1024 for text in strings):
        raise _Invalid("INVALID_SHAPE")
    return value


def _object(value, fields, path, optional=()):
    if (not isinstance(value, dict) or set(value) - set(fields) or
            set(fields) - set(optional) - set(value)):
        raise _Invalid("INVALID_SHAPE", path)


def _base58(raw):
    number, text = int.from_bytes(raw, "big"), ""
    while number:
        number, index = divmod(number, 58)
        text = _BASE58[index] + text
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + text


def _pubkey(value, path):
    if not isinstance(value, str) or not 32 <= len(value) <= 44:
        raise _Invalid("INVALID_PUBKEY", path)
    number = 0
    for ch in value:
        if ch not in _BASE58:
            raise _Invalid("INVALID_PUBKEY", path)
        number = number * 58 + _BASE58.index(ch)
    raw = (b"\0" * (len(value) - len(value.lstrip("1"))) +
           number.to_bytes((number.bit_length() + 7) // 8, "big"))
    if len(raw) != 32 or _base58(raw) != value:
        raise _Invalid("INVALID_PUBKEY", path)


def _finding(code, path):
    item = FINDINGS[code]
    return {"code": code, "path": path, "message": item["message"],
            "source_ids": list(item["source_ids"])}


def _source_findings(sources, protected, encode):
    findings, seen = [], set()
    for j, key in enumerate(sources):
        path = f"intent.sources[{j}]" if encode else f"descriptor.accounts[{6+j}].pubkey"
        if key in protected:
            findings.append(_finding("PROTECTED_SOURCE", path))
        if key in seen:
            findings.append(_finding("DUPLICATE_SOURCE", path))
        seen.add(key)
    return findings


def _requirements(accounts):
    effective = {}
    for meta in accounts:
        writable, signer = effective.get(meta["pubkey"], (False, False))
        effective[meta["pubkey"]] = (writable or meta["is_writable"], signer or meta["is_signer"])
    result = []
    for i, meta in enumerate(accounts):
        needs_write = i in (1, 2, 3) or i >= 6
        writable, signer = effective[meta["pubkey"]]
        result.append({
            "index": str(i), "role": FIXED_ROLES[i] if i < 6 else f"source[{i-6}]",
            "pubkey": meta["pubkey"], "required_is_writable": needs_write,
            "required_is_signer": False, "effective_is_writable": writable,
            "effective_is_signer": signer, "privileges_satisfied": not needs_write or writable,
        })
    return result


def _encode(intent, keys):
    _object(intent, ("sources",), "intent")
    sources = intent["sources"]
    if not isinstance(sources, list) or len(sources) > 33:
        raise _Invalid("INVALID_SHAPE", "intent.sources")
    for j, key in enumerate(sources):
        _pubkey(key, f"intent.sources[{j}]")
    count = len(sources)
    normalized = {"sources": list(sources), "source_count": str(count)}
    findings = _source_findings(sources, {v["base58"] for v in keys.values()}, True)
    if count > 32:
        findings.append(_finding("SOURCES_TOO_MANY", "intent.sources"))
    if findings:
        return None, normalized, [], findings
    accounts = [{"pubkey": keys[role]["base58"], "is_signer": False, "is_writable": i in (1, 2, 3)}
                for i, role in enumerate(FIXED_ROLES)]
    accounts.extend({"pubkey": key, "is_signer": False, "is_writable": True} for key in sources)
    descriptor = {"program_id": keys["program"]["base58"], "accounts": accounts,
                  "data_hex": (_HEADER + count.to_bytes(2, "little")).hex()}
    return descriptor, normalized, _requirements(accounts), findings


def _decode(descriptor, keys):
    _object(descriptor, ("program_id", "accounts", "data_hex"), "descriptor")
    _pubkey(descriptor["program_id"], "descriptor.program_id")
    accounts = descriptor["accounts"]
    if not isinstance(accounts, list) or len(accounts) > 39:
        raise _Invalid("INVALID_SHAPE", "descriptor.accounts")
    for i, meta in enumerate(accounts):
        path = f"descriptor.accounts[{i}]"
        _object(meta, ("pubkey", "is_signer", "is_writable"), path)
        _pubkey(meta["pubkey"], path + ".pubkey")
        for flag in ("is_signer", "is_writable"):
            if type(meta[flag]) is not bool:
                raise _Invalid("INVALID_SHAPE", path + "." + flag)
    text = descriptor["data_hex"]
    if (not isinstance(text, str) or len(text) > 512 or len(text) % 2 or
            re.fullmatch(r"[0-9a-f]*", text) is None):
        raise _Invalid("INVALID_DATA_HEX", "descriptor.data_hex")
    body = bytes.fromhex(text)
    if len(body) != 8:
        raise _Invalid("INVALID_WIRE_LENGTH", "descriptor.data_hex")
    if body[:6] != _HEADER:
        raise _Invalid("INVALID_WIRE_HEADER", "descriptor.data_hex")
    count = int.from_bytes(body[6:8], "little")
    if count > 32:
        raise _Invalid("INVALID_WIRE_COUNT", "descriptor.data_hex")
    if len(accounts) != 6 + count:
        raise _Invalid("INVALID_ACCOUNT_COUNT", "descriptor.accounts")
    sources = [meta["pubkey"] for meta in accounts[6:]]
    normalized = {"sources": sources, "source_count": str(count)}
    # Protection uses only the canonical trusted nine keys, never wrong fixed
    # accounts supplied by a caller. Actual duplicate classes remain separate.
    findings = _source_findings(sources, {v["base58"] for v in keys.values()}, False)
    if descriptor["program_id"] != keys["program"]["base58"]:
        findings.append(_finding("PROGRAM_ID_MISMATCH", "descriptor.program_id"))
    seen = set()
    for i, role in enumerate(FIXED_ROLES):
        key = accounts[i]["pubkey"]
        if key != keys[role]["base58"]:
            findings.append(_finding("FIXED_KEY_MISMATCH", f"descriptor.accounts[{i}].pubkey"))
        if key in seen:
            findings.append(_finding("DUPLICATE_FIXED", f"descriptor.accounts[{i}].pubkey"))
        seen.add(key)
    requirements = _requirements(accounts)
    for role in requirements:
        if not role["privileges_satisfied"]:
            findings.append(_finding("MISSING_PRIVILEGE", f"descriptor.accounts[{role['index']}]"))
    return deepcopy(descriptor), normalized, requirements, findings


def _process(value, input_hash):
    if not isinstance(value, dict) or set(value) - {"schema", "operation", "profile", "intent", "descriptor"}:
        raise _Invalid("INVALID_SHAPE")
    if value.get("schema") != "htfp-recover-request-v1":
        raise _Invalid("INVALID_SCHEMA", "schema")
    operation = value.get("operation")
    if operation not in ("encode", "decode"):
        raise _Invalid("INVALID_SHAPE", "operation")
    payload = "intent" if operation == "encode" else "descriptor"
    _object(value, ("schema", "operation", "profile", payload), "$", optional=("profile",))
    profile = value.get("profile")
    if profile is None or profile == "UNCONFIGURED":
        raise _Invalid("PROFILE_UNCONFIGURED", "profile")
    if not isinstance(profile, str):
        raise _Invalid("INVALID_SHAPE", "profile")
    if profile != PROFILE_NAME:
        raise _Invalid("UNSUPPORTED_PROFILE", "profile")
    keys = _profile_keys()
    descriptor, intent, requirements, findings = (_encode(value[payload], keys) if operation == "encode"
                                                 else _decode(value[payload], keys))
    unique = {(item["path"], item["code"]): item for item in findings}
    findings = [unique[key] for key in sorted(unique)]
    status = "NONCONFORMANT" if findings else "CONFORMANT"
    report = _base_report(input_hash)
    report.update(status=status, operation=operation, profile=PROFILE_NAME, descriptor=descriptor,
                  intent=intent, account_requirements=requirements, findings=findings)
    report["validation"] = {
        "body": "NOT_PRODUCED" if descriptor is None else "VALID_LOCAL_BODY",
        "descriptor": "NOT_PRODUCED" if descriptor is None else status,
        "intent": status,
    }
    return report, 1 if findings else 0


def process_bytes(raw):
    """Return (report,exit_code) for exact request bytes, no writes or network.

    The fixed profile is authenticated afresh for every selected local request.
    Conformance proves no native eligibility, receipt, R change or packet fit.
    """
    if not isinstance(raw, bytes):
        raise TypeError("process_bytes requires bytes")
    if len(raw) > _INPUT_LIMIT:
        return _error(_Invalid("INPUT_TOO_LARGE"))
    digest = hashlib.sha256(raw).hexdigest()
    try:
        return _process(_parse(raw), digest)
    except _Invalid as exc:
        return _error(exc, digest)


def process_file(path):
    """Read one explicit bounded regular local request and apply the codec."""
    try:
        raw = _regular_bytes(path, _INPUT_LIMIT, "INPUT_UNREADABLE", "INPUT_TOO_LARGE")
    except _Invalid as exc:
        return _error(exc)
    return process_bytes(raw)


def format_report(report):
    """Serialize an unmodified codec-produced report; not a report validator."""
    raw = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > 65536:
        raise RuntimeError("Report exceeds the fixed output bound")
    return raw


def main(argv):
    if len(argv) != 1 or argv[0].startswith("-"):
        return _error(_Invalid("CLI_USAGE"))
    return process_file(argv[0])
