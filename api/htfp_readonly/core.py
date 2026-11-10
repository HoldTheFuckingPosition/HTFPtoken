"""Strict fixed-snapshot decoding and exact arithmetic, without network access."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct

from . import trusted as t

U64_MAX = (1 << 64) - 1
U128_MAX = (1 << 128) - 1
SUPPLY_CAP = 10**19
SNAPSHOT_PATH = Path(__file__).parent / "data" / "snapshot.json"


def read_snapshot_bytes():
    # One extra byte detects an oversized replacement without reading it all.
    with SNAPSHOT_PATH.open("rb") as stream:
        return stream.read(5494)


ERRORS = {
    "NOT_FOUND": (404, "Unknown endpoint."),
    "REQUEST_TOO_LARGE": (414, "Request target or query exceeds the application limit."),
    "INVALID_REQUEST": (400, "Unsupported request target or body."),
    "INVALID_QUERY": (400, "Query must contain exactly the required canonical decimal parameters."),
    "INTEGER_OUT_OF_RANGE": (400, "Amount and minimum must fit unsigned64-bit integers."),
    "PROFILE_UNCONFIGURED": (503, "Production profile is not configured; no snapshot data is selected."),
    "SNAPSHOT_INVALID": (503, "The fixed historical snapshot is missing or fails validation."),
    "ZERO_SUPPLY": (422, "Redemption arithmetic is unavailable at zero supply."),
    "INVALID_AMOUNT": (422, "Redemption amount must be positive."),
    "AMOUNT_EXCEEDS_SUPPLY": (422, "Redemption amount exceeds snapshot supply."),
    "ZERO_PAYOUT": (422, "Snapshot arithmetic gives zero lamports."),
    "MINIMUM_NOT_MET": (422, "Snapshot payout is below the requested minimum."),
}


class APIError(Exception):
    def __init__(self, code):
        self.code = code
        self.status, self.message = ERRORS[code]
        super().__init__(self.message)


def require(condition):
    if not condition:
        raise ValueError("Unsupported or inconsistent fixed snapshot")


def u64(value):
    if type(value) is not int or not 0 <= value <= U64_MAX:
        raise APIError("INTEGER_OUT_OF_RANGE")
    return value


def canonical_integer(value):
    if not isinstance(value, str) or not re.fullmatch(r"0|[1-9][0-9]*", value, re.ASCII):
        raise APIError("INVALID_QUERY")
    if len(value) > 20:
        raise APIError("INTEGER_OUT_OF_RANGE")
    return u64(int(value))


def parse_target(target):
    """Application URL grammar only; HTTP framing belongs to the stdlib."""
    if len(target) > 1024:
        raise APIError("REQUEST_TOO_LARGE")
    if (not target.isascii() or not target.startswith("/") or target.startswith("//")
            or any(c in target for c in "%+#\\") or any(ord(c) <= 32 or ord(c) == 127 for c in target)):
        raise APIError("INVALID_REQUEST")
    path, mark, query = target.partition("?")
    if len(query) > 128:
        raise APIError("REQUEST_TOO_LARGE")
    if path not in ("/health", "/v1/status", "/v1/redemption-preview"):
        raise APIError("NOT_FOUND")
    if path != "/v1/redemption-preview":
        if mark:
            raise APIError("INVALID_QUERY")
        return path, None
    values = {}
    for pair in query.split("&"):
        key, sep, value = pair.partition("=")
        if not sep or key not in ("amount_base_units", "minimum_lamports") or key in values:
            raise APIError("INVALID_QUERY")
        values[key] = canonical_integer(value)
    if set(values) != {"amount_base_units", "minimum_lamports"}:
        raise APIError("INVALID_QUERY")
    return path, (values["amount_base_units"], values["minimum_lamports"])


def coption_pubkey(data):
    require(len(data) == 36)
    tag = int.from_bytes(data[:4], "little")
    require(tag in (0, 1))
    # Native COption None ignores the inactive payload, including nonzero bytes.
    return data[4:] if tag else None


def decode_mint(data):
    require(len(data) == 278)
    require(coption_pubkey(data[:36]) is None)
    require(coption_pubkey(data[46:82]) is None)
    supply = int.from_bytes(data[36:44], "little")
    require(supply <= SUPPLY_CAP and data[44:46] == bytes((7, 1)))
    require(data[82:165] == bytes(83) and data[165] == 1)
    # Fixed profile permits exactly one TransferFeeConfig TLV, no tail or duplicates.
    require(struct.unpack_from("<HH", data, 166) == (1, 108))
    require(data[170:202] == bytes(32))
    require(data[202:234].hex() == t.TUPLE["tax_authority"]["hex"])
    require(int.from_bytes(data[234:242], "little") == 0)
    require(struct.unpack_from("<QQH", data, 242) == (7, U64_MAX, 0))
    require(struct.unpack_from("<QQH", data, 260) == (9, U64_MAX, 800))
    return supply


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def strict_json(raw):
    def invalid_constant(_):
        raise ValueError("Nonfinite JSON constant")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=invalid_constant)


@dataclass(frozen=True)
class Snapshot:
    supply: int
    reserve: int
    maintenance: int
    booked_inventory: int
    guard: int

    def state(self):
        return {
            "program_id": t.TUPLE["program"]["base58"],
            "mint": t.TUPLE["mint"]["base58"],
            "reserve": t.TUPLE["reserve"]["base58"],
            "config": t.TUPLE["config"]["base58"],
            "inventory": t.TUPLE["inventory"]["base58"],
            "token2022_program": t.TUPLE["token2022"]["base58"],
            "genesis_commitment": t.GENESIS,
            "decimals": "7", "supply_base_units": str(self.supply),
            "reserve_lamports": str(self.reserve), "maintenance_lamports": str(self.maintenance),
            "backing_lamports": str(max(0, self.reserve - self.maintenance)),
            "booked_inventory_base_units": str(self.booked_inventory),
            "inventory_guard": str(self.guard),
        }


def decode_envelope(obj):
    """Semantic validation seam; serving also requires the immutable byte digest."""
    require(type(obj) is dict and set(obj) == {
        "accounts", "current_network_data", "evidence_class", "profile", "provenance",
        "public_cluster", "runtime_getters", "schema", "snapshot_id"})
    require(obj["schema"] == "htfp-m6a-local-snapshot-v1" and obj["snapshot_id"] == t.SNAPSHOT_ID)
    require(obj["profile"] == t.PROFILE and obj["evidence_class"] == "SYNTHETIC_LOCAL_HISTORICAL")
    require(obj["public_cluster"] is None and obj["current_network_data"] is False)
    require(obj["provenance"] == t.SOURCE_PROVENANCE)
    require(type(obj["accounts"]) is dict and set(obj["accounts"]) == set(t.ACCOUNTS))
    decoded = {}
    for name, expected in t.ACCOUNTS.items():
        account = obj["accounts"][name]
        require(type(account) is dict and set(account) == {
            "address", "bytes", "data_hex", "data_sha256", "executable", "lamports", "owner"})
        require(account["address"] == expected["address"] and account["owner"] == expected["owner"])
        require(account["executable"] is False)
        require(type(account["bytes"]) is int and account["bytes"] == int(expected["bytes"]))
        require(type(account["lamports"]) is int and u64(account["lamports"]) == int(expected["lamports"]))
        hexdata = account["data_hex"]
        require(type(hexdata) is str and re.fullmatch(r"[0-9a-f]*", hexdata) is not None)
        data = bytes.fromhex(hexdata)
        require(len(data) == account["bytes"])
        require(hashlib.sha256(data).hexdigest() == account["data_sha256"] == expected["data_sha256"])
        decoded[name] = data
    config = decoded["config"]
    require(config[:15] == b"HTFPCFG1\x01\x00\x01\xfe\xff\xff\xff")
    for start, name in ((15, "mint"), (47, "token2022"), (79, "reserve"), (111, "program")):
        require(config[start:start + 32].hex() == t.TUPLE[name]["hex"])
    require(config[143:].hex() == t.GENESIS)
    inv = decoded["inventory"]
    require(inv[:12] == b"HTFPINV1\x01\x00\xff\x00")
    booked = int.from_bytes(inv[12:], "little")
    supply = decode_mint(decoded["mint"])
    require(supply == 9999999994000000000 and booked == 0 and decoded["reserve"] == b"")
    rent = decoded["runtime_rent"]
    require(rent.hex() == "980d000000000000000000000000004032")
    maintenance = 128 * int.from_bytes(rent[:8], "little") * 2
    getters = obj["runtime_getters"]
    require(type(getters) is dict and set(getters) == {"clock", "rent"})
    expected_rent = {
        "burn_percent": 50, "exemption_threshold": 2.0, "lamports_per_byte_year": 3480,
        "minimum_balances": {"0": 890880, "165": 2039280, "175": 2108880,
                             "178": 2129760, "278": 2825760, "82": 1461600, "89": 1510320}}
    require(getters["rent"] == expected_rent and type(getters["rent"]["exemption_threshold"]) is float)
    for key in ("burn_percent", "lamports_per_byte_year"):
        require(type(getters["rent"][key]) is int)
    require(all(type(v) is int for v in getters["rent"]["minimum_balances"].values()))
    require(maintenance == getters["rent"]["minimum_balances"]["0"] == 890880)
    clock = struct.unpack("<QqQQq", decoded["runtime_clock"])
    keys = ("slot", "epoch_start_timestamp", "epoch", "leader_schedule_epoch", "unix_timestamp")
    require(type(getters["clock"]) is dict and set(getters["clock"]) == set(keys))
    require(all(type(getters["clock"][key]) is int for key in keys))
    require(dict(zip(keys, clock)) == getters["clock"])
    require(clock == (16352, 0, 9, 9, 1700000000))
    return Snapshot(supply, obj["accounts"]["reserve"]["lamports"], maintenance, booked, inv[11])


def decode_snapshot(raw):
    require(type(raw) is bytes and len(raw) == 5493 and hashlib.sha256(raw).hexdigest() == t.SNAPSHOT_SHA256)
    return decode_envelope(strict_json(raw))


def preview(supply, reserve, maintenance, amount, minimum):
    """Pure u64 arithmetic; generic unit tuples are not trusted H snapshots."""
    for value in (supply, reserve, maintenance, amount, minimum):
        u64(value)
    if supply == 0:
        raise APIError("ZERO_SUPPLY")
    if amount == 0:
        raise APIError("INVALID_AMOUNT")
    if amount > supply:
        raise APIError("AMOUNT_EXCEEDS_SUPPLY")
    backing = max(0, reserve - maintenance)
    product = backing * amount
    require(product <= U128_MAX)
    payout, remainder = divmod(product, supply)
    u64(payout)
    if payout == 0:
        raise APIError("ZERO_PAYOUT")
    if payout < minimum:
        raise APIError("MINIMUM_NOT_MET")
    return dict(zip(("amount_base_units", "minimum_lamports", "supply_base_units",
                     "reserve_lamports", "maintenance_lamports", "backing_lamports",
                     "payout_lamports", "division_remainder"),
                    map(str, (amount, minimum, supply, reserve, maintenance, backing, payout, remainder))))


def provenance():
    p = t.SOURCE_PROVENANCE
    return {
        "evidence_class": "SYNTHETIC_LOCAL_HISTORICAL", "profile": t.PROFILE,
        "public_cluster": None, "current_network_data": False,
        "source_trace_path": p["trace_path"], "source_stored_sha256": p["stored_sha256"],
        "source_decoded_sha256": p["decoded_sha256"], "event_index": "24", "boundary": "after",
        "transaction_sha256": p["transaction_sha256"], "transaction_status": "SUCCESS",
        "H_artifact_sha256": p["H_artifact_sha256"], "synthetic_slot": "16352",
        "synthetic_epoch": "9", "synthetic_unix_timestamp": "1700000000",
    }


class Application:
    def __init__(self, profile="unconfigured"):
        if profile not in ("unconfigured", "local-historical"):
            raise ValueError("Unsupported operator profile")
        self.local = profile == "local-historical"
        self.snapshot = None
        if self.local:
            self._verified()  # Invalid evidence starts unready, never serves an alternate.

    def _verified(self):
        if not self.local:
            return None
        try:
            raw = read_snapshot_bytes()
            require(len(raw) == 5493 and hashlib.sha256(raw).hexdigest() == t.SNAPSHOT_SHA256)
            if self.snapshot is None:
                self.snapshot = decode_snapshot(raw)
            return self.snapshot
        except (OSError, ValueError, KeyError, TypeError, APIError, struct.error):
            return None

    def handle(self, target, body_supported=True):
        # Verify even on invalid local requests, but preserve request validation precedence.
        snap = self._verified()
        body = {"api_version": "HTFP_READONLY_V1",
                "mode": "SYNTHETIC_LOCAL_HISTORICAL" if self.local else "UNCONFIGURED",
                "snapshot_id": t.SNAPSHOT_ID if snap else None,
                "snapshot_sha256": t.SNAPSHOT_SHA256 if snap else None, "error": None}
        try:
            if not body_supported:
                raise APIError("INVALID_REQUEST")
            route, args = parse_target(target)
            if route == "/health":
                body.update(process_alive=True, ready=snap is not None,
                            profile_state=("VERIFIED" if snap else "INVALID") if self.local else "UNCONFIGURED")
            elif route == "/v1/status":
                if self.local and snap is None:
                    raise APIError("SNAPSHOT_INVALID")
                body.update(ready=snap is not None, production_profile_configured=False,
                            data_current=False, provenance=provenance() if snap else None,
                            state=snap.state() if snap else None)
            else:
                if snap is None:
                    raise APIError("SNAPSHOT_INVALID" if self.local else "PROFILE_UNCONFIGURED")
                body.update(preview(snap.supply, snap.reserve, snap.maintenance, *args))
                body.update(arithmetic_only=True, authorization_verified=False, execution_guaranteed=False,
                            eligibility="UNASSESSED", production_profile_configured=False,
                            data_current=False, provenance=provenance())
            return 200, body
        except APIError as exc:
            body["error"] = {"code": exc.code, "message": exc.message}
            return exc.status, body
