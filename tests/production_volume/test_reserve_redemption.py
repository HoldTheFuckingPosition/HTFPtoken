"""Exercise fresh reserve funding and Redeem in the exact production-policy SBF.

The retained mint extensions and Token-2022 image are authenticated offline.
Supply and holder balances are explicit local genesis fixture inputs.
"""

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import struct

from solders.account import Account
from solders.compute_budget import set_compute_unit_limit
from solders.instruction import AccountMeta, Instruction
from solders.litesvm import LiteSVM
from solders.message import Message
from solders.pubkey import Pubkey
from solders.rent import Rent
from solders.signature import Signature
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction

from prepare_profile import pinned


PREFIX = b"HTFP\x01"
SUPPLY = 10_000_000_000_000_000_000
SYSTEM = Pubkey.default()
ORIGINAL_RATE = 5080
PREFUND = 2_000_003
RECORD_HEADER = b"HTFPRNT1"
FEE = 5_000


def data(row):
    return base64.b64decode(row["data"][0], validate=True)


def replace_u64(raw, offset, value):
    return raw[:offset] + struct.pack("<Q", value) + raw[offset + 8:]


class Scenario:
    def __init__(self, fixture, candidate, candidate_hash):
        profile = json.loads(pinned(fixture / "fixture-profile.json",
            "76f15e79536a794b50ea59ed3e942ba3562c8f69e7a354611f817416cf497be5"))
        original = json.loads(pinned(Path(profile["fixture_accounts_origin"]),
            "61a786cf239834c22bb72b2b6c0e4096c3401478a00a8cdeceab3f179a07c033"))
        self.k = {role: Pubkey.from_string(address) for role, address in profile["identities"].items()}
        self.k["payee"] = Pubkey.from_bytes(sha256(b"HTFP local redemption recipient").digest())
        self.k["storage"], self.bump = Pubkey.find_program_address(
            [b"htfp-reserve-storage", bytes(self.k["mint"])], self.k["program"])
        self.vm = LiteSVM().with_sigverify(False).with_transaction_history(0).with_log_bytes_limit(None)
        self.vm.add_program(self.k["program"], pinned(candidate, candidate_hash))
        native = profile["mainnet_cpi_images"]["token2022"]
        token_program = pinned(fixture / "mainnet-read-002/mainnet-token2022.payload.so", native["payload_sha256"])
        assert len(token_program) == native["capacity"]
        self.vm.add_program(self.k["token2022"], token_program)
        self.rent_rate(ORIGINAL_RATE)

        mint = data(original["mint"])
        assert mint[166:170] == struct.pack("<HH", 1, 108)
        mint = replace_u64(replace_u64(mint, 36, SUPPLY), 234, 0)
        custody = data(original["custody"])
        assert custody[:32] == bytes(self.k["mint"]) and custody[166:170] == struct.pack("<HH", 2, 8)
        holder = custody[:32] + bytes(self.k["genesis_owner"]) + custody[64:]
        holder = replace_u64(replace_u64(holder, 64, SUPPLY), 170, 0)
        self.put("mint", 10_000_000, mint, self.k["token2022"])
        self.put("genesis_holding", 10_000_000, holder, self.k["token2022"])
        self.put("initializer", 50_000_000)
        self.put("payee", 10_000_000)
        self.put("reserve", PREFUND)
        self.original_config = data(original["config"])
        self.transcript = []

    def rent_rate(self, rate):
        self.vm.set_rent(Rent(rate, 1.0, 50))
        assert self.vm.get_rent() == Rent(rate, 1.0, 50)
        assert self.vm.minimum_balance_for_rent_exemption(0) == rate * 128

    def put(self, role, lamports, body=b"", owner=SYSTEM):
        self.vm.set_account(self.k[role], Account(lamports, body, owner, False, 0))

    def account(self, role):
        return self.vm.get_account(self.k[role])

    def balance(self, role):
        return self.account(role).lamports

    def snapshot(self):
        return {role: self.account(role) for role in (
            "initializer", "payee", "reserve", "storage", "config", "inventory",
            "mint", "genesis_holding", "custody")}

    def instruction(self, suffix, roles, writable, signers):
        return Instruction(self.k["program"], PREFIX + suffix,
            [AccountMeta(self.k[role], role in signers, role in writable) for role in roles])

    def init(self):
        return self.instruction(bytes([0]),
            ("config", "inventory", "mint", "custody", "tax_authority", "reserve", "genesis_holding",
             "initializer", "token2022", "system", "storage"),
            {"config", "inventory", "custody", "reserve", "initializer", "storage"}, {"initializer"})

    def redeem(self, amount, minimum):
        return self.instruction(bytes([2]) + struct.pack("<QQ", amount, minimum) + bytes(self.k["payee"]) + bytes(2),
            ("config", "inventory", "mint", "genesis_holding", "reserve", "payee", "initializer",
             "token2022", "system", "storage"),
            {"inventory", "mint", "genesis_holding", "reserve", "payee"}, {"initializer"})

    def send(self, label, instructions, error=None, successful_burn_before_failure=False):
        instructions = [set_compute_unit_limit(400_000), *instructions]
        message = Message.new_with_blockhash(instructions, self.k["initializer"], self.vm.latest_blockhash())
        assert message.header.num_required_signatures == 1
        packet = Transaction.populate(message, [Signature.default()])
        result = self.vm.send_transaction(packet)
        if error is None:
            assert hasattr(result, "compute_units_consumed"), str(result)
            detail = {"compute_units": result.compute_units_consumed()}
        else:
            assert not hasattr(result, "compute_units_consumed") and f"Custom({error})" in str(result), str(result)
            if successful_burn_before_failure:
                logs = result.meta().logs()
                assert any("burn authorized redemption" in line for line in logs), logs
                assert any("native redemption payout" in line for line in logs), logs
            detail = {"expected_error": error}
        self.transcript.append({"check": label, "wire_bytes": len(bytes(packet)), **detail})

    def rejects(self, label, instructions, error, **options):
        before = self.snapshot()
        self.send(label, instructions, error, **options)
        for role, account in before.items():
            if role == "initializer":
                assert self.balance(role) == account.lamports - FEE
            else:
                assert self.account(role) == account, role

    def donate(self, amount):
        old = self.balance("reserve")
        storage = self.account("storage")
        self.send("ordinary SOL donation", [transfer(TransferParams(
            from_pubkey=self.k["initializer"], to_pubkey=self.k["reserve"], lamports=amount))])
        assert self.balance("reserve") == old + amount and self.account("storage") == storage

    def payout(self, rate, amount, supply, economic, storage):
        self.rent_rate(rate)
        want = economic * amount // supply
        payee, payer = self.balance("payee"), self.balance("initializer")
        self.send(f"payment at rate {rate}", [self.redeem(amount, want)])
        assert self.balance("payee") == payee + want and self.balance("initializer") == payer - FEE
        assert self.balance("reserve") == storage + economic - want
        assert struct.unpack_from("<Q", self.account("mint").data, 36)[0] == supply - amount
        assert struct.unpack_from("<Q", self.account("genesis_holding").data, 64)[0] == supply - amount
        assert self.account("inventory").data[11] == 0
        return supply - amount, economic - want


def run(fixture, candidate, candidate_hash):
    vm = Scenario(fixture, candidate, candidate_hash)
    original_funding = vm.balance("initializer")
    vm.send("fresh initialization with independently retained economic prefund", [vm.init()])
    seeded = vm.vm.minimum_balance_for_rent_exemption(0)
    record = vm.account("storage")
    assert record.owner == vm.k["program"] and record.data == RECORD_HEADER + bytes([vm.bump]) + struct.pack("<Q", seeded)
    assert vm.balance("reserve") == PREFUND + seeded
    assert original_funding - vm.balance("initializer") == FEE + seeded + sum(
        vm.vm.minimum_balance_for_rent_exemption(size) for size in (175, 20, 178, 17))
    vm.rejects("repeat initializer", [vm.init()], 7017)

    legacy = Scenario(fixture, candidate, candidate_hash)
    legacy.put("config", 10_000_000, legacy.original_config, legacy.k["program"])
    legacy.rejects("occupied legacy Config cannot initialize storage", [legacy.init()], 7017)

    vm.donate(1_000_004)
    supply, economic = SUPPLY, PREFUND + 1_000_004
    vm.rejects("rounding to zero burns nothing", [vm.redeem(1, 0)], 7008)
    good_amount = supply // 4
    vm.rejects("minimum plus one burns nothing", [vm.redeem(good_amount, economic * good_amount // supply + 1)], 7009)
    vm.rejects("late ordinary minimum failure rolls back first burn and transfer",
        [vm.redeem(good_amount, 1), vm.redeem(good_amount, economic + 1)], 7009,
        successful_burn_before_failure=True)
    for rate in (5080, 2575, 1322, 4800):
        supply, economic = vm.payout(rate, supply // 7, supply, economic, seeded)
        assert vm.account("storage") == record

    vm.rent_rate(6960)
    assert vm.balance("reserve") > vm.vm.minimum_balance_for_rent_exemption(0)
    vm.rejects("account can be rent-exempt while technical funding is inadequate", [vm.redeem(supply, 1)], 7028)
    vm.rent_rate(1322)
    saved = vm.account("reserve")
    vm.put("reserve", seeded - 1)
    vm.rejects("actual technical balance deficit", [vm.redeem(supply, 1)], 7029)
    vm.vm.set_account(vm.k["reserve"], saved)
    supply, economic = vm.payout(1322, supply, supply, economic, seeded)
    assert (supply, economic, vm.balance("reserve")) == (0, 0, seeded)
    vm.donate(12_345)
    vm.rejects("new receipts are immobilized after terminal burn", [vm.redeem(1, 1)], 7007)
    assert vm.account("storage") == record and vm.balance("reserve") == seeded + 12_345
    return {"elf_sha256": candidate_hash, "starting_storage": seeded,
        "profile": "Production-volume policy with retained local market and Token-2022 bindings",
        "tests": [*legacy.transcript, *vm.transcript]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.fixture_root, args.candidate, args.sha256), indent=2))
