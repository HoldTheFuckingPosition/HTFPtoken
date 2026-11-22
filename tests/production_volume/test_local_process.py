"""Exercise only changed sale-policy behavior on the retained offline CPMM stack."""

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory

from solders import solders as native
from solders.account import Account
from solders.compute_budget import set_compute_unit_limit
from solders.message import Message
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import Transaction

from prepare_profile import pinned, production_preimage


FIXTURE_FILES = {
    "fixture-profile.json": "76f15e79536a794b50ea59ed3e942ba3562c8f69e7a354611f817416cf497be5",
    "chain-config.bin": "be8d13d1a6def925af32187937fde9ef21d2d7ca5efb1c6e1fd6611b3f12cfe1",
}
PROTECTED = (
    "config", "inventory", "volume", "mint", "custody", "reserve", "pool",
    "vault_htfp", "vault_wsol", "observation", "amm_config", "wsol_mint",
)
ROLES = (
    "config", "inventory", "volume", "mint", "custody", "tax_authority", "reserve",
    "temp", "settle_authority", "payer", "token2022", "legacy_token", "wsol_mint",
    "system", "instructions_sysvar", "amm", "amm_config", "amm_authority", "pool",
    "vault_htfp", "vault_wsol", "observation",
)
WRITABLE = {
    "inventory", "volume", "mint", "custody", "reserve", "temp", "payer",
    "pool", "vault_htfp", "vault_wsol", "observation",
}


class FixturePayer:
    """Use an on-curve public identifier without any private-key operation."""

    def pubkey(self):
        for candidate in range(256):
            key = Pubkey.from_bytes(sha256(b"HTFP local fixture" + bytes([candidate])).digest())
            if key.is_on_curve():
                return key
        raise ValueError("No on-curve fixture address")


def load_fixture(root, scratch, elf):
    pinned(Path(native.__file__), "648e13d02ec2e8555d751e38980e01faa5cbb47c2e7d7262f3a2103caa3afa02")
    for name, digest in FIXTURE_FILES.items():
        (scratch / name).write_bytes(pinned(root / name, digest))
    profile = json.loads((scratch / "fixture-profile.json").read_bytes())
    pinned(Path(profile["fixture_accounts_origin"]),
           "61a786cf239834c22bb72b2b6c0e4096c3401478a00a8cdeceab3f179a07c033")
    (scratch / "local-only-htfp-2500-500.so").symlink_to(elf)
    runner = root / "validate-local.py"
    pinned(runner, "bb9f44d23ace51b791353666e7646c8c6d96fe1fecdb85167990788caf609224")
    spec = importlib.util.spec_from_file_location("retained_cpmm_fixture", runner)
    retained = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retained)
    retained.ROOT = scratch
    retained.P = root / "mainnet-read-002"
    retained.Keypair = FixturePayer
    commitment = sha256(production_preimage(root)).digest()

    class Fixture(retained.Fixture):
        def __init__(self):
            super().__init__()
            # Zero-signature fixtures share the runtime's history key. The
            # program's own sequence and instruction fence still run.
            self.vm.with_sigverify(False).with_transaction_history(0)
            self.ordinal = 0
            init = self.op("program", retained.PREFIX + b"\x04",
                           ("config", "inventory", "volume", "payer", "system"),
                           {"inventory", "volume", "payer"}, {"payer"})
            self.execute([init])
            assert self.raw("volume")[:10] == b"HTFPVOL2\x02\x00"
            assert self.raw("volume")[11:59] == commitment + bytes(16)

        def load(self, role, owner=None, body=lambda value: value):
            if role != "volume":  # Use the candidate's real initialization.
                super().load(role, owner, body)

        def change_data(self, role, data):
            old = self.account(role)
            self.install(role, Account(old.lamports, data, old.owner, old.executable, old.rent_epoch))

        def set_reserve(self, reserve):
            before = self.reserves()
            current = retained.amount(before["htfp"])
            self.change_data("vault_htfp", retained.u64(before["htfp"], 64, current - before["x1"] + reserve))

        def set_inventory(self, q):
            self.change_data("custody", retained.u64(self.raw("custody"), 64, q))
            self.change_data("inventory", retained.u64(self.raw("inventory"), 12, q))

        def execute(self, instructions, expected_error=None):
            self.ordinal += 1
            instructions = [set_compute_unit_limit(1_100_000 + self.ordinal), *instructions]
            message = Message.new_with_blockhash(instructions, self.k["payer"], self.vm.latest_blockhash())
            packet = Transaction.populate(message, [Signature.default()])
            assert len(bytes(packet)) <= 1232
            result = self.vm.send_transaction(packet)
            if expected_error is None:
                assert hasattr(result, "compute_units_consumed"), str(result)
                return {"units": result.compute_units_consumed(), "packet_bytes": len(bytes(packet))}
            assert not hasattr(result, "compute_units_consumed"), str(result)
            assert f"Custom({expected_error})" in str(result), str(result)
            return result

        def instructions_for(self, quantities, finalize=True, nonce=None):
            sequence = retained.amount(self.raw("volume"), 59)
            operations, temporaries = [], []
            for offset, quantity in enumerate(quantities):
                temporary = Pubkey.find_program_address(
                    [b"htfp-tmp-wsol", bytes(self.k["mint"]), struct.pack("<Q", sequence + offset)],
                    self.k["program"],
                )[0]
                self.k["temp"] = temporary
                temporaries.append(temporary)
                operations.append(self.op("program", retained.PREFIX + b"\x03" + struct.pack("<Q", quantity),
                                          ROLES, WRITABLE, {"payer"}))
            if finalize:
                operations.append(self.op(
                    "program", retained.PREFIX + b"\x05" + struct.pack("<Q", sequence + 1 if nonce is None else nonce),
                    ("config", "inventory", "volume", "instructions_sysvar"), {"inventory", "volume"},
                ))
            return operations, temporaries

        def assert_closed(self, keys):
            for key in keys:
                account = self.vm.get_account(key)
                assert account is None or (account.lamports == 0 and account.data == b"" and
                                           account.owner == Pubkey.default())

        def refusal(self, quantities, error, finalize=True, nonce=None):
            saved = {role: self.account(role) for role in PROTECTED}
            payer = self.account("payer").lamports
            instructions, keys = self.instructions_for(quantities, finalize, nonce)
            result = self.execute(instructions, error)
            assert {role: self.account(role) for role in PROTECTED} == saved
            assert payer - self.account("payer").lamports == 5000
            self.assert_closed(keys)
            return result

        def success(self, quotes, quantities):
            pool = self.reserves()
            volume, mint, custody, inventory = map(self.raw, ("volume", "mint", "custody", "inventory"))
            start = retained.amount(volume, 59)
            payer, reserve = (self.account(role).lamports for role in ("payer", "reserve"))
            instructions, keys = self.instructions_for(quantities)
            metrics = self.execute(instructions)
            combined = {key: sum(quote[key] for quote in quotes) for key in (
                "pool_input", "curve_out", "htfp_withheld_in", "protocol", "fund",
                "creator", "curve_input", "liquidity",
            )}
            self.check_pool(pool, {"in_side": 1, **combined})
            total = sum(quantities)
            assert self.raw("mint") == retained.u64(mint, 36, retained.amount(mint, 36) - total // 8 * 3)
            assert self.raw("custody") == retained.u64(custody, 64, retained.amount(custody) - total)
            assert self.raw("inventory") == retained.u64(inventory, 12, retained.amount(inventory, 12) - total)
            assert self.raw("volume") == retained.u64(volume, 59, start + len(quantities))
            assert self.account("reserve").lamports - reserve == combined["curve_out"]
            assert payer - self.account("payer").lamports == 5000
            self.assert_closed(keys)
            return metrics

    return Fixture, retained


def run(root, elf):
    with TemporaryDirectory(prefix="htfp-production-volume-") as temp:
        Fixture, retained = load_fixture(root, Path(temp), elf)
        batched = Fixture()
        x = batched.reserves()["x1"] // 500 * 500
        y = batched.reserves()["x0"]
        gross = x // 100
        first = retained.quote(gross, 1, x, y)
        after_x = x + first["curve_input"] + first["liquidity"]
        after_y = y - first["curve_out"]
        second_gross = after_x // 500 * 5
        second = retained.quote(second_gross, 1, after_x, after_y)
        q1, q2 = gross // 5 * 8, second_gross // 5 * 8
        assert second_gross > gross
        batched.set_inventory(q1 + q2 + 8)
        batched.set_reserve(x - 1)
        assert gross == batched.reserves()["x1"] // 100 + 1
        assert first["pool_input"] <= batched.reserves()["x1"] // 100
        batched.refusal([q1], 7020)
        batched.set_reserve(x)
        batched.refusal([q1], 7021, finalize=False)
        rollback = batched.refusal([q1, q2 + 8], 7020)
        assert "HTFP Process close" in str(rollback)
        same_message = batched.success([first, second], [q1, q2])
        batched.refusal([8], 7021, nonce=1)

        sequential = Fixture()
        sequential.set_reserve(x)
        sequential.set_inventory(q1 + q2)
        original_clock = sequential.vm.get_clock()
        first_metrics = sequential.success([first], [q1])
        second_metrics = sequential.success([second], [q2])
        assert sequential.vm.get_clock() == original_clock
        sequential.refusal([8], 7006)

        layout = Fixture()
        layout.set_inventory(q1)
        volume = layout.raw("volume")
        layout.change_data("volume", retained.u64(volume, 43, 1))
        layout.refusal([q1], 7019)
        layout.change_data("volume", b"HTFPVOL1\x01\x00" + volume[10:])
        layout.refusal([q1], 7019)

        return {
            "status": "PASS_ISOLATED_PRODUCTION_VOLUME_POLICY",
            "candidate_sha256": sha256(elf.read_bytes()).hexdigest(),
            "signatures_generated": 0,
            "cases": {
                "floor_plus_one_with_net_under_limit_refused": True,
                "missing_finalize_refused": True,
                "stale_finalize_nonce_refused": True,
                "failed_later_call_rolled_back_first_settlement": True,
                "same_message_one_finalize_updated_reserve": same_message,
                "same_clock_separate_calls": [first_metrics, second_metrics],
                "inventory_exhaustion_refused": True,
                "nonzero_reserved_and_legacy_header_refused": True,
            },
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.fixture_root.resolve(), args.candidate.resolve()), indent=2))
