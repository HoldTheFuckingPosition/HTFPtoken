"""Run the new reserve sponsor paths against a sealed, local HTFP V2 ELF."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

from solders.compute_budget import set_compute_unit_limit
from solders.message import Message
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction

from test_reserve_redemption import FEE, PREFUND, SUPPLY, Scenario, replace_u64


class SponsorScenario(Scenario):
    def __init__(self, fixture, candidate, candidate_hash):
        super().__init__(fixture, candidate, candidate_hash)
        for role, balance in (("sponsor", 10_000_000), ("other_sponsor", 10_000_000),
                              ("short_sponsor", 10_000)):
            self.k[role] = Pubkey.from_bytes(sha256(("HTFP local " + role).encode()).digest())
            self.put(role, balance)

    def snapshot(self):
        return super().snapshot() | {
            role: self.account(role) for role in ("sponsor", "other_sponsor", "short_sponsor")
        }

    def top_up(self, technical, amount, payer="sponsor", signed=True, record="storage"):
        return self.instruction(bytes([7]) + struct.pack("<QQ", technical, amount),
            (payer, "reserve", record, "system"), {payer, "reserve", record}, {payer} if signed else set())

    def send(self, label, instructions, error=None, system_cpi_before_failure=False):
        message = Message.new_with_blockhash(
            [set_compute_unit_limit(400_000), *instructions],
            self.k["initializer"], self.vm.latest_blockhash(),
        )
        signers = message.header.num_required_signatures
        packet = Transaction.populate(message, [Signature.default()] * signers)
        result = self.vm.send_transaction(packet)
        detail = {"check": label, "wire_bytes": len(bytes(packet)), "fixture_fee": FEE * signers}
        if error is None:
            assert hasattr(result, "compute_units_consumed"), str(result)
            detail["compute_units"] = result.compute_units_consumed()
        else:
            assert not hasattr(result, "compute_units_consumed") and f"Custom({error})" in str(result), str(result)
            logs = result.meta().logs()
            assert not any("burn authorized redemption" in line for line in logs), logs
            system_success = "Program 11111111111111111111111111111111 success" in logs
            assert system_success == system_cpi_before_failure, logs
            detail.update(expected_error=error, system_cpi_rolled_back=system_success)
        self.transcript.append(detail)
        return FEE * signers

    def check_transition(self, before, fee, lamport_deltas=None, byte_updates=None):
        deltas = (lamport_deltas or {}) | {"initializer": -fee}
        byte_updates = byte_updates or {}
        for role, old in before.items():
            new = self.account(role)
            assert new.lamports == old.lamports + deltas.get(role, 0), role
            assert new.data == byte_updates.get(role, old.data), role
            assert (new.owner, new.executable) == (old.owner, old.executable), role

    def rejects(self, label, instructions, error, **options):
        before = self.snapshot()
        fee = self.send(label, instructions, error, **options)
        self.check_transition(before, fee)

    def floor(self, rate):
        self.rent_rate(rate)
        return self.vm.get_rent().minimum_balance(0)


def run(fixture, candidate, candidate_hash):
    state = SponsorScenario(fixture, candidate, candidate_hash)
    state.send("native fresh initialization", [state.init()])
    technical = state.vm.get_rent().minimum_balance(0)
    assert state.balance("reserve") == technical + PREFUND
    assert struct.unpack_from("<Q", state.account("storage").data, 9)[0] == technical
    state.rejects("already covered, zero top-up", [state.top_up(technical, 0)], 7030)

    first_floor = state.floor(6000)
    gap = first_floor - technical
    state.rejects("rent rise initially blocks redemption before burn", [state.redeem(SUPPLY, 1)], 7028)
    state.donate(99_911)
    economic = PREFUND + 99_911
    assert state.balance("reserve") - technical == economic
    state.rejects("ordinary donation does not cure the technical gap", [state.redeem(SUPPLY, 1)], 7028)
    state.rejects("sponsor missing its signature", [state.top_up(technical, gap, signed=False)], 7005)
    state.rejects("mismatched record", [state.top_up(technical, gap, record="payee")], 7027)
    state.rejects("underquoted top-up", [state.top_up(technical, gap - 1)], 7030)
    state.rejects("overquoted top-up", [state.top_up(technical, gap + 1)], 7030)
    state.rejects("underfunded sponsor", [state.top_up(technical, gap, "short_sponsor")], 7031)

    first_quote = state.top_up(technical, gap)
    competing_quote = state.top_up(technical, gap, "other_sponsor")
    before = state.snapshot()
    fee = state.send("first external payer funds the exact shortfall", [first_quote])
    state.check_transition(before, fee, {"sponsor": -gap, "reserve": gap},
        {"storage": replace_u64(before["storage"].data, 9, first_floor)})
    assert state.balance("reserve") - first_floor == economic
    state.rejects("competing sponsor loses the funding race", [competing_quote], 7030)
    state.rejects("repeated top-up by the successful payer", [first_quote], 7030)

    assert state.floor(2575) < first_floor
    state.donate(678_901)
    economic += 678_901
    spent = SUPPLY // 7
    payout = economic * spent // SUPPLY
    before = state.snapshot()
    fee = state.send("rounded redemption after lower rent and genuine receipt", [state.redeem(spent, payout)])
    remaining = SUPPLY - spent
    state.check_transition(before, fee, {"reserve": -payout, "payee": payout}, {
        "mint": replace_u64(before["mint"].data, 36, remaining),
        "genesis_holding": replace_u64(before["genesis_holding"].data, 64, remaining),
    })
    economic -= payout
    assert state.balance("reserve") - first_floor == economic

    second_floor = state.floor(6920)
    assert second_floor - first_floor == gap
    state.rejects("same amount at a later rise with an obsolete recorded basis", [first_quote], 7030)
    second_quote = state.top_up(first_floor, gap, "other_sponsor")
    state.rejects("later minimum failure rolls back a successful System top-up",
        [second_quote, state.redeem(remaining, economic + 1)], 7009, system_cpi_before_failure=True)

    before = state.snapshot()
    fee = state.send("fresh sponsored increase and full-supply redemption settle atomically",
        [second_quote, state.redeem(remaining, economic)])
    state.check_transition(before, fee, {"other_sponsor": -gap, "reserve": gap - economic, "payee": economic}, {
        "storage": replace_u64(before["storage"].data, 9, second_floor),
        "mint": replace_u64(before["mint"].data, 36, 0),
        "genesis_holding": replace_u64(before["genesis_holding"].data, 64, 0),
    })
    assert state.balance("reserve") == second_floor
    return {
        "elf_sha256": candidate_hash,
        "initial_technical_reserve": technical,
        "first_technical_reserve": first_floor,
        "terminal_technical_reserve": second_floor,
        "each_top_up": gap,
        "partial_and_full_redemption": [payout, economic],
        "tests": state.transcript,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.fixture_root, args.candidate, args.sha256), indent=2))
