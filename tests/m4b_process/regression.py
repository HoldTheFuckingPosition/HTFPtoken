"""Exact explicit source/output/feature adapter for all33 frozen M3 tests.
Original mode: fresh current-source local-m3/default/PDA helper + exact Testnet.
Integrated mode: fresh local-m4b/default/helper + exact mixed native+mint fixture;
only the unfrozen-six-byte Process error changes7015->7000, per frozen new ABI.
All original financial/authentication/assertion/discovery/success checks remain.
"""
from common import *
import types,importlib.util,struct,traceback
from solders.litesvm import LiteSVM
from solders.transaction_metadata import FailedTransactionMetadata
from solders.sysvar import CLOCK,RENT
from solders.pubkey import Pubkey

def load(name,path,deps=None):
 old={k:sys.modules.get(k) for k in deps or {}}
 try:
  sys.modules.update(deps or {});s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
 finally:
  for k,v in old.items():
   if v is None:sys.modules.pop(k,None)
   else:sys.modules[k]=v

def main(label,mode):
 assert mode in ['original','integrated'];out=OUT/label;out.mkdir(exist_ok=False);before=freeze(out)
 sys.path.insert(0,str(ROOT/'tests/m3'));original_native=load('original_fixed_native_fixture',ROOT/'tests/m3/native_fixture.py')
 B=load('frozen_B_reg_common',ROOT/'tests/m4b/common.py');mint=load('frozen_B_reg_mint',ROOT/'tests/m4b/native_mint_fixture.py',{'common':B})
 fixture_module=types.ModuleType('native_fixture')
 if mode=='original':fixture_module.SELECTORS=original_native.SELECTORS;fixture_module.prepare=original_native.prepare;selector=original_native.CAPTURE_SELECTOR
 else:
  class IntegratedFixture(B.MixedFixture):
   def install(self,svm):
    row=super().install(svm);row['reviewed_native_mint_static_dependency']=mint.install(svm);return row
  fixture_module.SELECTORS=('m4b-mixed-with-reviewed-native-mint',);fixture_module.prepare=lambda selector:IntegratedFixture();selector=fixture_module.SELECTORS[0]
 sys.modules['native_fixture']=fixture_module
 original_policy=ROOT/'tests/m3/evidence_policy.py';policy=original_policy.read_text();needle="if not path.is_relative_to(ROOT/'evidence/m3'):";assert policy.count(needle)==1
 policy=policy.replace(needle,"if not (path.is_relative_to(ROOT/'evidence/m3') or path.is_relative_to(ROOT/'evidence/m4b/process_author')):")
 pm=types.ModuleType('evidence_policy');pm.__file__=str(original_policy);exec(compile(policy,str(original_policy),'exec'),pm.__dict__);base_validate=pm.validate_artifact
 def validate(path,kind,feature):return base_validate(path,kind,'local-m4b' if mode=='integrated' and kind=='htfp' and feature=='local-m3' else feature)
 pm.validate_artifact=validate;sys.modules['evidence_policy']=pm
 # Frozen test module is adapted in memory only for the exact documented new wire error.
 if mode=='integrated':
  tp=ROOT/'tests/m3/test_contract.py';text=tp.read_text();old="f.send('unimplemented_process',[ix(b'HTFP\\1\\3',[],H)],error=7015,index=0)";new=old.replace('error=7015','error=7000');assert text.count(old)==1;text=text.replace(old,new)
  tm=types.ModuleType('test_contract');tm.__file__=str(tp);exec(compile(text,str(tp),'exec'),tm.__dict__);sys.modules['test_contract']=tm
 import harness as h
 old_send=LiteSVM.send_transaction;old_vm_send=h.VM.send;serials=[];vms={};metadata_errors=[]
 def state(svm,key):
  a=svm.get_account(key)
  return None if a is None else dict(address=str(key),owner=str(a.owner),lamports=a.lamports,data_hex=bytes(a.data).hex(),data_sha256=sha(bytes(a.data)),length=len(a.data),executable=a.executable)
 def actual(svm):
  c=svm.get_clock();r=svm.get_rent()
  return dict(clock={k:getattr(c,k) for k in ['slot','epoch_start_timestamp','epoch','leader_schedule_epoch','unix_timestamp']},rent={k:getattr(r,k) for k in ['lamports_per_byte_year','exemption_threshold','burn_percent']},raw_clock=state(svm,CLOCK),raw_rent=state(svm,RENT))
 def alt_states(svm,tx):
  keys=set(lookup.account_key for lookup in getattr(tx.message,'address_table_lookups',[]))
  for instruction in tx.message.instructions:
   if str(tx.message.account_keys[instruction.program_id_index])=='AddressLookupTab1e1111111111111111111111111' and instruction.accounts:keys.add(tx.message.account_keys[instruction.accounts[0]])
  return {str(key):state(svm,key) for key in keys}
 def recording(svm,tx):
  alt_before=alt_states(svm,tx)
  runtime_before=actual(svm);vm=vms.get(id(svm));control_before=vm.snapshot() if vm is not None else None
  result=old_send(svm,tx);meta=result.meta() if isinstance(result,FailedTransactionMetadata) else result
  row=dict(transaction_hex=bytes(tx).hex(),transaction_sha256=sha(bytes(tx)),message_hex=bytes(tx.message).hex(),recent_blockhash=str(tx.message.recent_blockhash),signatures=[str(s) for s in tx.signatures],packet_bytes=len(bytes(tx)),status='FAILURE' if isinstance(result,FailedTransactionMetadata) else 'SUCCESS',error=str(result.err()) if isinstance(result,FailedTransactionMetadata) else None,compute_units=meta.compute_units_consumed(),signature_verification=True,blockhash_verification=True,heap_bytes=32768,actual_runtime_before=runtime_before,actual_runtime_after=actual(svm),fixture=vm.label if vm else None,message_version='v0' if hasattr(tx.message,'address_table_lookups') else 'legacy',addresses={k:str(v) for k,v in {**h.K,**vm.tracked}.items()} if vm else {},control_before=control_before,control_after=vm.snapshot() if vm else None)
  # Outcome is saved before optional inner formatting; the actual native result is never replaced.
  serials.append(row)
  try:row['actual_inner_instructions']=[[dict(program_id_index=i.instruction().program_id_index,accounts=list(i.instruction().accounts),data_hex=bytes(i.instruction().data).hex(),stack_height=i.stack_height()) for i in group] for group in meta.inner_instructions()]
  except Exception as e:row['metadata_instrumentation_error']=repr(e);metadata_errors.append(repr(e))
  alts={}
  for lookup in getattr(tx.message,'address_table_lookups',[]):alts[str(lookup.account_key)]=state(svm,lookup.account_key)
  for instruction in tx.message.instructions:
   program=tx.message.account_keys[instruction.program_id_index]
   if str(program)=='AddressLookupTab1e1111111111111111111111111' and instruction.accounts:
    key=tx.message.account_keys[instruction.accounts[0]];alts[str(key)]=state(svm,key)
  if alts:row['actual_ALT_accounts']=alts;row['actual_ALT_accounts_before']=alt_before
  assert row['packet_bytes']<=1232 and row['compute_units']<=1400000
  return result
 def vm_send(vm,*a,**kw):
  vms[id(vm.svm)]=vm;start=len(serials);old_events=len(h.EVENTS)
  try:return old_vm_send(vm,*a,**kw)
  finally:
   rows=[r for r in h.EVENTS[old_events:] if r['kind']=='transaction'];captured=serials[start:]
   assert len(rows)==len(captured),(len(rows),len(captured))
   for row,meta in zip(rows,captured):
    for k,v in meta.items():
     if k not in ['control_before','control_after']:row[k]=v
    meta['attached_to_harness_event']=True
 def write_events(output,events):
  enriched=list(events)
  for row in serials:
   if not row.get('attached_to_harness_event'):
    extra=dict(row);extra['kind']='direct_native_preflight_control';enriched.append(extra)
  assert len(json.dumps(enriched,separators=(',',':')).encode())<=128*1024**2
  save_gzip_events(output/'events.json.gz',enriched)
 original=ROOT/'tests/m3/run.py';driver=original.read_text();replacements=[("['evidence/m3/author','evidence/m3/supervisor']","['evidence/m4b/process_author']"),("budget_root=ROOT/'evidence/m3/author/native-target'","budget_root=out"),("out.mkdir(exist_ok=False)","assert out.exists()"),("if h:(out/'events.json').write_text(json.dumps(exact(h.EVENTS),indent=2)+'\\n')","if h:write_events(out,h.EVENTS)")]
 for a,b in replacements:assert driver.count(a)==1,a;driver=driver.replace(a,b)
 # JSON stage reports use compact serialization only; no fields/assertions are removed.
 driver=driver.replace('indent=2',"separators=(',',':')")
 folders={'M3_ELF':'build-m3-final' if mode=='original' else 'build-h4b-final-002','M3_DEFAULT_ELF':'build-default-final','M3_HELPER_ELF':'build-m3-helper-final'}
 argv=['tests/m4b_process/regression.py','--out',str(out.relative_to(ROOT)),'--elf',str(OUT/folders['M3_ELF']/'htfp.so'),'--default-elf',str(OUT/folders['M3_DEFAULT_ELF']/'htfp.so'),'--helper-elf',str(OUT/folders['M3_HELPER_ELF']/'pda_wallet.so'),'--native-fixture',selector]
 LiteSVM.send_transaction=recording;h.VM.send=vm_send;sys.argv=argv
 try:
  namespace={'__file__':str(original),'__name__':'explicit_stage_c_M3_adapter','write_events':write_events};exec(compile(driver,str(original),'exec'),namespace);status=namespace['main']()
 finally:
  LiteSVM.send_transaction=old_send;h.VM.send=old_vm_send
  (out/'adapted_original_driver.py.txt').write_text(driver);(out/'adapted_evidence_policy.py.txt').write_text(policy)
  save(out/'ADAPTER.json',dict(mode=mode,original_driver_sha256=file_sha(original),original_policy_sha256=file_sha(original_policy),adapter_sha256=file_sha(__file__),adapted_driver_sha256=sha(driver.encode()),adapted_policy_sha256=sha(policy.encode()),replacements=replacements,feature_mapping='local-m3 expected -> actual local-m4b only for integrated htfp build validation; default/helper unchanged' if mode=='integrated' else None,exact_test_expectation_change='six-byte unfrozen Process7015 -> malformed active Process7000 only in integrated mode' if mode=='integrated' else None,test_financial_assertions_removed=False,source_inputs_unchanged=all(file_sha(ROOT/p)==d for p,d in before.items()),native_send_attempts=len(serials),metadata_errors=metadata_errors,resources=resources()))
 if status==0:
  report=json.loads((out/'report.json').read_text());assert tuple(int(report[x]) for x in ['tests_run','transaction_count','expected_failures','failures','errors','skipped'])==(33,788,93,0,0,0);assert len(serials)==789 and not metadata_errors
  assert sum(p.stat().st_size for p in out.rglob('*') if p.is_file())<=128*1024**2
 print(json.dumps(dict(status=status,mode=mode,send_attempts=len(serials),resources=resources())));return status
if __name__=='__main__':raise SystemExit(main(sys.argv[1],sys.argv[2]))
