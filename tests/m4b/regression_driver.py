"""Evidence-prefix adapter ONLY for frozen M3 driver; all33 tests remain unchanged.
Adds read-only serialized-message recording around the same native send call.
"""
from pathlib import Path
import json,sys,hashlib,traceback,types
from common import ROOT,OUT,save,file_sha,resources
from solders.litesvm import LiteSVM
from solders.transaction_metadata import FailedTransactionMetadata

def main(label):
 original=ROOT/'tests/m3/run.py';source=original.read_text();adapted=source
 replacements=[("['evidence/m3/author','evidence/m3/supervisor']","['evidence/m4b/author']"),("budget_root=ROOT/'evidence/m3/author/native-target'","budget_root=out")]
 for before,after in replacements:
  assert adapted.count(before)==1;adapted=adapted.replace(before,after)
 expected=json.loads((ROOT/'evidence/m3/author/native-target/captured-full-001/environment.json').read_text())['artifacts']
 args=['tests/m4b/regression_driver.py','--out','evidence/m4b/author/'+label,'--elf',expected['M3_ELF']['path'],'--default-elf',expected['M3_DEFAULT_ELF']['path'],'--helper-elf',expected['M3_HELPER_ELF']['path'],'--native-fixture','testnet-capture-462242918']
 out=OUT/label;assert not out.exists();messages=[];resource_rows=[resources()];native_send=LiteSVM.send_transaction
 def recording_send(self,tx):
  packet=bytes(tx);assert len(packet)<=1232
  result=native_send(self,tx);meta=result.meta() if isinstance(result,FailedTransactionMetadata) else result
  assert meta.compute_units_consumed()<=1400000
  messages.append(dict(transaction_hex=packet.hex(),transaction_sha256=hashlib.sha256(packet).hexdigest(),message_hex=bytes(tx.message).hex(),recent_blockhash=str(tx.message.recent_blockhash),signatures=[str(s) for s in tx.signatures],packet_bytes=len(packet),compute_units=meta.compute_units_consumed(),status='FAILURE' if isinstance(result,FailedTransactionMetadata) else 'SUCCESS',error=str(result.err()) if isinstance(result,FailedTransactionMetadata) else None,logs=meta.logs(),instrumentation='record only; original native send and unchanged assertions'))
  if len(messages)%25==0:resource_rows.append(resources())
  return result
 # No transaction/signature/settings/instruction/assertion is changed by this instrumentation.
 LiteSVM.send_transaction=recording_send;sys.argv=args
 policy_path=ROOT/'tests/m3/evidence_policy.py';policy_original=policy_path.read_text()
 policy_before="if not path.is_relative_to(ROOT/'evidence/m3'):"
 policy_after="if not (path.is_relative_to(ROOT/'evidence/m3') or path.is_relative_to(ROOT/'evidence/m4b/author')):"
 assert policy_original.count(policy_before)==1
 policy_adapted=policy_original.replace(policy_before,policy_after)
 policy_module=types.ModuleType('evidence_policy');policy_module.__file__=str(policy_path)
 exec(compile(policy_adapted,str(policy_path),'exec'),policy_module.__dict__)
 sys.modules['evidence_policy']=policy_module
 namespace={'__file__':str(original),'__name__':'m4b_original_m3_evidence_adapter'}
 try:
  exec(compile(adapted,str(original),'exec'),namespace);status=namespace['main']()
 finally:
  LiteSVM.send_transaction=native_send
  if out.exists():
   save(out/'serialized_transactions.json',messages)
   (out/'original_driver_output_adapter.py.txt').write_text(adapted)
   (out/'original_evidence_policy_output_adapter.py.txt').write_text(policy_adapted)
   save(out/'ADAPTER.json',dict(original_policy_sha256=file_sha(policy_path),policy_prefix_replacement=[policy_before,policy_after],adapted_policy_sha256=hashlib.sha256(policy_adapted.encode()).hexdigest(),original_driver_path=str(original.relative_to(ROOT)),original_driver_sha256=file_sha(original),adapter_sha256=file_sha(__file__),replacements=replacements,adapted_driver_sha256=hashlib.sha256(adapted.encode()).hexdigest(),transaction_recording='Read-only wrapper around unchanged LiteSVM.send_transaction, no changes to signatures/checks/arguments/actual native execution',message_count=len(messages),resource_observations=resource_rows+[resources()],original_artifacts=expected,original_test_discovery='all unchanged tests/m3/test_*.py',native_fixture='original Testnet414f5c53...be19b91',no_skips_or_assertion_changes=True))
 if status==0:
  report=json.loads((out/'report.json').read_text());assert (int(report['tests_run']),int(report['transaction_count']),int(report['expected_failures']))==(33,788,93);assert len(messages)==789 # 788 harness TX + unchanged direct invalid-signature boundary control
 print(json.dumps(dict(adapter_status=status,message_count=len(messages),out=str(out),resources=resources())));return status
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
