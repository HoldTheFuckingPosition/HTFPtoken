"""Focused native prerequisites before dependent frozen case families."""
import argparse,traceback,gc
from runtime import *
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--fixture',required=True);parser.add_argument('--label',required=True);args=parser.parse_args();integrity(args.fixture);out=OUT/args.label;before=freeze(out);result=dict(status='INCOMPLETE',phase='L01_L02_L03_FOCUSED',command=sys.argv,fixture=FIXTURE);probes=[];vm=None
 try:
  for writable in [False,True]:
   vm=VM('focused_'+('CPI_W' if writable else 'SDK_R'))
   if not writable:
    vm.send('actual_MemoV3_control',[ix('memo',b'HTFP_M5_LOCKER_MEMO_V3_CONTROL',[])])
    vm.send('valid_System_signature_control',[sol(K['payer'],K['beneficiary'],1)])
    vm.send('invalid_signature_control',[sol(K['payer'],K['beneficiary'],1)],control='invalid_signature')
    vm.send('expired_blockhash_control',[sol(K['payer'],K['beneficiary'],1)],control='expired_blockhash')
   vm.setup_pool();row=vm.lock(writable,observe=True);flag=next(a for a in row['actual_compiled_accounts'] if a['pubkey']==str(K['lp_mint']));assert flag['writable']==writable
   record=dict(variant='CPI_W' if writable else 'SDK_R',status=row['status'],error=row['error'],message_sha256=row['transaction_sha256'],LP_mint_compiled_writable=flag['writable'],rollback=row.get('rollback_verified'))
   if row['status']=='SUCCESS':
    assert amt(vm.account('creator_lp'))==0 and amt(vm.account('shared_lp_escrow'))==999999999900;assert supply(vm.account('fee_key_mint_1'))==1 and amt(vm.account('fee_key_account_1'))==1;assert vm.account('metadata_1') is not None;record['genuine_escrow_and_FeeKey_metadata_assertions']=True
   probes.append(record);del vm;vm=None;gc.collect()
  result.update(status='PREREQUISITES_PASS' if any(p['status']=='SUCCESS' for p in probes) else 'BLOCKED_BOTH_GENUINE_ABI_CANDIDATES_FAILED',probes=probes,full_26_107_run='NOT_RUN_AT_FOCUSED_CHECKPOINT')
 except BaseException:result.update(status='BLOCKED_SETUP_OR_INSTRUMENTATION_FAILURE',error=traceback.format_exc(),probes=probes)
 finally:
  if vm is not None:del vm;gc.collect()
  save_trace(out/'events.json.gz',EVENTS);assert source_inputs()==before;result.update(instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],source_unchanged=True,resources=resources());save(out/'RESULT.json',result)
 print(json.dumps(result,indent=2));return 0 if result['status']=='PREREQUISITES_PASS' else 1
if __name__=='__main__':raise SystemExit(main())
