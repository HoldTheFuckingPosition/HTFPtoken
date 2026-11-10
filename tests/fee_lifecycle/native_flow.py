"""New isolated H/Token2022/CPMM fee lifecycle; imports only frozen LGE helpers."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import struct
import sys
import time
import traceback
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {
    "tests/lge_pool/native_adapter.py": "8af4335544daf41cdb7997208ea85ef10055d41319c63e95d3177056fcc86c85",
    "tests/lge_pool/native_rehearsal.py": "05774d26766e96b4b57278cd7d1bbb559691359d5219f819e4ce0d100402f167",
}
for _path, _digest in FROZEN.items():
    assert hashlib.sha256((ROOT / _path).read_bytes()).hexdigest() == _digest
sys.path.insert(0, str(ROOT / "tests/lge_pool"))
import native_adapter as n
import native_rehearsal as lge
from solders.system_program import create_account_with_seed

SCOPE = "evidence/FEE_LIFECYCLE_SCOPE.md"
SCOPE_SHA = "1be67d272968223770801e46143cb3892a3af2463fda62b3cc4ef7b475c814b3"
FOUNDER_SHA = "4515882625ed1be8fb2f5a8fde045016e78f74bf3cc4e87a7ec25447251a9d30"
PROFILE_PATH = "config/m3/local_profile.json"
PROFILE_SHA = "8c39db647774d1e24946aa8cebf00d18ee527a6af47a3c5d1c8f614b92398f6a"
BUILD_PATH = "evidence/m4b/supervisor/process/build-m3-final/build.json"
BUILD_SHA = "2458aba055d06cdf17d05d7ca965d8e94627f42ac391d7463e8cd27502c6fa02"
H_PATH = "evidence/m4b/supervisor/process/build-m3-final/htfp.so"
H_SHA = "2634fd48775e74e845aee5018e49dc8663f7ccb671871efb5df4adf0ca07823c"


def resources():
    fs = os.statvfs(ROOT)
    free = fs.f_bavail * fs.f_frsize
    used = sum(p.stat().st_blocks * 512 for p in (ROOT / "evidence/fee_lifecycle").rglob("*") if p.is_file())
    assert free >= 2 * 1024**3 and used <= 16 * 1024**2, (free, used)
    return {"free_bytes": free, "all_fee_lifecycle_allocated_bytes": used, "evidence_cap_bytes": 16 * 1024**2}


def inputs():
    fixture, codes, hashes, ata, wsol = n.public_inputs()
    for path, digest in {SCOPE: SCOPE_SHA, "evidence/fee_lifecycle/FOUNDER_SOURCE.json": FOUNDER_SHA,
                         PROFILE_PATH: PROFILE_SHA, BUILD_PATH: BUILD_SHA, H_PATH: H_SHA, **FROZEN}.items():
        assert n.sha((ROOT / path).read_bytes()) == digest, path
        hashes[path] = digest
    profile = json.loads((ROOT / PROFILE_PATH).read_bytes())
    public = {role: n.Pubkey.from_string(value["base58"]) for role, value in profile["public_keys"].items()}
    assert public["program"] == n.H and public["reserve"] == n.RESERVE
    build = json.loads((ROOT / BUILD_PATH).read_bytes())
    assert build["feature"] == "local-m3" and build["kind"] == "htfp" and build["source_unchanged"]
    assert build["exit_status"] == "0" and build["elf_sha256"] == H_SHA and int(build["elf_bytes"]) == 155240
    for path, digest in build["inputs_before_sha256"].items():
        assert n.sha((ROOT / path).read_bytes()) == digest, path
        hashes[path] = digest
    assert hashes["programs/htfp/src/lib.rs"] == "c4ecf74099de5175d0940f469f809f699bbbebdf69327e129e638215c16799cd"
    assert hashes["programs/htfp/src/profile.rs"] == "0b115a8b0321979f38459a8e93351a96c7275dbb8c94099731fdef073ab6df2a"
    return fixture, codes, hashes, ata, wsol, public


class Run(n.NativeRun):
    """New namespace/caps; inherited packet/send/rollback/clock evidence code is frozen."""
    def __init__(self, output, role):
        assert role in ("author", "supervisor")
        self.role, self.output = role, Path(output)
        base = ROOT / "evidence/fee_lifecycle" / role
        assert self.output.parent == base and not self.output.exists()
        base.mkdir(exist_ok=True)
        vm = sends = 0
        for prior in sorted(base.glob("*/CASE_LEDGER.jsonl")):
            rows = [json.loads(line) for line in prior.read_text().splitlines()]
            assert rows and rows[-1]["event"] == "RUN_FINISHED", "unclosed prior lifecycle campaign"
            vm += sum(row["event"] == "VM_ATTEMPT_STARTED" for row in rows)
            sends += sum(row["event"] == "SEND_ATTEMPT_STARTED" for row in rows)
        assert vm < 3 and sends < 160
        self.prior_vm, self.prior_send = vm, sends
        self.vms = self.sends = self.synthetic_airdrop_calls = self.fees = 0
        self.output.mkdir()
        self.journal = (self.output / "CASE_LEDGER.jsonl").open("xb")
        self.event_file = (self.output / "events.jsonl.gz").open("xb")
        self.compressor = gzip.GzipFile(filename="", mode="wb", fileobj=self.event_file, mtime=0)
        self.sequence = self.event_count = 0
        self.tracked = {}
        self.finished = False
        self.append("RUN_STARTED", source_hashes=self.source_hashes(), resources=resources(), prior_vm=vm, prior_sends=sends)

    def source_hashes(self):
        paths = sorted([*FROZEN, *[str(p.relative_to(ROOT)) for p in (ROOT / "tests/fee_lifecycle").glob("*.py")]])
        return {p: n.sha((ROOT / p).read_bytes()) for p in paths}

    def send(self, *args, **kwargs):
        resources()
        assert self.prior_send + self.sends < 160
        return super().send(*args, **kwargs)

    def load_h(self):
        raw = (ROOT / H_PATH).read_bytes()
        assert len(raw) == 155240 and n.sha(raw) == H_SHA and self.svm.get_account(n.H) is None
        self.append("H_LOAD_PROSPECTIVE", path=H_PATH, bytes=len(raw), sha256=H_SHA, build_path=BUILD_PATH, build_sha256=BUILD_SHA)
        self.svm.add_program(n.H, raw)
        a = self.svm.get_account(n.H)
        assert a is not None and a.executable and bytes(a.data) == raw
        self.programs["H"] = {"program": str(n.H), "owner": str(a.owner), "bytes": len(a.data), "sha256": n.sha(bytes(a.data)), "feature": "local-m3", "build_sha256": BUILD_SHA}
        self.emit({"kind": "H_post_load_getter", "actual": self.programs["H"], "binary_copied_to_evidence": False, "source_public_equivalence": "NOT_CLAIMED"})

    def finish(self, status, error=None):
        if self.finished:
            return
        self.finished = True
        self.compressor.close()
        self.event_file.flush()
        os.fsync(self.event_file.fileno())
        self.event_file.close()
        stored = (self.output / "events.jsonl.gz").read_bytes()
        raw = gzip.decompress(stored)
        record = {"schema": "HTFP_FEE_LIFECYCLE_NATIVE_RESULT_V1", "status": status, "error": error, "role": self.role,
                  "actual_vm_attempts": self.vms, "explicit_signed_send_attempts": self.sends, "synthetic_airdrop_API_calls": self.synthetic_airdrop_calls,
                  "prior_role_vm_attempts": self.prior_vm, "prior_role_send_attempts": self.prior_send,
                  "role_cumulative_vm_attempts": self.prior_vm + self.vms, "role_cumulative_send_attempts": self.prior_send + self.sends,
                  "events": {"path": str((self.output / "events.jsonl.gz").relative_to(ROOT)), "stored_bytes": len(stored), "stored_sha256": n.sha(stored), "raw_bytes": len(raw), "raw_sha256": n.sha(raw), "rows": self.event_count},
                  "network_fees_expected_lamports": str(self.fees), "source_hashes_after": self.source_hashes(), "resources": resources(),
                  "airdrop_internal_native_execution": "separate synthetic API call; no assertion that implementation-internal transfers are absent", "stage_acceptance": False}
        n.persist(self.output / "RESULT.json", record)
        self.append("RUN_FINISHED", **record)
        self.journal.close()


def published_test_signer(number):
    # RFC8032 publicly published artificial vectors, not operational key material.
    public_vectors = ["9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
                      "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
                      "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7"]
    return n.Keypair.from_seed(bytes.fromhex(public_vectors[number - 1]))


class Lifecycle(lge.Rehearsal):
    def snapshot_file(self, filename, phase, **extra):
        clock = self.r.svm.get_clock()
        h = self.r.svm.get_account(n.H)
        assert h is not None and h.executable
        value = {"schema": "HTFP_FEE_LIFECYCLE_RAW_PHASE_V1", "phase": phase, "UTC": n.utc(),
                 "clock_getter": {"epoch": clock.epoch, "slot": clock.slot, "unix_timestamp": clock.unix_timestamp},
                 "accounts": self.r.snapshot(), "H_present": True, "H_metadata": {"owner": str(h.owner), "bytes": len(h.data), "executable": h.executable, "sha256": n.sha(bytes(h.data))}, **extra}
        n.persist(self.r.output / filename, value)
        return value

    def prepare(self, fixture, native_wsol, public):
        r = self.r
        self.operations, self.mint_signer, self.founder = [published_test_signer(i) for i in (1, 2, 3)]
        assert self.operations.pubkey() == public["initializer"] and self.mint_signer.pubkey() == public["mint"] and self.founder.pubkey() == public["genesis_owner"]
        self.team, self.marketing = n.Keypair(), n.Keypair()
        self.participants = [n.Keypair() for _ in lge.CONTRIBUTIONS]
        r.operations = self.operations
        for role, key in [("operations", self.operations.pubkey()), ("founder", self.founder.pubkey()), ("mint", self.mint_signer.pubkey()), ("team", self.team.pubkey()), ("marketing", self.marketing.pubkey())]:
            self.track(role, key)
        for i, kp in enumerate(self.participants, 1):
            self.track("participant-" + str(i), kp.pubkey())
        for role in ["config", "inventory", "custody", "genesis_holding", "tax_authority", "reserve"]:
            self.track(role, public[role])
        self.tax_authority = public["tax_authority"]
        self.track("clock", n.CLOCK)
        self.track("rent", n.RENT)
        self.track("wsol_mint", n.WSOL)
        assert r.svm.get_account(n.RESERVE) is None
        r.append("SYNTHETIC_SOL_AIRDROP_PROSPECTIVE", address=str(self.operations.pubkey()), lamports=str(lge.OPS_START))
        answer = r.svm.airdrop(self.operations.pubkey(), lge.OPS_START)
        r.synthetic_airdrop_calls += 1
        assert r.svm.get_balance(self.operations.pubkey()) == lge.OPS_START
        r.emit({"kind": "synthetic_SOL_initialization", "address": str(self.operations.pubkey()), "before": None,
                "after": n.account_record(self.operations.pubkey(), r.svm.get_account(self.operations.pubkey())),
                "airdrop_return_type": type(answer).__module__ + "." + type(answer).__name__, "public_funds": False})
        r.svm.set_account(n.WSOL, n.Account(r.svm.minimum_balance_for_rent_exemption(82), native_wsol, n.TOKEN))
        config_raw = (ROOT / fixture["raw_config0"]["path"]).read_bytes()
        config_key = n.Pubkey.find_program_address([b"amm_config", bytes([0, 0])], n.AMM)[0]
        self.track("amm_config", config_key)
        r.svm.set_account(config_key, n.Account(r.svm.minimum_balance_for_rent_exemption(236), config_raw, n.AMM))
        assert n.u64(config_raw, 12) == n.u64(config_raw, 108) == 2500 and n.u64(config_raw, 116) == 0
        self.track("creation_fee_receiver", n.FEE_RECEIVER)
        r.svm.set_account(n.FEE_RECEIVER, n.Account(r.svm.minimum_balance_for_rent_exemption(165), bytes(165), n.TOKEN))
        r.emit({"kind": "explicit_nonmonetary_dependency_prestate", "after": {k: r.snapshot()[k] for k in ["wsol_mint", "amm_config", "creation_fee_receiver"]},
                "disclosure": "Only exact zero-supply native SOL mint metadata, unchanged captured config0, and zero-filled fee receiver storage with local rent. No positive token, custody/R or pool state injected."})
        self.initial_tracked_lamports = sum(int(a["lamports"]) for a in r.snapshot().values() if a is not None)
        r.send("native_initialize_zero_value_creation_fee_receiver", [n.instruction(n.TOKEN, bytes([18]) + bytes(self.founder.pubkey()), [n.am(n.FEE_RECEIVER, True), n.am(n.WSOL)])])
        assert self.amount("creation_fee_receiver") == 0
        self.t0 = int(time.time())
        self.activation_timestamp = self.t0 + 120
        self.open_time = self.activation_timestamp + 14400
        r.clock(7, 100000, self.t0, "coherent_E7_before_genesis")
        self.plan = {"LOCAL_TEST_ONLY": True, "scope_sha256": SCOPE_SHA, "supply_base_units": str(n.SUPPLY), "decimals": "7",
                     "participants": [{"id": "participant-" + str(i + 1), "contribution_lamports": str(c), "token_base_units": str(a)} for i, (c, a) in enumerate(zip(lge.CONTRIBUTIONS, lge.ENTITLEMENTS))],
                     "total_contribution_lamports": str(lge.TOTAL), "token_allocations_base_units": {"participants": str(sum(lge.ENTITLEMENTS)), "pool": str(lge.POOL_HTFP), "team": str(lge.TEAM_HTFP), "marketing": str(lge.MARKETING_HTFP)},
                     "sol_allocations_lamports": {"reserve": str(lge.RESERVE_SOL), "pool": str(lge.POOL_SOL)},
                     "synthetic_clock": {"E": 7, "E_plus_2": 9, "initial_unix": self.t0, "activation_unix": self.activation_timestamp, "opening_unix": self.open_time, "test_only_margin_seconds": 14400, "real_prediction": False},
                     "operations_initial_lamports": str(lge.OPS_START), "creator_topup_lamports": str(lge.CREATOR_OPERATIONAL_TOPUP), "historical_fee_config_ppm": [2500, 2500], "final_creator500_validated": False}
        n.persist(r.output / "PLAN.json", self.plan)

    def genesis(self):
        r, p, m, g = self.r, self.operations.pubkey(), self.keys["mint"], self.keys["genesis_holding"]
        assert n.Pubkey.create_with_seed(p, "m3-local-holder-v1", n.T22) == g
        create = n.create_account({"from_pubkey": p, "to_pubkey": m, "lamports": r.svm.minimum_balance_for_rent_exemption(278), "space": 278, "owner": n.T22})
        fee_config = n.instruction(n.T22, bytes([26, 0]) + n.option(p) + n.option(self.tax_authority) + struct.pack("<HQ", 0, n.U64_MAX), [n.am(m, True)])
        init_mint = n.instruction(n.T22, bytes([20, 7]) + bytes(p) + n.option(None), [n.am(m, True)])
        r.send("native_fixed_M3_create_0bps_mint", [create, fee_config, init_mint], [self.mint_signer])
        holding = create_account_with_seed({"from_pubkey": p, "to_pubkey": g, "base": p, "seed": "m3-local-holder-v1", "lamports": r.svm.minimum_balance_for_rent_exemption(178), "space": 178, "owner": n.T22})
        r.send("native_exact_seeded_GenesisHolding178", [holding, n.instruction(n.T22, bytes([18]) + bytes(self.founder.pubkey()), [n.am(g, True), n.am(m)])])
        r.send("native_full_initial_issuance_to_fixed_genesis", [n.instruction(n.T22, bytes([14]) + struct.pack("<QB", n.SUPPLY, 7), [n.am(m, True), n.am(g, True), n.am(p, False, True)])])
        r.send("native_schedule9_revoke_fee_and_mint_authorities", [
            n.instruction(n.T22, bytes([26, 5]) + struct.pack("<HQ", 800, n.U64_MAX), [n.am(m, True), n.am(p, False, True)]),
            n.instruction(n.T22, bytes([6, 4]) + n.option(None), [n.am(m, True), n.am(p, False, True)]),
            n.instruction(n.T22, bytes([6, 0]) + n.option(None), [n.am(m, True), n.am(p, False, True)])])
        state = n.mint(self.raw("mint"))
        assert state["supply"] == str(n.SUPPLY) and self.amount("genesis_holding") == n.SUPPLY
        assert state["mint_authority_tag"] == state["freeze_authority_tag"] == 0 and state["fee_configuration_authority"] == "00" * 32
        assert state["older"] == {"epoch": "7", "maximum": str(n.U64_MAX), "bps": "0"} and state["newer"] == {"epoch": "9", "maximum": str(n.U64_MAX), "bps": "800"}
        assert state["withdraw_authority"] == bytes(self.tax_authority).hex()
        self.snapshot_file("PHASE_GENESIS_BEFORE_H.json", "full_fixed_supply_before_any_H_initialization_or_distribution", decoded_mint=state)
        metas = [n.am(self.keys["config"], True), n.am(self.keys["inventory"], True), n.am(m), n.am(self.keys["custody"], True), n.am(self.tax_authority), n.am(n.RESERVE), n.am(g), n.am(p, True, True), n.am(n.T22), n.am(n.SYSTEM)]
        r.send("genuine_H_Initialize_before_distribution", [n.instruction(n.H, bytes.fromhex("485446500100"), metas)])
        assert len(self.raw("config")) == 175 and len(self.raw("inventory")) == 20 and len(self.raw("custody")) == 178
        assert self.booked() == 0 and self.raw("inventory")[11] == 0 and self.amount("custody") == self.withheld("custody") == 0
        assert self.amount("genesis_holding") == n.SUPPLY and n.mint(self.raw("mint")) == state
        self.config_bytes = self.raw("config")
        self.snapshot_file("PHASE_H_INITIALIZED.json", "actual_H_initialized_R0_guard0_full_genesis_retained")
        self.ata("founder_htfp", self.founder.pubkey(), m, n.T22)
        self.transfer_token("zero_tax_move_initialized_genesis_to_founder_ATA", "genesis_holding", "founder_htfp", n.SUPPLY, self.founder, 0)
        assert self.amount("genesis_holding") == 0
        self.mint_initialized_bytes = self.raw("mint")

    def booked(self):
        return n.u64(self.raw("inventory"), 12)

    def recover_ix(self, roles, custody_override=None):
        metas = [n.am(self.keys["config"]), n.am(self.keys["inventory"], True), n.am(self.keys["mint"], True),
                 n.am(custody_override or self.keys["custody"], True), n.am(self.tax_authority), n.am(n.T22)]
        metas.extend(n.am(self.keys[role], True) for role in roles)
        return n.instruction(n.H, bytes.fromhex("485446500101") + struct.pack("<H", len(roles)), metas)

    def recover(self, name, roles):
        assert len({str(self.keys[k]) for k in roles}) == len(roles)
        before_r, before_c = self.booked(), self.amount("custody")
        expected = int(n.mint(self.raw("mint"))["withheld"]) + self.withheld("custody") + sum(self.withheld(k) for k in roles)
        old = {k: (self.amount(k), self.raw(k)) for k in roles}
        supply_before = n.mint(self.raw("mint"))["supply"]
        reserve_before = self.account("reserve").lamports
        row = self.r.send(name, [self.recover_ix(roles)])
        assert self.booked() == before_r + expected and self.amount("custody") == before_c + expected
        assert self.booked() <= self.amount("custody") and self.withheld("custody") == 0
        assert n.mint(self.raw("mint"))["withheld"] == "0" and n.mint(self.raw("mint"))["supply"] == supply_before
        for role, (amount, raw) in old.items():
            assert self.amount(role) == amount and self.withheld(role) == 0
            before = bytearray(raw)
            cursor = 166
            while cursor + 4 <= len(before):
                kind, length = struct.unpack_from("<HH", before, cursor)
                cursor += 4
                if kind == 2:
                    assert length == 8
                    before[cursor:cursor + 8] = bytes(8)
                    break
                cursor += length
            assert self.raw(role) == bytes(before)
        assert self.raw("config") == self.config_bytes and self.raw("inventory")[11] == 0
        assert self.account("reserve").lamports == reserve_before
        proof = {"name": name, "sources": roles, "expected_from_raw_before": str(expected), "R_before": str(before_r), "R_after": str(self.booked()),
                 "custody_before": str(before_c), "custody_after": str(self.amount("custody")), "surplus_after": str(self.amount("custody") - self.booked()), "transaction_sha256": row["transaction_sha256"]}
        self.r.emit({"kind": "H_recover_delta_certificate", **proof})
        return proof

    def opening_and_transfers(self):
        r = self.r
        self.ata("trader_wsol", self.participants[4].pubkey(), n.WSOL, n.TOKEN)
        r.send("separate_operational_trader_wrap", [n.native_transfer(self.operations.pubkey(), self.keys["trader_wsol"], lge.TRADER_OPERATIONAL_SOL), n.instruction(n.TOKEN, bytes([17]), [n.am(self.keys["trader_wsol"], True)])])
        r.clock(8, 110000, self.t0 + 60, "coherent_E8_pre_activation")
        e8 = self.transfer_token("E8_native_transfer_still_0percent", "participant-1_htfp", "participant-2_htfp", 1001, self.participants[0], 0)
        r.clock(9, 120000, self.open_time - 1, "coherent_E9_pool_still_closed")
        r.send("pre_open_CPMM_swap_reject", [self.swap_instruction(False, 1000000)], [self.participants[4]], expected_error=6000)
        r.clock(9, 120001, self.open_time, "coherent_E9_exact_opening")
        transfers = [self.transfer_token("literal_800bps_transfer_" + str(amount), "participant-1_htfp", "participant-2_htfp", amount, self.participants[0], 800) for amount in [1, 1001, 1000000007]]
        assert [p["actual_withheld"] for p in transfers] == ["1", "81", "80000001"]
        buy = self.checked_swap("pool_buy_active_800bps", False, 1000000, 800)
        sell = self.checked_swap("pool_sell_active_800bps", True, 100000000000000, 800)
        self.snapshot_file("PHASE_PRE_RECOVERY.json", "native_active_tax_sources_before_H_recovery")
        return {"E8_transfer": e8, "literal_transfers": transfers, "buy": buy, "sell": sell}

    def recovery_cases(self):
        r = self.r
        roles = ["participant-2_htfp", "participant-5_htfp", "vault" + str(self.htfp_side)]
        r.send("H_Recover_duplicate_sources_reject", [self.recover_ix([roles[0], roles[0]])], expected_error=7003)
        r.send("H_Recover_wrong_fixed_custody_reject", [self.recover_ix(roles, self.keys["founder_htfp"])], expected_error=7001)
        batch = self.recover("H_Recover_taxed_wallet_and_pool_vault_batch", roles)
        assert int(batch["expected_from_raw_before"]) > 0
        retry = self.recover("H_Recover_same_cleared_batch_idempotent", roles)
        empty = self.recover("H_Recover_empty_batch_idempotent", [])
        assert retry["expected_from_raw_before"] == empty["expected_from_raw_before"] == "0"
        self.snapshot_file("PHASE_POST_BATCH_RECOVERY.json", "H_recovered_batch_R_and_C_equal")
        self.transfer_token("new_native_tax_for_mint_held_path", "participant-1_htfp", "participant-2_htfp", 1001, self.participants[0], 800)
        assert self.withheld("participant-2_htfp") == 81
        before_r, before_c = self.booked(), self.amount("custody")
        r.send("native_permissionless_harvest_to_mint", [n.instruction(n.T22, bytes([26, 4]), [n.am(self.keys["mint"], True), n.am(self.keys["participant-2_htfp"], True)])])
        assert n.mint(self.raw("mint"))["withheld"] == "81" and self.withheld("participant-2_htfp") == 0
        assert self.booked() == before_r and self.amount("custody") == before_c
        self.snapshot_file("PHASE_MINT_HELD.json", "native_harvest_has_not_yet_credited_H_R")
        unauthorized = n.instruction(n.T22, bytes([26, 2]), [n.am(self.keys["mint"], True), n.am(self.keys["founder_htfp"], True), n.am(self.founder.pubkey(), False, True)])
        r.send("unauthorized_native_mint_withheld_withdrawal_reject", [unauthorized], [self.founder], expected_error="Custom(4)")
        mintheld = self.recover("H_Recover_mint_held_with_n0", [])
        assert mintheld["expected_from_raw_before"] == "81"
        donation_r = self.booked()
        donation = self.transfer_token("native_taxed_spendable_donation_to_custody", "participant-3_htfp", "custody", 1001, self.participants[2], 800)
        assert self.booked() == donation_r and self.amount("custody") - self.booked() == 920 and self.withheld("custody") == 81
        self.snapshot_file("PHASE_DONATION.json", "donation_net_unbooked_withheld_separate")
        donation_recovery = self.recover("H_Recover_only_donation_withholding_n0", [])
        assert donation_recovery["expected_from_raw_before"] == "81" and donation_recovery["surplus_after"] == "920"
        continued = self.checked_swap("pool_buy_continues_after_H_recovery", False, 2000000, 800)
        return {"batch": batch, "retry": retry, "empty": empty, "mint_held": mintheld, "donation": donation, "donation_recovery": donation_recovery, "post_recovery_trade": continued}

    def collect_ix(self, signed=True):
        creator_share = n.Pubkey.find_program_address([b"creator_fee_share", bytes(self.founder.pubkey()), bytes(self.keys["amm_config"])], n.AMM)[0]
        self.track("creator_share", creator_share)
        side_destinations = [self.keys["founder_htfp"] if values[0] == self.keys["mint"] else self.keys["founder_wsol"] for values in self.ordered]
        metas = [n.am(self.founder.pubkey(), True, signed), n.am(self.authority), n.am(self.keys["pool"], True), n.am(self.keys["amm_config"]),
                 n.am(self.keys["vault0"], True), n.am(self.keys["vault1"], True), n.am(self.ordered[0][0]), n.am(self.ordered[1][0]),
                 n.am(side_destinations[0], True), n.am(side_destinations[1], True), n.am(self.ordered[0][1]), n.am(self.ordered[1][1]),
                 n.am(n.ATA), n.am(n.SYSTEM), n.am(creator_share)]
        return n.instruction(n.AMM, bytes.fromhex("1416567bc61cdb84"), metas)

    def creator_claim(self):
        r = self.r
        p0 = n.pool(self.raw("pool"))
        gross = [int(p0["creator0"]), int(p0["creator1"])]
        assert all(x > 0 for x in gross)
        old = {role: (self.amount(role), self.withheld(role)) for role in ["founder_htfp", "founder_wsol", "vault0", "vault1"]}
        supply = n.mint(self.raw("mint"))["supply"]
        unsigned = self.collect_ix(False)
        assert r.svm.get_account(self.keys["creator_share"]) is None
        r.send("creator_claim_missing_founder_signature_reject", [unsigned], expected_error=3010)
        row = r.send("genuine_CPMM_creator_claim_both_assets_same_founder", [self.collect_ix(True)], [self.founder])
        p1 = n.pool(self.raw("pool"))
        assert p1["creator0"] == p1["creator1"] == "0"
        h_gross, w_gross = gross[self.htfp_side], gross[1 - self.htfp_side]
        h_tax = lge.fee(h_gross, 800)
        assert self.amount("founder_htfp") - old["founder_htfp"][0] == h_gross - h_tax
        assert self.withheld("founder_htfp") - old["founder_htfp"][1] == h_tax
        assert self.amount("founder_wsol") - old["founder_wsol"][0] == w_gross
        for side in range(2):
            assert old["vault" + str(side)][0] - self.amount("vault" + str(side)) == gross[side]
            assert self.withheld("vault" + str(side)) == old["vault" + str(side)][1]
            for prefix in ["protocol", "fund"]:
                assert p1[prefix + str(side)] == p0[prefix + str(side)]
        assert n.mint(self.raw("mint"))["supply"] == supply and self.amount("founder_lp") == self.lp_receipt
        assert n.token(self.raw("founder_htfp"))["authority"] == n.token(self.raw("founder_wsol"))["authority"] == str(self.founder.pubkey())
        claim = {"gross_by_side": list(map(str, gross)), "HTFP_gross": str(h_gross), "HTFP_tax": str(h_tax), "HTFP_net": str(h_gross - h_tax), "wSOL_gross": str(w_gross), "recipient_owner": str(self.founder.pubkey()), "share_override_absent": True, "fallback_share_ppm": "0", "transaction_sha256": row["transaction_sha256"]}
        self.snapshot_file("PHASE_CREATOR_COLLECTED.json", "creator_assets_received_HTFP_tax_still_withheld", claim=claim)
        r.send("creator_claim_no_accrual_retry_reject", [self.collect_ix(True)], [self.founder], expected_error=6014)
        recovered = self.recover("H_Recover_new_creator_receipt_withholding", ["founder_htfp"])
        assert recovered["expected_from_raw_before"] == str(h_tax)
        w_amount = self.amount("founder_wsol")
        assert w_amount == w_gross
        w_lamports = self.account("founder_wsol").lamports
        native_rent = int(n.token(self.raw("founder_wsol"))["native_reserve"])
        founder_before = self.account("founder").lamports
        assert w_lamports == native_rent + w_amount
        closed = r.send("native_unwrap_only_founder_creator_wSOL_receipt", [n.instruction(n.TOKEN, bytes([9]), [n.am(self.keys["founder_wsol"], True), n.am(self.founder.pubkey(), True), n.am(self.founder.pubkey(), False, True)])], [self.founder])
        after = self.account("founder_wsol")
        assert after is None or (after.lamports == 0 and len(after.data) == 0 and after.owner == n.SYSTEM)
        assert self.account("founder").lamports - founder_before == w_amount + native_rent
        unwrap = {"wSOL_income": str(w_amount), "returned_account_rent": str(native_rent), "founder_native_SOL_delta": str(w_amount + native_rent), "transaction_sha256": closed["transaction_sha256"], "LP_principal_withdrawn": False}
        r.emit({"kind": "creator_claim_delta_certificate", **claim, "recovery": recovered, "unwrap": unwrap})
        return {"claim": claim, "receipt_tax_recovery": recovered, "unwrap": unwrap}

    def redeem(self):
        r = self.r
        amount = 10**17
        owner = self.participants[0]
        payee = owner.pubkey()
        before_supply = int(n.mint(self.raw("mint"))["supply"])
        reserve = self.account("reserve").lamports
        maintenance = r.svm.minimum_balance_for_rent_exemption(0)
        quotient = Fraction(max(0, reserve - maintenance) * amount, before_supply)
        payout = quotient.numerator // quotient.denominator
        assert payout == 21991091 and payout >= maintenance
        before_token = self.amount("participant-1_htfp")
        before_r, before_c, before_pool, before_lp = self.booked(), self.raw("custody"), self.raw("pool"), self.raw("lp_mint")
        before_payee = r.svm.get_balance(payee) or 0
        def ix(minimum):
            data = bytes.fromhex("485446500102") + struct.pack("<QQ", amount, minimum) + bytes(payee) + bytes([0, 0])
            return n.instruction(n.H, data, [n.am(self.keys["config"]), n.am(self.keys["inventory"], True), n.am(self.keys["mint"], True), n.am(self.keys["participant-1_htfp"], True), n.am(n.RESERVE, True), n.am(payee, True), n.am(owner.pubkey(), False, True), n.am(n.T22), n.am(n.SYSTEM)])
        r.send("H_Redeem_excess_minimum_rolls_back", [ix(payout + 1)], [owner], expected_error=7009)
        row = r.send("genuine_H_Redeem_ordinary_owner", [ix(payout)], [owner])
        assert self.amount("participant-1_htfp") == before_token - amount
        assert int(n.mint(self.raw("mint"))["supply"]) == before_supply - amount
        assert reserve - self.account("reserve").lamports == payout and (r.svm.get_balance(payee) or 0) - before_payee == payout
        assert self.booked() == before_r and self.raw("custody") == before_c and self.raw("pool") == before_pool and self.raw("lp_mint") == before_lp
        assert self.amount("founder_lp") == self.lp_receipt and self.raw("inventory")[11] == 0
        proof = {"amount_burned": str(amount), "supply_before": str(before_supply), "supply_after": str(before_supply - amount), "reserve_before": str(reserve), "Rent_minimum_balance_0": str(maintenance), "payout": str(payout), "minimum": str(payout), "ordinary_owner": str(owner.pubkey()), "recipient": str(payee), "transaction_sha256": row["transaction_sha256"]}
        r.emit({"kind": "H_redeem_delta_certificate", **proof})
        return proof

    def final(self, opening, recovery, creator, redemption):
        roles = [k for k in self.keys if k.endswith("_htfp")] + ["genesis_holding", "custody", "vault" + str(self.htfp_side)]
        assert len({str(self.keys[k]) for k in roles}) == len(roles)
        total = sum(self.amount(k) + self.withheld(k) for k in roles) + int(n.mint(self.raw("mint"))["withheld"])
        assert total == int(n.mint(self.raw("mint"))["supply"]) == n.SUPPLY - 10**17
        assert self.amount("custody") - self.booked() == 920
        assert self.raw("config") == self.config_bytes and self.raw("inventory")[11] == 0
        actual_lamports = sum(int(v["lamports"]) for v in self.r.snapshot().values() if v is not None)
        assert actual_lamports + self.r.fees == self.initial_tracked_lamports
        self.snapshot_file("PHASE_FINAL.json", "coherent_integrated_flow_final", decoded_pool=n.pool(self.raw("pool")), decoded_mint=n.mint(self.raw("mint")))
        report = {"schema": "HTFP_INTEGRATED_FEE_LIFECYCLE_REPORT_V1", "status": "LOCAL_NATIVE_FEE_LIFECYCLE_PASS", "stage_acceptance": False,
                  "scope_sha256": SCOPE_SHA, "role": self.r.role, "H_feature": "local-m3", "H_actual_elf_sha256": H_SHA,
                  "opening_and_literal_transfers": opening, "recovery_cases": recovery, "creator_claim": creator, "ordinary_owner_redemption": redemption,
                  "all_token_roles": roles, "final_spendable_plus_withheld_supply": str(total), "final_R": str(self.booked()), "final_Custody_spendable": str(self.amount("custody")), "unbooked_surplus": "920",
                  "initial_LP_receipt_retained": str(self.lp_receipt), "initial_tracked_lamports": str(self.initial_tracked_lamports), "final_tracked_lamports": str(actual_lamports), "network_fee_lamports": str(self.r.fees),
                  "limitations": ["historical2500/2500config not final2500/500", "no Process/SOL conversion of recovered HTFP", "no LP burn/withdrawal/locker/BurnAndEarn/fullM5", "fixed artificial localM3 identities and synthetic clock, no production profile", "captured programs/bundledATA/synthetic loader, public/source equivalence unproven", "no public actions or actual keys"]}
        n.persist(self.r.output / "REPORT.json", report)
        n.persist(self.r.output / "IDENTITIES.json", {"roles": {k: str(v) for k, v in sorted(self.keys.items())}, "htfp_side": self.htfp_side, "published_artificial_roles": ["operations=initializerTEST1", "mintTEST2", "founderTEST3"], "other_wallets_ephemeral_no_export": True})


def main():
    parser = argparse.ArgumentParser(description="New isolated native fee lifecycle, no network")
    parser.add_argument("--role", choices=("author", "supervisor"), default="author")
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    assert args.label and args.label.replace("-", "").replace("_", "").isalnum()
    fixture, codes, hashes, ata, wsol, public = inputs()
    r = Run(ROOT / "evidence/fee_lifecycle" / args.role / args.label, args.role)
    sources = r.source_hashes()
    try:
        for path, digest in sources.items():
            dest = r.output / "source" / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            raw = (ROOT / path).read_bytes()
            assert n.sha(raw) == digest
            with dest.open("xb") as stream:
                stream.write(raw)
        n.persist(r.output / "INPUTS.json", {"scope_sha256": SCOPE_SHA, "sources": sources, "public_inputs": hashes, "native_fixture": fixture, "H_build_path": BUILD_PATH, "H_actual_elf_sha256": H_SHA, "stage_acceptance": False})
        r.create_vm(fixture, codes, ata)
        r.load_h()
        test = Lifecycle(r)
        test.prepare(fixture, wsol, public)
        test.genesis()
        test.collect_and_distribute()
        test.initialize()
        opening = test.opening_and_transfers()
        recovery = test.recovery_cases()
        creator = test.creator_claim()
        redemption = test.redeem()
        test.final(opening, recovery, creator, redemption)
        assert r.source_hashes() == sources
        assert all(n.sha((ROOT / p).read_bytes()) == h for p, h in hashes.items())
        r.finish("LOCAL_NATIVE_FEE_LIFECYCLE_PASS")
        print(json.dumps({"status": "LOCAL_NATIVE_FEE_LIFECYCLE_PASS", "output": str(r.output), "VMs": r.vms, "sends": r.sends, "synthetic_airdrop_API_calls": r.synthetic_airdrop_calls, "stage_acceptance": False}))
        return 0
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
        n.persist(r.output / "FAILURE.json", failure)
        r.finish("RETAINED_FEE_LIFECYCLE_FAILURE", failure)
        print(json.dumps({"status": "RETAINED_FEE_LIFECYCLE_FAILURE", "output": str(r.output), **failure}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
