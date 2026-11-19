"""Focused offline HTFP-01 regression using the captured Devnet runtime fixture."""

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from solders import solders as solders_native
from solders.account import Account
from solders.instruction import AccountMeta, Instruction
from solders.system_program import transfer

sys.path.insert(0, str(Path(__file__).with_name("program")))
import native
from native import NATIVE_RUNTIME_SHA, Q, VM, pinned, sha
from oracle import amount, changed, check_batch, check_recover, raw, replace_u64


BASELINE = "evidence/devnet_processor_upgrade/build-supervisor/build-001/enabled.so"
BASELINE_SHA = "fcb1e58e60c1d30087792626966053498bcbc01962922e93dac51c31dfd00415"
NATIVE_CREDIT = 10_000_000


def funded_vm(elf):
    # Reuse the captured VM and receipt oracle without reopening their old journal.
    run = SimpleNamespace(
        elf=elf, vms=0, txs=0, coverage=[], resources=lambda: None,
        emit=lambda _: None, journal=lambda *_args, **_kwargs: None,
    )
    vm = VM(run)
    vm.send("fixture-token-fees", [
        vm.transfer_token(vm.k["participant2_htfp"], 100_000_000_000_000_000),
    ])
    vm.send("fixture-custody-donation", [vm.transfer_token(vm.k["custody"], 1000)])
    vm.verified()
    vm.send("initialize-volume", [vm.operation(4)])
    receipt = vm.send(
        "recover-fixture-withholding", [vm.recover([vm.k["participant2_htfp"]])], payer=1,
    )
    check_recover(receipt, 8_000_000_000_000_080)
    return vm


def external_surplus(vault):
    data = raw(vault)
    return int(vault["lamports"]) - amount(data, 113) - amount(data, 64)


def credit_vault(vm):
    receipt = vm.send("external-native-credit", [transfer({
        "from_pubkey": vm.actors[0].pubkey(),
        "to_pubkey": vm.k["vault_wsol"],
        "lamports": NATIVE_CREDIT,
    })])
    before = receipt["before"]["vault_wsol"]
    after = receipt["after"]["vault_wsol"]
    assert external_surplus(before) == 0
    assert after == changed(before, lamports=int(before["lamports"]) + NATIVE_CREDIT)
    assert external_surplus(after) == NATIVE_CREDIT


def report_row(receipt, **extra):
    packet_bytes = len(bytes.fromhex(receipt["packet_hex"]))
    assert packet_bytes <= 1232 and receipt["compute_units"] <= 400_000
    return {
        "case": receipt["name"],
        "status": receipt["status"],
        "expected_error": receipt["expected_error"],
        "error": receipt["error"],
        "compute_units": receipt["compute_units"],
        "packet_bytes": packet_bytes,
        **extra,
    }


def corrected_flow(elf):
    vm = funded_vm(elf)
    credit_vault(vm)
    process, finalize = vm.process(Q), vm.fence()

    vault_index = next(
        i for i, role in enumerate(vm.abi["wire"]["3"]["accounts"])
        if role["role"] == "vault_wsol"
    )
    metas = list(process.accounts)
    metas[vault_index] = AccountMeta(vm.k["participant1_htfp"], False, True)
    wrong_vault = vm.send("wrong-vault", [
        Instruction(process.program_id, process.data, metas), finalize,
    ], expect=7001)

    vault_key = vm.k["vault_wsol"]
    vault = vm.svm.get_account(vault_key)
    backed_lamports = amount(vault.data, 64) + amount(vault.data, 113)
    vm.host("invalid-local-native-backing", vault_key, Account(
        backed_lamports - 1, vault.data, vault.owner, vault.executable, vault.rent_epoch,
    ))
    under_backed = vm.send("under-backed-vault", [process, finalize], expect=7023)
    vm.host("restore-local-vault", vault_key, vault)

    overdraft = transfer({
        "from_pubkey": vm.actors[0].pubkey(),
        "to_pubkey": vm.actors[1].pubkey(),
        "lamports": vm.svm.get_balance(vm.actors[0].pubkey()) + 1,
    })
    rolled_back = vm.send("late-failure", [process, overdraft, finalize], expect=1)
    assert any("HTFP Process close" in line for line in rolled_back["logs"])
    assert external_surplus(rolled_back["after"]["vault_wsol"]) == NATIVE_CREDIT

    receipt = vm.send("process-preserves-external-credit", [process, finalize])
    result = check_batch(receipt, [Q], 0, [str(vm.actors[0].pubkey())])
    assert result["output"] == 2_300_975
    assert external_surplus(receipt["before"]["vault_wsol"]) == NATIVE_CREDIT
    assert external_surplus(receipt["after"]["vault_wsol"]) == NATIVE_CREDIT
    return result["output"], [
        report_row(wrong_vault), report_row(under_backed), report_row(rolled_back),
        report_row(receipt, reserve_credit_lamports=result["output"],
                   preserved_external_lamports=NATIVE_CREDIT),
    ]


def synchronized_flow(elf):
    vm = funded_vm(elf)
    credit_vault(vm)
    sync = Instruction(vm.k["legacy_token"], bytes([17]), [
        AccountMeta(vm.k["vault_wsol"], False, True),
    ])
    receipt = vm.send("legacy-sync-before-process", [sync, vm.process(Q), vm.fence()])
    vault_before = receipt["before"]["vault_wsol"]
    before_sync = raw(vault_before)
    assert external_surplus(vault_before) == NATIVE_CREDIT
    assert external_surplus(receipt["after"]["vault_wsol"]) == 0
    # Price the original processor against the SPL balance after the prefix instruction.
    synchronized_vault = changed(
        vault_before, data=replace_u64(before_sync, 64, amount(before_sync, 64) + NATIVE_CREDIT),
    )
    synchronized_receipt = dict(
        receipt, before=dict(receipt["before"], vault_wsol=synchronized_vault),
    )
    result = check_batch(synchronized_receipt, [Q], 0, [str(vm.actors[0].pubkey())])
    return result["output"], report_row(
        receipt, reserve_credit_lamports=result["output"], synchronized_lamports=NATIVE_CREDIT,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--fixture-root", required=True, type=Path,
                        help="Root containing the pinned evidence paths listed in the regression README.")
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Run without Python optimization so the fixture assertions execute.")
    native.FIXTURE_ROOT = args.fixture_root.resolve(strict=True)
    assert native.FIXTURE_ROOT.is_dir()
    imported_runtime = Path(solders_native.__file__).resolve(strict=True)
    assert sha(imported_runtime.read_bytes()) == NATIVE_RUNTIME_SHA
    candidate = args.candidate.read_bytes()
    assert candidate.startswith(b"\x7fELF") and sha(candidate) != BASELINE_SHA
    output, rows = corrected_flow(candidate)
    synced_output, synced_row = synchronized_flow(pinned(BASELINE, BASELINE_SHA))
    assert synced_output > output
    print(json.dumps({
        "candidate_sha256": sha(candidate),
        "baseline_sha256": BASELINE_SHA,
        "cases": [*rows, synced_row],
    }, indent=2))


if __name__ == "__main__":
    main()
