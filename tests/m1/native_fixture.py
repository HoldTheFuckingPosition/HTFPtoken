"""Bundled local Token-2022 runtime harness; no RPC or custom HTFP program.

Wire/layout references are the preserved official research sources under
evidence/m1/sources/ at 486240c69e8ee3a8ac7cdaa24011052386cb872c.
Their match to the bundled ELF is UNKNOWN. Successful native readback is tested.
"""
import hashlib
import struct

from solders.clock import Clock
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.litesvm import LiteSVM
from solders.pubkey import Pubkey
from solders.system_program import CreateAccountParams, create_account
from solders.token.state import Mint, TokenAccount
from solders.transaction import Transaction
from solders.transaction_metadata import FailedTransactionMetadata

from models.monetary import DECIMALS, INITIAL_SUPPLY, U64_MAX

TOKEN_2022 = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
EXPECTED_ELF_SHA256 = "47181a65d6ee7d7a100480db2efaa21fcfff2be1af49155c30975e9fe5c0c9d6"
MINT_LEN = 166 + 4 + 108
TOKEN_LEN = 166 + 4 + 8
EVENTS = []


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def exact_json(value):
    """All integer values become decimal strings, including values >2**53."""
    if type(value) is int:
        return str(value)
    if isinstance(value, dict):
        return {str(k): exact_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(v) for v in value]
    return value


def meta(key, signer=False, writable=False):
    return AccountMeta(key, signer, writable)


def native(data, accounts):
    return Instruction(TOKEN_2022, data, accounts)


def option_key(pubkey):
    # instruction.rs pack_pubkey_option: u8 tag, unlike base-state u32 COption.
    return b"\0" if pubkey is None else b"\1" + bytes(pubkey)


def set_fee(mint, authority, bps=800, maximum=U64_MAX, signer=True):
    # TokenInstruction::TransferFeeExtension=26; TransferFeeInstruction::Set=5.
    return native(bytes([26, 5]) + struct.pack("<HQ", bps, maximum),
                  [meta(mint, writable=True), meta(authority, signer)])


def revoke(mint, authority, authority_type):
    # instruction.rs SetAuthority=6; MintTokens=0, TransferFeeConfig=4.
    return native(bytes([6, authority_type]) + option_key(None),
                  [meta(mint, writable=True), meta(authority, True)])


def mint_to(mint, destination, authority, amount):
    return native(bytes([14]) + struct.pack("<QB", amount, DECIMALS),
                  [meta(mint, writable=True), meta(destination, writable=True),
                   meta(authority, True)])


def transfer(source, mint, destination, owner, amount, fee, signer=True):
    # transfer_fee/instruction.rs TransferCheckedWithFee=1 under prefix 26.
    return native(bytes([26, 1]) + struct.pack("<QBQ", amount, DECIMALS, fee),
                  [meta(source, writable=True), meta(mint),
                   meta(destination, writable=True), meta(owner, signer)])


def burn(source, mint, owner, amount):
    return native(bytes([15]) + struct.pack("<QB", amount, DECIMALS),
                  [meta(source, writable=True), meta(mint, writable=True), meta(owner, True)])


def extensions(data, account_type):
    # extension/mod.rs: base165 + type1 + repeated u16 type/u16 len/value.
    if len(data) < 166 or data[165] != account_type:
        raise ValueError("unexpected account type or length")
    result, cursor = {}, 166
    while cursor < len(data):
        if cursor + 4 > len(data):
            raise ValueError("truncated TLV header")
        tag, size = struct.unpack_from("<HH", data, cursor)
        cursor += 4
        if tag == 0 and size == 0 and not any(data[cursor:]):
            break
        if tag in result or cursor + size > len(data):
            raise ValueError("duplicate or truncated extension")
        result[tag] = data[cursor:cursor + size]
        cursor += size
    return result


def mint_state(account):
    data = bytes(account.data)
    if account.owner != TOKEN_2022 or len(data) != MINT_LEN or any(data[82:165]):
        raise ValueError("wrong mint identity/length/padding")
    base = Mint.from_bytes(data[:82])
    ext = extensions(data, 1)
    if set(ext) != {1} or len(ext[1]) != 108:
        raise ValueError("unexpected mint extension contract")
    fee = ext[1]
    def rate(offset):
        epoch, maximum, bps = struct.unpack_from("<QQH", fee, offset)
        return {"epoch": epoch, "maximum_fee": maximum, "bps": bps}
    return {"supply": base.supply, "decimals": base.decimals,
            "is_initialized": base.is_initialized,
            "mint_authority": None if base.mint_authority is None else str(base.mint_authority),
            "freeze_authority": None if base.freeze_authority is None else str(base.freeze_authority),
            "fee_authority": None if fee[:32] == bytes(32) else str(Pubkey.from_bytes(fee[:32])),
            "withdraw_authority": None if fee[32:64] == bytes(32) else str(Pubkey.from_bytes(fee[32:64])),
            "mint_withheld": struct.unpack_from("<Q", fee, 64)[0],
            "older": rate(72), "newer": rate(90)}


def token_state(account):
    data = bytes(account.data)
    if account.owner != TOKEN_2022 or len(data) != TOKEN_LEN:
        raise ValueError("wrong token account identity/length")
    base = TokenAccount.from_bytes(data[:165])
    ext = extensions(data, 2)
    if set(ext) != {2} or len(ext[2]) != 8:
        raise ValueError("unexpected token extension contract")
    return {"mint": str(base.mint), "owner": str(base.owner),
            "spendable": base.amount, "withheld": struct.unpack("<Q", ext[2])[0]}


def account_deltas(before, after):
    result = {}
    for role, new in after.items():
        old = before[role]
        if old is None or new is None:
            result[role] = {"created": old is None and new is not None,
                            "closed": old is not None and new is None}
            continue
        delta = {"lamports": new["lamports"] - old["lamports"],
                 "data_unchanged": new["data_hex"] == old["data_hex"]}
        for key in ("supply", "spendable", "withheld", "mint_withheld"):
            if key in new["decoded"]:
                delta[key] = new["decoded"][key] - old["decoded"][key]
        result[role] = delta
    return result


class NativeFixture:
    def __init__(self, label, issuance=INITIAL_SUPPLY):
        self.label = label
        # Use the working installed constructor, not default().with_spl_programs().
        self.svm = LiteSVM()
        program = self.svm.get_account(TOKEN_2022)
        assert program is not None and program.executable
        assert str(program.owner) == "BPFLoader2111111111111111111111111111111111"
        assert len(program.data) == 535256
        assert bytes(program.data)[:4] == b"\x7fELF"
        assert sha256(bytes(program.data)) == EXPECTED_ELF_SHA256
        self.payer, self.authority, self.withdraw, self.minter, self.holder = [Keypair() for _ in range(5)]
        self.mint, self.source, self.destination, self.custody = [Keypair() for _ in range(4)]
        self.tracked = {"mint": self.mint.pubkey(), "source": self.source.pubkey(),
                        "destination": self.destination.pubkey(), "custody": self.custody.pubkey()}
        self.svm.airdrop(self.payer.pubkey(), 1_000_000_000)
        self.clock(7)
        mint_key = self.mint.pubkey()
        create = create_account(CreateAccountParams(
            from_pubkey=self.payer.pubkey(), to_pubkey=mint_key,
            lamports=self.svm.minimum_balance_for_rent_exemption(MINT_LEN),
            space=MINT_LEN, owner=TOKEN_2022))
        # Initialize extension before InitializeMint2; native MintToChecked below.
        init_fee = native(bytes([26, 0]) + option_key(self.authority.pubkey())
                          + option_key(self.withdraw.pubkey()) + struct.pack("<HQ", 0, U64_MAX),
                          [meta(mint_key, writable=True)])
        init_mint = native(bytes([20, DECIMALS]) + bytes(self.minter.pubkey()) + option_key(None),
                           [meta(mint_key, writable=True)])
        self.send("initialize_mint", [create, init_fee, init_mint], [self.mint])
        for key in [self.source, self.destination, self.custody]:
            create = create_account(CreateAccountParams(
                from_pubkey=self.payer.pubkey(), to_pubkey=key.pubkey(),
                lamports=self.svm.minimum_balance_for_rent_exemption(TOKEN_LEN),
                space=TOKEN_LEN, owner=TOKEN_2022))
            init = native(bytes([18]) + bytes(self.holder.pubkey()),
                          [meta(key.pubkey(), writable=True), meta(mint_key)])
            self.send("initialize_token_account", [create, init], [key])
        self.send("issue_exact_supply",
                  [mint_to(mint_key, self.source.pubkey(), self.minter.pubkey(), issuance)],
                  [self.minter])

    def clock(self, epoch):
        schedule = self.svm.get_epoch_schedule()
        slot = schedule.get_first_slot_in_epoch(epoch)
        assert schedule.get_epoch(slot) == epoch
        self.svm.warp_to_slot(slot)
        self.svm.set_clock(Clock(slot, 0, epoch, epoch, 0))
        actual = self.svm.get_clock()
        assert actual.epoch == epoch and actual.slot == slot
        EVENTS.append(exact_json({"kind": "synthetic_clock", "fixture": self.label,
                                  "epoch": actual.epoch, "slot": actual.slot,
                                  "method": "epoch-schedule first slot + warp_to_slot + set_clock"}))

    def snapshot(self):
        result = {}
        for role, address in self.tracked.items():
            account = self.svm.get_account(address)
            if account is None:
                result[role] = None
            else:
                raw = bytes(account.data)
                result[role] = {"address": str(address), "runtime_owner": str(account.owner),
                                "lamports": account.lamports, "data_len": len(raw),
                                "data_hex": raw.hex(), "data_sha256": sha256(raw),
                                "decoded": mint_state(account) if role == "mint" else token_state(account)}
        return result

    def state(self, role):
        return self.snapshot()[role]["decoded"]

    def send(self, name, instructions, signers=(), expected_error=None,
             error_instruction=None, replay=None, corrupt_signature=False):
        before = self.snapshot()
        payer_before = self.svm.get_balance(self.payer.pubkey())
        if replay is None:
            self.svm.expire_blockhash()  # Fresh hash; sigverify/history stay enabled.
        transaction = replay or Transaction.new_signed_with_payer(
            instructions, self.payer.pubkey(), [self.payer, *signers], self.svm.latest_blockhash())
        if corrupt_signature:
            from solders.signature import Signature
            transaction.signatures = [Signature.default() for _ in transaction.signatures]
        result = self.svm.send_transaction(transaction)
        failed = isinstance(result, FailedTransactionMetadata)
        metadata = result.meta() if failed else result
        after = self.snapshot()
        event = {"kind": "native_transaction", "fixture": self.label, "case": name,
                 "synthetic_clock_epoch": self.svm.get_clock().epoch,
                 "evidence_level": "BUNDLED LOCAL TOKEN-2022 RUNTIME",
                 "expected": "SUCCESS" if expected_error is None else {"error": expected_error, "instruction": error_instruction}, "actual": "FAILURE" if failed else "SUCCESS",
                 "error": str(result.err()) if failed else None,
                 "error_instruction": getattr(result.err(), "index", None) if failed else None,
                 "signature": str(metadata.signature()), "recent_blockhash": str(transaction.message.recent_blockhash),
                 "compute_units": metadata.compute_units_consumed(), "logs": metadata.logs(),
                 "instructions": [{"program": str(ix.program_id), "data_hex": bytes(ix.data).hex(),
                                   "accounts": [{"address": str(a.pubkey), "signer": a.is_signer,
                                                 "writable": a.is_writable} for a in ix.accounts]}
                                  for ix in instructions],
                 "before": before, "after": after,
                 "observed_deltas": account_deltas(before, after),
                 "failed_token_state_expected_unchanged": expected_error is not None,
                 "payer_lamports_before": payer_before,
                 "payer_lamports_after": self.svm.get_balance(self.payer.pubkey()),
                 "payer_network_fees_excluded_from_token_state_rollback": True}
        EVENTS.append(exact_json(event))
        if expected_error is None:
            assert not failed, str(result)
        else:
            assert failed, "expected native failure, got success"
            if type(expected_error) is int:
                assert getattr(getattr(result.err(), "err", None), "code", None) == expected_error, str(result.err())
            else:
                assert expected_error in str(result.err()), str(result.err())
            if error_instruction is not None:
                assert getattr(result.err(), "index", None) == error_instruction, str(result.err())
            assert after == before, "failed transaction changed tracked mint/token accounts"
        return transaction

    def schedule_and_revoke(self):
        self.send("schedule_800bps_at_E_plus_2",
                  [set_fee(self.mint.pubkey(), self.authority.pubkey())], [self.authority])
        self.send("revoke_fee_configuration",
                  [revoke(self.mint.pubkey(), self.authority.pubkey(), 4)], [self.authority])
        self.send("revoke_mint_issuance",
                  [revoke(self.mint.pubkey(), self.minter.pubkey(), 0)], [self.minter])
