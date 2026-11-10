"""Genuine, isolated native LGE/CPMM bootstrap. No H/locker/old harness execution."""
import argparse
from fractions import Fraction
import math
import time
import traceback

from native_adapter import (
    ROOT, SCOPE_SHA, SYSTEM, TOKEN, T22, ATA, WSOL, AMM, H, RESERVE, RESERVE_BUMP,
    CLOCK, RENT, FEE_RECEIVER, U64_MAX, SUPPLY, NativeRun, Keypair, Pubkey, Account,
    Path, json, struct, sha, utc, persist, public_inputs, serialized, resource_check,
    am, instruction, option, native_transfer, create_account, u64, mint, token, pool,
    account_record,
)

CONTRIBUTIONS = [500_000_000, 1_000_000_000, 2_000_000_000, 3_000_000_000, 4_500_000_000]
ENTITLEMENTS = [250_000_000_000_000_000, 500_000_000_000_000_000, 1_000_000_000_000_000_000,
                1_500_000_000_000_000_000, 2_250_000_000_000_000_000]
TOTAL = 11_000_000_000
POOL_SOL = 8_800_000_000
RESERVE_SOL = 2_200_000_000
POOL_HTFP = 3_500_000_000_000_000_000
TEAM_HTFP = MARKETING_HTFP = 500_000_000_000_000_000
OPS_START = 50_000_000_000
CREATOR_OPERATIONAL_TOPUP = 1_000_000_000
TRADER_OPERATIONAL_SOL = 20_000_000
EPOCH = 7


def ceil_fraction(value):
    return -(-value.numerator // value.denominator)


def fee(amount, rate):
    return ceil_fraction(Fraction(amount * rate, 10_000))


class Rehearsal:
    def __init__(self, run):
        self.r = run
        self.keys = {}
        self.participants = []

    def account(self, name):
        return self.r.svm.get_account(self.keys[name])

    def raw(self, name):
        return bytes(self.account(name).data)

    def amount(self, name):
        return int(token(self.raw(name))["amount"])

    def withheld(self, name):
        return int(token(self.raw(name))["withheld"])

    def track(self, role, key):
        self.keys[role] = self.r.track(role, key)
        return key

    def snapshot_file(self, filename, phase, **extra):
        value = {"schema": "HTFP_LGE_POOL_RAW_PHASE_V1", "phase": phase, "UTC": utc(),
                 "clock_getter": {"epoch": self.r.svm.get_clock().epoch, "slot": self.r.svm.get_clock().slot,
                                  "unix_timestamp": self.r.svm.get_clock().unix_timestamp},
                 "accounts": self.r.snapshot(), "H_present": self.r.svm.get_account(H) is not None, **extra}
        assert value["H_present"] is False
        persist(self.r.output / filename, value)
        return value

    def ata(self, role, owner, mint_key, program):
        key, bump = Pubkey.find_program_address([bytes(owner), bytes(program), bytes(mint_key)], ATA)
        self.track(role, key)
        self.r.send("create_native_ATA_" + role, [instruction(ATA, b"\1", [
            am(self.r.operations.pubkey(), True, True), am(key, True), am(owner), am(mint_key), am(SYSTEM), am(program)])])
        state = token(self.raw(role))
        assert state["mint"] == str(mint_key) and state["authority"] == str(owner) and state["amount"] == "0"
        self.r.emit({"kind": "native_ATA_verified", "role": role, "address": str(key), "bump": bump, "raw_decoded": state})
        return key

    def transfer_token(self, name, source_role, destination_role, amount, authority, rate):
        source_before, destination_before = self.amount(source_role), self.amount(destination_role)
        withholding_before = self.withheld(destination_role)
        ms_before = self.raw("mint")
        row = self.r.send(name, [instruction(T22, bytes([12]) + struct.pack("<QB", amount, 7), [
            am(self.keys[source_role], True), am(self.keys["mint"]), am(self.keys[destination_role], True), am(authority.pubkey(), False, True)])], [authority])
        expected_fee = fee(amount, rate)
        assert self.amount(source_role) == source_before - amount
        assert self.amount(destination_role) == destination_before + amount - expected_fee
        assert self.withheld(destination_role) == withholding_before + expected_fee
        assert self.raw("mint") == ms_before
        proof = {"name": name, "amount": str(amount), "expected_rate_bps": str(rate), "source": source_role,
                 "destination": destination_role, "actual_net": str(self.amount(destination_role) - destination_before),
                 "actual_withheld": str(self.withheld(destination_role) - withholding_before), "transaction_sha256": row["transaction_sha256"]}
        self.r.emit({"kind": "native_transfer_delta_certificate", **proof})
        return proof

    def prepare(self, fixture, native_wsol):
        r = self.r
        self.operations = Keypair()
        self.founder = Keypair()
        self.mint_signer = Keypair()
        self.team, self.marketing = Keypair(), Keypair()
        self.participants = [Keypair() for _ in CONTRIBUTIONS]
        r.operations = self.operations
        for role, kp in [("operations", self.operations), ("founder", self.founder), ("mint", self.mint_signer), ("team", self.team), ("marketing", self.marketing)]:
            self.track(role, kp.pubkey())
        for i, kp in enumerate(self.participants, 1):
            self.track("participant-" + str(i), kp.pubkey())
        self.track("reserve", RESERVE)
        self.track("clock", CLOCK)
        self.track("rent", RENT)
        self.track("wsol_mint", WSOL)
        self.tax_authority = Pubkey.find_program_address([b"htfp-tax-authority", bytes(self.keys["mint"])], H)[0]
        self.track("tax_authority", self.tax_authority)
        assert str(RESERVE) == "33S4fefxDJ9Bz6KmHns37uvwcWSPQnsEyopAZ6YtJpdo" and RESERVE_BUMP == 255
        assert r.svm.get_account(RESERVE) is None
        r.append("SYNTHETIC_SOL_AIRDROP_PROSPECTIVE", address=str(self.operations.pubkey()), lamports=str(OPS_START), purpose="independent operational funding and temporary contributor principal funding")
        before = account_record(self.operations.pubkey(), r.svm.get_account(self.operations.pubkey()))
        result = r.svm.airdrop(self.operations.pubkey(), OPS_START)
        r.synthetic_airdrop_calls += 1
        assert not isinstance(result, Exception)
        assert r.svm.get_balance(self.operations.pubkey()) == OPS_START
        r.emit({"kind": "synthetic_SOL_initialization", "address": str(self.operations.pubkey()), "before": before,
                "after": account_record(self.operations.pubkey(), r.svm.get_account(self.operations.pubkey())), "public_funds": False,
                "airdrop_return_type": type(result).__module__ + "." + type(result).__name__,
                "airdrop_internal_execution_not_an_explicit_signed_send": True})
        mint_rent = r.svm.minimum_balance_for_rent_exemption(82)
        r.svm.set_account(WSOL, Account(mint_rent, native_wsol, TOKEN))
        conf = fixture["raw_config0"]
        config_raw = (ROOT / conf["path"]).read_bytes()
        config_key = Pubkey.find_program_address([b"amm_config", bytes([0, 0])], AMM)[0]
        self.track("amm_config", config_key)
        r.svm.set_account(config_key, Account(r.svm.minimum_balance_for_rent_exemption(len(config_raw)), config_raw, AMM))
        assert len(config_raw) == 236 and u64(config_raw, 12) == 2500 and u64(config_raw, 108) == 2500
        assert u64(config_raw, 20) == 120000 and u64(config_raw, 28) == 40000 and u64(config_raw, 36) == 150000000
        self.track("creation_fee_receiver", FEE_RECEIVER)
        rent = r.svm.minimum_balance_for_rent_exemption(165)
        r.svm.set_account(FEE_RECEIVER, Account(rent, bytes(165), TOKEN))
        r.emit({"kind": "explicit_nonmonetary_dependency_prestate", "before": {"wsol_mint": None, "amm_config": None, "creation_fee_receiver": None},
                "after": {name: r.snapshot()[name] for name in ["wsol_mint", "amm_config", "creation_fee_receiver"]},
                "disclosure": "Static zero-supply nativeSOL mint; unchanged captured config0; zero-filled Token-owned165-byte receiver. Only local rent supplied. No initialized token balances or pool/LP state injected.",
                "network_or_public_control_claim": False})
        self.initial_tracked_lamports = sum(int(value["lamports"]) for value in r.snapshot().values() if value is not None)
        r.send("native_initialize_zero_value_creation_fee_receiver", [instruction(TOKEN, bytes([18]) + bytes(self.founder.pubkey()), [am(FEE_RECEIVER, True), am(WSOL)])])
        assert self.amount("creation_fee_receiver") == 0
        assert self.account("creation_fee_receiver").lamports == rent
        self.t0 = int(time.time())
        self.activation_timestamp = self.t0 + 120
        self.open_time = self.activation_timestamp + 14_400
        r.clock(EPOCH, 100_000, self.t0, "main_E_initial_setup")
        self.identities = {role: str(key) for role, key in sorted(self.keys.items())}
        self.plan = {"scope_sha256": SCOPE_SHA, "LOCAL_TEST_ONLY": True, "decimals": "7", "supply_base_units": str(SUPPLY),
                     "total_contribution_lamports": str(TOTAL),
                     "participants": [{"id": "participant-" + str(i + 1), "contribution_lamports": str(c), "token_base_units": str(n)} for i, (c, n) in enumerate(zip(CONTRIBUTIONS, ENTITLEMENTS))],
                     "token_allocations_base_units": {"participants": str(sum(ENTITLEMENTS)), "pool": str(POOL_HTFP), "team": str(TEAM_HTFP), "marketing": str(MARKETING_HTFP)},
                     "sol_allocations_lamports": {"pool": str(POOL_SOL), "reserve": str(RESERVE_SOL)},
                     "operations": {"initial_synthetic_lamports": str(OPS_START), "creator_topup_lamports": str(CREATOR_OPERATIONAL_TOPUP), "trader_wrap_lamports": str(TRADER_OPERATIONAL_SOL), "contributor_principal_is_not_an_operational_cost": True},
                     "clock": {"E": EPOCH, "initial_unix": self.t0, "synthetic_E_plus_2_unix": self.activation_timestamp, "pool_open_unix": self.open_time, "test_only_margin_seconds": 14_400, "real_network_prediction": False},
                     "fees": {"native_initial_bps": "0", "native_scheduled_bps": "800", "maximum_fee": str(U64_MAX), "ordinary_ppm": "2500", "creator_ppm": "2500", "BothToken": True, "desired_creator_500_proven": False}}
        persist(r.output / "PLAN.json", self.plan)

    def genesis(self):
        r = self.r
        payer = self.operations.pubkey()
        m = self.keys["mint"]
        create = create_account({"from_pubkey": payer, "to_pubkey": m, "lamports": r.svm.minimum_balance_for_rent_exemption(278), "space": 278, "owner": T22})
        init_fee = instruction(T22, bytes([26, 0]) + option(payer) + option(self.tax_authority) + struct.pack("<HQ", 0, U64_MAX), [am(m, True)])
        init_mint = instruction(T22, bytes([20, 7]) + bytes(payer) + option(None), [am(m, True)])
        r.send("native_create_0bps_fee_mint", [create, init_fee, init_mint], [self.mint_signer])
        self.ata("founder_htfp", self.founder.pubkey(), m, T22)
        r.send("native_issue_exact_supply", [instruction(T22, bytes([14]) + struct.pack("<QB", SUPPLY, 7), [am(m, True), am(self.keys["founder_htfp"], True), am(payer, False, True)])])
        schedule = instruction(T22, bytes([26, 5]) + struct.pack("<HQ", 800, U64_MAX), [am(m, True), am(payer, False, True)])
        revoke_fee = instruction(T22, bytes([6, 4]) + option(None), [am(m, True), am(payer, False, True)])
        revoke_mint = instruction(T22, bytes([6, 0]) + option(None), [am(m, True), am(payer, False, True)])
        r.send("native_schedule_E_plus_2_and_revoke", [schedule, revoke_fee, revoke_mint])
        state = mint(self.raw("mint"))
        assert state["supply"] == str(SUPPLY) and state["decimals"] == 7
        assert state["mint_authority_tag"] == state["freeze_authority_tag"] == 0
        assert state["fee_configuration_authority"] == "00" * 32
        assert state["withdraw_authority"] == bytes(self.tax_authority).hex()
        assert state["older"]["bps"] == "0" and state["newer"] == {"epoch": str(EPOCH + 2), "maximum": str(U64_MAX), "bps": "800"}
        assert self.amount("founder_htfp") == SUPPLY and self.withheld("founder_htfp") == 0
        # An actual authority rejection after revocation; no fabricated authority state.
        r.send("revoked_mint_authority_rejects_extra_issuance", [instruction(T22, bytes([14]) + struct.pack("<QB", 1, 7), [am(m, True), am(self.keys["founder_htfp"], True), am(payer, False, True)])], expected_error="Custom(5)")
        self.mint_initialized_bytes = self.raw("mint")
        self.snapshot_file("GENESIS.json", "actual_native_genesis_after_schedule_and_revocation", decoded_mint=state)

    def collect_and_distribute(self):
        r = self.r
        for i, (kp, contribution) in enumerate(zip(self.participants, CONTRIBUTIONS), 1):
            r.send("synthetic_principal_to_participant_" + str(i), [native_transfer(self.operations.pubkey(), kp.pubkey(), contribution)])
            r.send("manual_LGE_collect_participant_" + str(i), [native_transfer(kp.pubkey(), self.founder.pubkey(), contribution)], [kp])
        assert r.svm.get_balance(self.founder.pubkey()) == TOTAL
        assert all((r.svm.get_balance(k.pubkey()) or 0) == 0 for k in self.participants)
        self.snapshot_file("COLLECTED.json", "exact_11_SOL_before_operational_topup")
        r.send("separate_operational_topup_to_pool_creator", [native_transfer(self.operations.pubkey(), self.founder.pubkey(), CREATOR_OPERATIONAL_TOPUP)])
        for i, (kp, amount) in enumerate(zip(self.participants, ENTITLEMENTS), 1):
            role = "participant-" + str(i) + "_htfp"
            self.ata(role, kp.pubkey(), self.keys["mint"], T22)
            self.transfer_token("zero_tax_initial_allocation_" + str(i), "founder_htfp", role, amount, self.founder, 0)
        for role, signer, amount in [("team", self.team, TEAM_HTFP), ("marketing", self.marketing, MARKETING_HTFP)]:
            self.ata(role + "_htfp", signer.pubkey(), self.keys["mint"], T22)
            self.transfer_token("zero_tax_initial_" + role, "founder_htfp", role + "_htfp", amount, self.founder, 0)
        assert self.amount("founder_htfp") == POOL_HTFP
        assert sum(self.amount("participant-" + str(i) + "_htfp") for i in range(1, 6)) == sum(ENTITLEMENTS)
        assert self.amount("team_htfp") == TEAM_HTFP and self.amount("marketing_htfp") == MARKETING_HTFP
        assert all(self.withheld(role) == 0 for role in self.keys if role.endswith("_htfp"))
        assert self.raw("mint") == self.mint_initialized_bytes
        r.send("LGE_twenty_percent_to_canonical_local_reserve", [native_transfer(self.founder.pubkey(), RESERVE, RESERVE_SOL)], [self.founder])
        reserve = self.account("reserve")
        assert reserve.owner == SYSTEM and not reserve.executable and len(reserve.data) == 0 and reserve.lamports == RESERVE_SOL
        self.ata("founder_wsol", self.founder.pubkey(), WSOL, TOKEN)
        r.send("wrap_exact_eighty_percent_LGE_SOL", [native_transfer(self.founder.pubkey(), self.keys["founder_wsol"], POOL_SOL), instruction(TOKEN, bytes([17]), [am(self.keys["founder_wsol"], True)])], [self.founder])
        assert self.amount("founder_wsol") == POOL_SOL
        assert TOTAL == RESERVE_SOL + POOL_SOL
        assert SUPPLY == sum(ENTITLEMENTS) + POOL_HTFP + TEAM_HTFP + MARKETING_HTFP
        self.snapshot_file("DISTRIBUTED.json", "all_initial_allocations_0percent_and_80_20_SOL_before_CPMM", decoded_mint=mint(self.raw("mint")))

    def derive_pool(self):
        self.ordered = sorted([(self.keys["mint"], T22, "founder_htfp", POOL_HTFP), (WSOL, TOKEN, "founder_wsol", POOL_SOL)], key=lambda x: bytes(x[0]))
        self.authority = Pubkey.find_program_address([b"vault_and_lp_mint_auth_seed"], AMM)[0]
        key = Pubkey.find_program_address([b"pool", bytes(self.keys["amm_config"]), bytes(self.ordered[0][0]), bytes(self.ordered[1][0])], AMM)[0]
        self.track("pool", key)
        self.track("lp_mint", Pubkey.find_program_address([b"pool_lp_mint", bytes(key)], AMM)[0])
        self.track("observation", Pubkey.find_program_address([b"observation", bytes(key)], AMM)[0])
        for side, values in enumerate(self.ordered):
            self.track("vault" + str(side), Pubkey.find_program_address([b"pool_vault", bytes(key), bytes(values[0])], AMM)[0])
        self.track("founder_lp", Pubkey.find_program_address([bytes(self.founder.pubkey()), bytes(TOKEN), bytes(self.keys["lp_mint"])], ATA)[0])
        self.htfp_side = 0 if self.ordered[0][0] == self.keys["mint"] else 1

    def initialize(self):
        self.derive_pool()
        r = self.r
        ms_before = self.raw("mint")
        creator_before = self.account("founder").lamports
        specs = [am(self.founder.pubkey(), True, True), am(self.keys["amm_config"]), am(self.authority), am(self.keys["pool"], True),
                 am(self.ordered[0][0]), am(self.ordered[1][0]), am(self.keys["lp_mint"], True),
                 am(self.keys[self.ordered[0][2]], True), am(self.keys[self.ordered[1][2]], True), am(self.keys["founder_lp"], True),
                 am(self.keys["vault0"], True), am(self.keys["vault1"], True), am(FEE_RECEIVER, True), am(self.keys["observation"], True),
                 am(TOKEN), am(self.ordered[0][1]), am(self.ordered[1][1]), am(ATA), am(SYSTEM)]
        wire = bytes.fromhex("4399af27da102620") + struct.pack("<QQQ", self.ordered[0][3], self.ordered[1][3], self.open_time) + bytes([1, 0])
        assert len(wire) == 34
        result = r.send("genuine_CPMM_InitializeV2_BothToken", [instruction(AMM, wire, specs)], [self.founder])
        p = pool(self.raw("pool"))
        assert self.amount("founder_htfp") == self.amount("founder_wsol") == 0
        assert self.raw("mint") == ms_before
        liquidity = math.isqrt(POOL_SOL * POOL_HTFP)
        receipt = liquidity - 100
        assert liquidity == 175499287747842 and receipt == 175499287747742
        assert self.amount("founder_lp") == receipt and u64(self.raw("lp_mint"), 36) == receipt
        assert p["lp_supply"] == str(liquidity) and p["open_time"] == str(self.open_time)
        assert p["creator_fee_on"] == 0 and p["creator_fee_enabled"] == 1
        assert p["creator"] == str(self.founder.pubkey()) and p["config"] == str(self.keys["amm_config"])
        for side, (m, program, _, amount) in enumerate(self.ordered):
            assert p["mint" + str(side)] == str(m) and p["program" + str(side)] == str(program)
            assert p["vault" + str(side)] == str(self.keys["vault" + str(side)])
            assert self.amount("vault" + str(side)) == amount
            assert self.withheld("vault" + str(side)) == 0
        self.lp_receipt = receipt
        self.creation_operational_cost = creator_before - self.account("founder").lamports
        created_rent = sum(r.svm.minimum_balance_for_rent_exemption(len(self.account(role).data)) for role in ["pool", "lp_mint", "founder_lp", "vault0", "vault1", "observation"])
        assert self.creation_operational_cost == 150000000 + created_rent
        assert sum(self.account(role).lamports for role in ["pool", "lp_mint", "founder_lp", "vault0", "vault1", "observation"]) == created_rent + POOL_SOL
        assert self.amount("creation_fee_receiver") == 150000000
        assert self.account("reserve").lamports == RESERVE_SOL
        self.snapshot_file("POOL_INITIALIZED.json", "main_actual_CPMM_pool_35percent_8_8SOL", decoded_pool=p,
                           sqrt_liquidity=str(liquidity), actual_minted_LP=str(receipt), creator_operational_cost=str(self.creation_operational_cost),
                           transaction_sha256=result["transaction_sha256"])

    def swap_instruction(self, htfp_in, amount, minimum=0):
        incoming = self.htfp_side if htfp_in else 1 - self.htfp_side
        outgoing = 1 - incoming
        trader = self.participants[4]
        metas = [am(trader.pubkey(), False, True), am(self.authority), am(self.keys["amm_config"]), am(self.keys["pool"], True),
                 am(self.keys["participant-5_htfp" if htfp_in else "trader_wsol"], True), am(self.keys["trader_wsol" if htfp_in else "participant-5_htfp"], True),
                 am(self.keys["vault" + str(incoming)], True), am(self.keys["vault" + str(outgoing)], True),
                 am(self.ordered[incoming][1]), am(self.ordered[outgoing][1]), am(self.ordered[incoming][0]), am(self.ordered[outgoing][0]), am(self.keys["observation"], True)]
        return instruction(AMM, bytes.fromhex("8fbe5adac41e33de") + struct.pack("<QQ", amount, minimum), metas)

    def checked_swap(self, name, htfp_in, amount, tax_rate):
        r = self.r
        p0 = pool(self.raw("pool"))
        incoming = self.htfp_side if htfp_in else 1 - self.htfp_side
        outgoing = 1 - incoming
        source = "participant-5_htfp" if htfp_in else "trader_wsol"
        dest = "trader_wsol" if htfp_in else "participant-5_htfp"
        vi, vo = "vault" + str(incoming), "vault" + str(outgoing)
        effective = [self.amount("vault" + str(side)) - sum(int(p0[prefix + str(side)]) for prefix in ("protocol", "fund", "creator")) for side in range(2)]
        net_input = amount - (fee(amount, tax_rate) if htfp_in else 0)
        total_fee = ceil_fraction(Fraction(net_input * 5000, 1_000_000))
        creator = int(Fraction(total_fee * 2500, 5000))
        trade = total_fee - creator
        curve_input = net_input - total_fee
        exact_output = Fraction(curve_input * effective[outgoing], effective[incoming] + curve_input)
        gross_output = math.floor(exact_output)
        assert Fraction(gross_output) <= exact_output < gross_output + 1
        output_tax = fee(gross_output, tax_rate) if not htfp_in else 0
        net_output = gross_output - output_tax
        protocol, fund = math.floor(Fraction(trade * 120000, 1_000_000)), math.floor(Fraction(trade * 40000, 1_000_000))
        old = {role: (self.amount(role), self.withheld(role)) for role in (source, dest, vi, vo)}
        before_mint = self.raw("mint")
        result = r.send(name, [self.swap_instruction(htfp_in, amount)], [self.participants[4]])
        assert self.amount(source) == old[source][0] - amount
        assert self.amount(dest) == old[dest][0] + net_output
        assert self.amount(vi) == old[vi][0] + net_input
        assert self.amount(vo) == old[vo][0] - gross_output
        assert self.withheld(vi) == old[vi][1] + (fee(amount, tax_rate) if htfp_in else 0)
        assert self.withheld(dest) == old[dest][1] + output_tax
        assert self.withheld(source) == old[source][1] and self.withheld(vo) == old[vo][1]
        p1 = pool(self.raw("pool"))
        for side in range(2):
            for prefix, delta in [("protocol", protocol), ("fund", fund), ("creator", creator)]:
                assert int(p1[prefix + str(side)]) - int(p0[prefix + str(side)]) == (delta if side == incoming else 0)
        assert creator > 0 and p1["creator_fee_on"] == 0 and p1["creator_fee_enabled"] == 1
        final_effective = [self.amount("vault" + str(side)) - sum(int(p1[prefix + str(side)]) for prefix in ("protocol", "fund", "creator")) for side in range(2)]
        assert final_effective[0] * final_effective[1] >= effective[0] * effective[1]
        assert self.amount("founder_lp") == self.lp_receipt and u64(self.raw("lp_mint"), 36) == self.lp_receipt
        assert self.raw("mint") == before_mint and self.account("reserve").lamports == RESERVE_SOL
        proof = {"name": name, "HTFP_input": htfp_in, "input_side": incoming, "gross_input": str(amount), "input_native_tax": str(amount - net_input),
                 "gross_output": str(gross_output), "output_native_tax": str(output_tax), "net_output": str(net_output),
                 "creator_liability_delta": str(creator), "protocol_liability_delta": str(protocol), "fund_liability_delta": str(fund),
                 "ordinary_trade_fee": str(trade), "effective_before": list(map(str, effective)), "effective_after": list(map(str, final_effective)),
                 "rate_bps": str(tax_rate), "transaction_sha256": result["transaction_sha256"]}
        r.emit({"kind": "raw_delta_swap_certificate", **proof})
        return proof

    def main_checks(self):
        r = self.r
        self.ata("trader_wsol", self.participants[4].pubkey(), WSOL, TOKEN)
        r.send("separate_operational_funding_for_post_allocation_trader", [native_transfer(self.operations.pubkey(), self.keys["trader_wsol"], TRADER_OPERATIONAL_SOL), instruction(TOKEN, bytes([17]), [am(self.keys["trader_wsol"], True)])])
        r.clock(EPOCH + 1, 110_000, self.t0 + 60, "main_E_plus_1_zero_fee")
        e1 = self.transfer_token("E_plus_1_native_fee_still_zero", "participant-1_htfp", "participant-2_htfp", 1001, self.participants[0], 0)
        r.clock(EPOCH + 2, 120_000, self.activation_timestamp, "main_E_plus_2_fee_active_pool_closed")
        e2 = self.transfer_token("E_plus_2_native_fee_800", "participant-1_htfp", "participant-2_htfp", 1001, self.participants[0], 800)
        assert e1["actual_withheld"] == "0" and e2["actual_withheld"] == "81"
        r.clock(EPOCH + 2, 120_001, self.open_time - 1, "main_last_second_before_opening")
        r.send("CPMM_swap_before_timestamp_opening_rejects", [self.swap_instruction(False, 1_000_000)], [self.participants[4]], expected_error=6000)
        r.clock(EPOCH + 2, 120_002, self.open_time, "main_exact_opening_timestamp")
        r.send("CPMM_impossible_minimum_rolls_back", [self.swap_instruction(False, 1_000_000, U64_MAX)], [self.participants[4]], expected_error=6005)
        buy = self.checked_swap("main_at_open_native_buy_800bps", False, 1_000_000, 800)
        sell = self.checked_swap("main_at_open_native_sell_800bps", True, 100_000_000_000_000, 800)
        assert int(buy["output_native_tax"]) > 0 and int(sell["input_native_tax"]) > 0
        assert int(mint(self.raw("mint"))["supply"]) == SUPPLY
        assert self.amount("founder_htfp") == 0
        token_roles = [role for role in self.keys if role.endswith("_htfp")] + ["vault" + str(self.htfp_side)]
        assert len({str(self.keys[role]) for role in token_roles}) == len(token_roles)
        accounted_tokens = sum(self.amount(role) + self.withheld(role) for role in token_roles) + int(mint(self.raw("mint"))["withheld"])
        assert accounted_tokens == SUPPLY
        main_lamports = sum(int(value["lamports"]) for value in r.snapshot().values() if value is not None)
        assert main_lamports + r.fees == self.initial_tracked_lamports
        self.main_final = self.snapshot_file("MAIN_FINAL_SNAPSHOT.json", "main_accepted_before_counterfactual", decoded_pool=pool(self.raw("pool")), decoded_mint=mint(self.raw("mint")))
        self.main_report = {"status": "GENUINE_LOCAL_LGE_CPMM_MAIN_CHECKS_PASS", "stage_acceptance": False,
                            "role": r.role, "H_loaded_or_initialized": False, "pool_is_native_CPMM": True,
                            "allocations": self.plan, "E_plus_1_transfer": e1, "E_plus_2_transfer": e2, "buy": buy, "sell": sell,
                            "initial_LP_receipt": str(self.lp_receipt), "LP_retained_not_BurnAndEarn": True,
                            "main_final_snapshot_sha256": sha((r.output / "MAIN_FINAL_SNAPSHOT.json").read_bytes()),
                            "creator_creation_operational_cost_lamports": str(self.creation_operational_cost),
                            "network_fees_at_main_completion_lamports": str(r.fees), "actual_sends_at_main_completion": r.sends,
                            "raw_conservation": {"tracked_token_roles": token_roles, "spendable_plus_withheld_plus_mint_withheld": str(accounted_tokens), "initial_tracked_lamports": str(self.initial_tracked_lamports), "main_tracked_lamports": str(main_lamports), "network_fees_lamports": str(r.fees)},
                            "limitations": ["historical config2500/2500, final2500/500 unavailable/unproven", "mixed historical captured programs plus bundledATA, synthetic loader", "no H/custody/Recover/Redeem/Process/locker/fullM5/public integration", "clock mapping and4h are synthetic only", "ephemeral local wallet keys never exported"]}
        persist(r.output / "MAIN_ACCEPTANCE.json", self.main_report)
        r.append("MAIN_ACCEPTANCE_SNAPSHOT_FROZEN_BEFORE_COUNTERFACTUAL", snapshot_sha256=self.main_report["main_final_snapshot_sha256"], report_sha256=sha((r.output / "MAIN_ACCEPTANCE.json").read_bytes()))

    def counterfactual(self):
        r = self.r
        r.clock(EPOCH + 1, 120_003, self.open_time + 10, "COUNTERFACTUAL_EPOCH_REWIND_TIMESTAMP_OPEN", counterfactual=True)
        proof = self.checked_swap("counterfactual_open_timestamp_does_not_prove_tax_activation", True, 1_000_000_000_000, 0)
        assert proof["input_native_tax"] == "0" and fee(int(proof["gross_input"]), 800) > 0
        report = {"status": "COUNTERFACTUAL_TIMESTAMP_ONLY_GUARD_OBSERVED", "NON_REAL_BANK_CHRONOLOGY": True,
                  "main_acceptance_snapshot_unchanged": sha((r.output / "MAIN_FINAL_SNAPSHOT.json").read_bytes()) == self.main_report["main_final_snapshot_sha256"],
                  "main_acceptance_report_sha256": sha((r.output / "MAIN_ACCEPTANCE.json").read_bytes()), "proof": proof,
                  "warning": "Explicit synthetic epoch rewind after frozen main acceptance, despite later timestamp/slot. This counterfactual bank is not the main final state or a real-network chronology.", "stage_acceptance": False}
        assert report["main_acceptance_snapshot_unchanged"]
        self.snapshot_file("COUNTERFACTUAL_SNAPSHOT.json", "counterfactual_not_main_final", NON_REAL_BANK_CHRONOLOGY=True)
        persist(r.output / "COUNTERFACTUAL.json", report)


def main():
    parser = argparse.ArgumentParser(description="NEW standalone local native rehearsal; no network")
    parser.add_argument("--role", choices=("author", "supervisor"), default="author")
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    assert args.label and args.label.replace("-", "").replace("_", "").isalnum()
    fixture, codes, input_hashes, ata_raw, native_mint = public_inputs()
    base = ROOT / "evidence/lge_pool" / ("native_author" if args.role == "author" else "native_supervisor")
    r = NativeRun(base / args.label, args.role)
    sources = r.source_hashes()
    try:
        source_root = r.output / "source"
        source_root.mkdir()
        for path, digest in sources.items():
            raw = (ROOT / path).read_bytes()
            assert sha(raw) == digest
            (source_root / Path(path).name).write_bytes(raw)
        persist(r.output / "INPUTS.json", {"scope_sha256": SCOPE_SHA, "sources": sources, "public_inputs": input_hashes,
                                            "provenance": fixture, "ephemeral_signers_exported": False, "stage_acceptance": False})
        r.create_vm(fixture, codes, ata_raw)
        test = Rehearsal(r)
        test.prepare(fixture, native_mint)
        test.genesis()
        test.collect_and_distribute()
        test.initialize()
        test.main_checks()
        test.counterfactual()
        assert sources == r.source_hashes(), "source changed during execution"
        assert all(sha((ROOT / path).read_bytes()) == digest for path, digest in input_hashes.items()), "retained input changed"
        persist(r.output / "IDENTITIES.json", {"roles": {role: str(key) for role, key in sorted(test.keys.items())}, "token0_is_HTFP": test.htfp_side == 0,
                                               "operations_wallet_is_separate": test.operations.pubkey() != test.founder.pubkey(), "ephemeral_signing_material_exported": False})
        r.finish("GENUINE_LOCAL_LGE_CPMM_REHEARSAL_PASS")
        print(json.dumps({"status": "GENUINE_LOCAL_LGE_CPMM_REHEARSAL_PASS", "output": str(r.output), "VMs": r.vms, "sends": r.sends, "stage_acceptance": False}))
        return 0
    except BaseException as exc:
        failure = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        persist(r.output / "FAILURE.json", failure)
        r.finish("RETAINED_NATIVE_REHEARSAL_FAILURE", failure)
        print(json.dumps({"status": "RETAINED_NATIVE_REHEARSAL_FAILURE", "output": str(r.output), **failure}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
