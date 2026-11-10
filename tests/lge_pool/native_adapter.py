"""New standalone native CPMM adapter; no old harness imports or public RPC."""
from pathlib import Path
import base64
import gzip
import hashlib
import importlib.metadata
import json
import os
import platform
import struct
import sys
from datetime import datetime, timezone

from solders.account import Account
from solders.clock import Clock
from solders.compute_budget import set_compute_unit_limit
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.litesvm import LiteSVM
from solders.pubkey import Pubkey
from solders.system_program import create_account, transfer
from solders.transaction import Transaction
from solders.transaction_metadata import FailedTransactionMetadata

ROOT = Path(__file__).resolve().parents[2]
SCOPE = "evidence/LGE_POOL_TEST_SCOPE.md"
SCOPE_SHA = "3cf337bc3c7d03d7c9ec4e04e5908dd31a3613106f078ca573f7cb1cb02346c8"
FIXTURE_SHA = "ca481f4e8389fbd1ba799d89dc320898c346f611af9685760020658c5de1db7b"
ABI_SHA = "931db4fd5fe5230c5358d71f2232814d0a976a07ec9bfccccaf480a9df49bbbb"
SYSTEM = Pubkey.from_string("11111111111111111111111111111111")
TOKEN = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
T22 = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
ATA = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
WSOL = Pubkey.from_string("So11111111111111111111111111111111111111112")
AMM = Pubkey.from_string("DRaycpLY18LhpbydsBWbVJtxpNv9oXPgjRSfpF2bWpYb")
H = Pubkey.from_string("CseQKCWvi4EA2o3oa11Age4p4xKWSLuzjWCzitASrPJu")
RESERVE, RESERVE_BUMP = Pubkey.find_program_address([b"sol-vault"], H)
CLOCK = Pubkey.from_string("SysvarC1ock11111111111111111111111111111111")
RENT = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
FEE_RECEIVER = Pubkey.from_string("3oE58BKVt8KuYkGxx8zBojugnymWmBiyafWgMrnb6eYy")
U64_MAX = (1 << 64) - 1
SUPPLY = 10**19


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def serialized(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def persist(path, value):
    with Path(path).open("xb") as stream:
        stream.write(serialized(value))
        stream.flush()
        os.fsync(stream.fileno())


def am(key, writable=False, signer=False):
    return AccountMeta(key, signer, writable)


def instruction(program, data, accounts):
    return Instruction(program, bytes(data), accounts)


def option(key):
    return b"\0" if key is None else b"\1" + bytes(key)


def native_transfer(source, destination, amount):
    return transfer({"from_pubkey": source, "to_pubkey": destination, "lamports": amount})


def u64(raw, offset):
    return int.from_bytes(raw[offset:offset + 8], "little")


def extensions(raw):
    result, offset = {}, 166
    while offset + 4 <= len(raw):
        if not any(raw[offset:]):
            break
        kind, size = struct.unpack_from("<HH", raw, offset)
        offset += 4
        assert offset + size <= len(raw) and kind not in result
        result[kind] = raw[offset:offset + size]
        offset += size
    return result


def token(raw):
    assert len(raw) >= 165
    ext = extensions(raw) if len(raw) > 165 else {}
    withheld = ext.get(2, b"\0" * 8)
    assert len(withheld) == 8
    return {"mint": str(Pubkey.from_bytes(raw[:32])), "authority": str(Pubkey.from_bytes(raw[32:64])),
            "amount": str(u64(raw, 64)), "withheld": str(u64(withheld, 0)), "state": raw[108],
            "native_tag": int.from_bytes(raw[109:113], "little"), "native_reserve": str(u64(raw, 113)),
            "extension_types": sorted(ext)}


def mint(raw):
    assert len(raw) == 278
    fee = extensions(raw)[1]
    assert len(fee) == 108
    return {"supply": str(u64(raw, 36)), "decimals": raw[44], "initialized": raw[45],
            "mint_authority_tag": int.from_bytes(raw[:4], "little"),
            "freeze_authority_tag": int.from_bytes(raw[46:50], "little"),
            "fee_configuration_authority": fee[:32].hex(), "withdraw_authority": fee[32:64].hex(),
            "withheld": str(u64(fee, 64)),
            "older": {"epoch": str(u64(fee, 72)), "maximum": str(u64(fee, 80)), "bps": str(int.from_bytes(fee[88:90], "little"))},
            "newer": {"epoch": str(u64(fee, 90)), "maximum": str(u64(fee, 98)), "bps": str(int.from_bytes(fee[106:108], "little"))}}


def pool(raw):
    assert len(raw) == 637
    keys = {name: str(Pubkey.from_bytes(raw[8 + 32 * i:40 + 32 * i])) for i, name in enumerate(
        ["config", "creator", "vault0", "vault1", "lp_mint", "mint0", "mint1", "program0", "program1", "observation"])}
    keys.update({"status": raw[329], "lp_decimals": raw[330], "decimals0": raw[331], "decimals1": raw[332],
                 "lp_supply": str(u64(raw, 333)), "protocol0": str(u64(raw, 341)), "protocol1": str(u64(raw, 349)),
                 "fund0": str(u64(raw, 357)), "fund1": str(u64(raw, 365)), "open_time": str(u64(raw, 373)),
                 "recent_epoch": str(u64(raw, 381)), "creator_fee_on": raw[389], "creator_fee_enabled": raw[390],
                 "creator0": str(u64(raw, 397)), "creator1": str(u64(raw, 405))})
    return keys


def account_record(address, value):
    if value is None:
        return None
    raw = bytes(value.data)
    return {"address": str(address), "owner": str(value.owner), "executable": value.executable,
            "lamports": str(value.lamports), "bytes": len(raw), "data_hex": raw.hex(), "data_sha256": sha(raw)}


def resource_check():
    vfs = os.statvfs(ROOT)
    free = vfs.f_bavail * vfs.f_frsize
    allocated = sum(p.stat().st_blocks * 512 for p in (ROOT / "evidence/lge_pool").rglob("*") if p.is_file())
    assert free >= 2 * 1024**3 and allocated <= 16 * 1024**2, (free, allocated)
    return {"free_bytes": free, "all_lge_evidence_allocated_bytes": allocated, "evidence_cap_bytes": 16 * 1024**2}


def public_inputs():
    assert platform.node() == "weathertrades" and ROOT == Path.cwd() and os.getuid() == ROOT.stat().st_uid
    assert sys.version_info[:3] == (3, 12, 3) and sys.dont_write_bytecode
    assert (ROOT / SCOPE).is_file() and sha((ROOT / SCOPE).read_bytes()) == SCOPE_SHA
    for name, version in [("solders", "0.26.0"), ("jsonalias", "0.1.1"), ("typing_extensions", "4.16.0")]:
        assert importlib.metadata.version(name) == version
    fixture_path = ROOT / "config/m4b/native_fixture.json"
    assert sha(fixture_path.read_bytes()) == FIXTURE_SHA
    assert sha((ROOT / "config/m4b/native_abi.json").read_bytes()) == ABI_SHA
    f = json.loads(fixture_path.read_bytes())
    sources = {SCOPE: SCOPE_SHA, "config/m4b/native_fixture.json": FIXTURE_SHA, "config/m4b/native_abi.json": ABI_SHA}
    codes = {}
    for row in f["captures"]:
        raw = (ROOT / row["path"]).read_bytes()
        assert len(raw) == row["full_bytes"] and sha(raw) == row["full_sha256"]
        codes[row["role"]] = raw
        sources[row["path"]] = sha(raw)
    for spec in [f["raw_config0"], f["bundled_ATA"]]:
        if "container" in spec:
            raw = Path(spec["container"]).read_bytes()
            assert sha(raw) == spec["container_sha256"]
            sources[spec["container"]] = sha(raw)
            ata_raw = raw[spec["slice_offset"]:spec["slice_offset"] + spec["slice_bytes"]]
            assert sha(ata_raw) == spec["ELF_sha256"]
        else:
            raw = (ROOT / spec["path"]).read_bytes()
            assert len(raw) == spec["bytes"] and sha(raw) == spec["sha256"]
            sources[spec["path"]] = sha(raw)
    native_mint = ROOT / "evidence/m4a/author/devnet/native_SOL_mint.account.json"
    meta = json.loads(native_mint.read_bytes())
    # The retained record stores metadata; exact zero-supply bytes are separate.
    mint_path = ROOT / "evidence/m4a/author/devnet/native_SOL_mint.account_data.bin"
    raw = mint_path.read_bytes()
    assert len(raw) == 82 and u64(raw, 36) == 0 and raw[44:46] == bytes([9, 1])
    assert not any(raw[:36]) and not any(raw[46:82])
    assert meta["owner"] == str(TOKEN) and meta["executable"] is False
    assert base64.b64decode(meta["data"][0], validate=True) == raw
    sources[str(native_mint.relative_to(ROOT))] = sha(native_mint.read_bytes())
    sources[str(mint_path.relative_to(ROOT))] = sha(raw)
    return f, codes, sources, ata_raw, raw


class NativeRun:
    """Durable prospective counters and complete raw local sends."""
    def __init__(self, output, role):
        assert role in ("author", "supervisor")
        self.role, self.output = role, Path(output)
        base = ROOT / "evidence/lge_pool" / ("native_author" if role == "author" else "native_supervisor")
        assert self.output.parent == base and self.output.name and not self.output.exists()
        base.mkdir(exist_ok=True)
        old_vm = old_send = 0
        for prior in sorted(base.glob("*/CASE_LEDGER.jsonl")):
            rows = [json.loads(line) for line in prior.read_text().splitlines()]
            assert rows and rows[-1]["event"] == "RUN_FINISHED", "unclosed prior role campaign"
            old_vm += sum(row["event"] == "VM_ATTEMPT_STARTED" for row in rows)
            old_send += sum(row["event"] == "SEND_ATTEMPT_STARTED" for row in rows)
        self.prior_vm, self.prior_send = old_vm, old_send
        self.vms = self.sends = 0
        assert old_vm < 3 and old_send < 200
        self.output.mkdir()
        self.journal = (self.output / "CASE_LEDGER.jsonl").open("xb")
        self.event_file = (self.output / "events.jsonl.gz").open("xb")
        self.compressor = gzip.GzipFile(filename="", mode="wb", fileobj=self.event_file, mtime=0)
        self.sequence = 0
        self.event_count = 0
        self.tracked = {}
        self.fees = 0
        self.synthetic_airdrop_calls = 0
        self.finished = False
        self.append("RUN_STARTED", source_hashes=self.source_hashes(), resources=resource_check(), prior_vm=old_vm, prior_sends=old_send)

    def source_hashes(self):
        return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted((ROOT / "tests/lge_pool").glob("native*.py"))}

    def append(self, event, **values):
        self.sequence += 1
        raw = serialized({"sequence": self.sequence, "UTC": utc(), "role": self.role, "event": event, **values})
        self.journal.write(raw)
        self.journal.flush()
        os.fsync(self.journal.fileno())

    def emit(self, event):
        self.event_count += 1
        self.compressor.write(serialized({"event_index": self.event_count, **event}))
        self.compressor.flush()
        self.event_file.flush()
        os.fsync(self.event_file.fileno())

    def create_vm(self, fixture, codes, ata_bytes):
        assert self.prior_vm + self.vms < 3
        self.append("VM_ATTEMPT_STARTED", ordinal=self.prior_vm + self.vms + 1, resources=resource_check())
        self.vms += 1
        self.svm = LiteSVM().with_sigverify(True).with_blockhash_check(True)
        loaded = {}
        for label, key in [("CPMM", AMM), ("Token2022", T22), ("legacyToken", TOKEN)]:
            self.svm.add_program(key, codes[label])
            observed = self.svm.get_account(key)
            assert observed is not None and observed.executable and bytes(observed.data) == codes[label]
            loaded[label] = {"program": str(key), "owner": str(observed.owner), "bytes": len(observed.data), "sha256": sha(bytes(observed.data))}
        ata_account = self.svm.get_account(ATA)
        assert ata_account is not None and ata_account.executable and bytes(ata_account.data) == ata_bytes
        loaded["ATA"] = {"program": str(ATA), "owner": str(ata_account.owner), "bytes": len(ata_account.data), "sha256": sha(bytes(ata_account.data))}
        assert self.svm.get_account(H) is None
        self.programs = loaded
        self.emit({"kind": "post_load_getters", "programs": loaded, "H_present": False, "loader": fixture["loader"], "public_runtime_equivalence": "NOT_CLAIMED"})
        self.append("VM_CONSTRUCTED", programs=loaded, H_present=False)

    def track(self, role, key):
        assert role not in self.tracked or self.tracked[role] == key
        self.tracked[role] = key
        return key

    def snapshot(self):
        return {role: account_record(key, self.svm.get_account(key)) for role, key in sorted(self.tracked.items())}

    def clock(self, epoch, slot, timestamp, phase, counterfactual=False):
        before = self.svm.get_clock()
        raw = {"kind": "clock_transition", "phase": phase,
               "NON_REAL_BANK_CHRONOLOGY": counterfactual,
               "before": {"epoch": before.epoch, "slot": before.slot, "unix_timestamp": before.unix_timestamp},
               "requested": {"epoch": epoch, "slot": slot, "unix_timestamp": timestamp}}
        self.append("CLOCK_CHANGE_PROSPECTIVE", **raw)
        self.svm.warp_to_slot(slot)
        self.svm.set_clock(Clock(slot, 0, epoch, epoch, timestamp))
        actual = self.svm.get_clock()
        assert (actual.epoch, actual.slot, actual.unix_timestamp) == (epoch, slot, timestamp)
        raw["getter"] = {"epoch": actual.epoch, "slot": actual.slot, "unix_timestamp": actual.unix_timestamp}
        raw["raw_sysvars"] = {"clock": account_record(CLOCK, self.svm.get_account(CLOCK)), "rent": account_record(RENT, self.svm.get_account(RENT))}
        self.emit(raw)

    def send(self, name, instructions, signer_objects=(), expected_error=None):
        resource_check()
        assert self.prior_send + self.sends < 200
        before = self.snapshot()
        self.svm.expire_blockhash()
        blockhash = self.svm.latest_blockhash()
        signers = {str(self.operations.pubkey()): self.operations}
        signers.update({str(k.pubkey()): k for k in signer_objects})
        tx = Transaction.new_signed_with_payer([set_compute_unit_limit(1_400_000), *instructions], self.operations.pubkey(), list(signers.values()), blockhash)
        packet = bytes(tx)
        assert len(packet) <= 1232 and all(tx.verify_with_results())
        ix_rows = [{"program_id": str(ix.program_id), "data_hex": bytes(ix.data).hex(),
                    "accounts": [{"pubkey": str(m.pubkey), "is_signer": m.is_signer, "is_writable": m.is_writable} for m in ix.accounts]} for ix in instructions]
        self.append("SEND_ATTEMPT_STARTED", ordinal=self.prior_send + self.sends + 1, name=name, packet_sha256=sha(packet), packet_bytes=len(packet), expected_error=expected_error, source_hashes=self.source_hashes())
        self.sends += 1
        result = self.svm.send_transaction(tx)
        failed = isinstance(result, FailedTransactionMetadata)
        meta = result.meta() if failed else result
        after = self.snapshot()
        fee = len(tx.signatures) * 5000
        self.fees += fee
        row = {"kind": "transaction", "name": name, "ordinal": self.prior_send + self.sends,
               "status": "FAILURE" if failed else "SUCCESS", "expected_error": expected_error,
               "error": str(result.err()) if failed else None, "transaction_hex": packet.hex(), "transaction_sha256": sha(packet), "packet_bytes": len(packet),
               "message_hex": bytes(tx.message).hex(), "message_sha256": sha(bytes(tx.message)), "recent_blockhash": str(blockhash),
               "signatures": [str(s) for s in tx.signatures], "signature_verification": tx.verify_with_results(),
               "compute_unit_limit": 1_400_000, "compute_units": meta.compute_units_consumed(), "network_fee_expected_lamports": str(fee),
               "payer": str(self.operations.pubkey()), "instructions": ix_rows, "logs": meta.logs(),
               "inner_instructions": [[json.loads(inner.to_json()) for inner in group] for group in meta.inner_instructions()],
               "before": before, "after": after, "program_hashes": self.programs}
        self.emit(row)
        self.append("SEND_ATTEMPT_COMPLETED", ordinal=self.prior_send + self.sends, name=name, status=row["status"], error=row["error"], packet_sha256=sha(packet), compute_units=row["compute_units"])
        assert row["compute_units"] <= 1_400_000
        if failed:
            for role, old in before.items():
                want = old
                if old is not None and old["address"] == str(self.operations.pubkey()):
                    want = dict(old, lamports=str(int(old["lamports"]) - fee))
                assert after[role] == want, ("rollback", name, role)
            assert expected_error is not None, row["error"]
            if type(expected_error) is int:
                assert getattr(getattr(result.err(), "err", None), "code", None) == expected_error, row["error"]
            else:
                assert expected_error in row["error"], row["error"]
        else:
            assert expected_error is None, (name, "unexpected success")
        return row

    def finish(self, status, error=None):
        if self.finished:
            return
        self.finished = True
        self.compressor.close()
        self.event_file.flush()
        os.fsync(self.event_file.fileno())
        self.event_file.close()
        raw = (self.output / "events.jsonl.gz").read_bytes()
        decoded = gzip.decompress(raw)
        record = {"schema": "HTFP_LGE_POOL_NATIVE_RUN_V1", "status": status, "role": self.role, "error": error,
                  "actual_vm_attempts": self.vms, "actual_send_attempts": self.sends, "prior_role_vm_attempts": self.prior_vm,
                  "explicit_signed_send_attempts": self.sends, "synthetic_airdrop_API_calls": self.synthetic_airdrop_calls,
                  "airdrop_internal_native_execution": "LiteSVM implementation may execute an internal transfer; not represented as an extra explicit signed-send envelope",
                  "prior_role_send_attempts": self.prior_send, "role_cumulative_vm_attempts": self.prior_vm + self.vms,
                  "role_cumulative_send_attempts": self.prior_send + self.sends, "network_fees_expected_lamports": str(self.fees),
                  "events": {"path": str((self.output / "events.jsonl.gz").relative_to(ROOT)), "stored_bytes": len(raw), "stored_sha256": sha(raw), "raw_bytes": len(decoded), "raw_sha256": sha(decoded), "rows": self.event_count},
                  "source_hashes_after": self.source_hashes(), "resources": resource_check(), "stage_acceptance": False}
        persist(self.output / "RESULT.json", record)
        self.append("RUN_FINISHED", **record)
        self.journal.close()
