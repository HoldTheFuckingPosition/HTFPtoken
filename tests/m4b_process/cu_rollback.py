"""Genuine H CU-boundary failures; no callee replacement or debug endpoint."""
from test_process import *
import re

def reached(row):
 logs=row['logs'];restore=next((i for i,x in enumerate(logs) if 'HTFP Process restore P' in x),None)
 return dict(after_burn=any('HTFP Process native swap' in x for x in logs),after_swap=any('HTFP Process close' in x for x in logs),after_close=any('HTFP actual postclose owner=11111111111111111111111111111111 data_len=0 lamports=0' in x for x in logs),after_refund=restore is not None,after_restore=restore is not None and any(x=='Program 11111111111111111111111111111111 success' for x in logs[restore+1:]))
def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);before=freeze(out);case=ProcessTests('test_happy_donation_and_native_fee_separation');v=None;observations=[]
 try:
  def setup(suffix):
   vm=case.make(suffix);l=vm.svm.minimum_balance_for_rent_exemption(165);vm.send('genuine_prefund_before_CU_failure',[native_transfer(vm.i.pubkey(),vm.temp(0),l-1)]);return vm
  calibration=setup('-calibrate');row=calibration.send('complete_current_H_calibration',[calibration.process_ix(),calibration.finish()]);costs=[int(re.search(r' consumed (\d+) of ',x).group(1)) for x in row['logs'] if x.startswith('Program '+str(K['program'])+' consumed ')];assert len(costs)==2;proc=costs[0]
  v=setup('-failures');covered={name:False for name in ['after_burn','after_swap','after_close','after_refund','after_restore']}
  for margin in [1,1000,4000,8000,12000,18000,26000,40000,60000,80000]:
   budget=max(5000,150+proc-margin);row=v.send('actual_H_CU_failure_margin_'+str(margin),[v.process_ix(),v.finish()],observe=True,cu=budget);assert row['status']=='FAILURE' and row['compute_units']==budget;assert ('ProgramFailedToComplete' in row['error'] and any('exceeded CUs meter' in x for x in row['logs'])) or 'ComputationalBudgetExceeded' in row['error'];stage=reached(row);covered={k:covered[k] or stage[k] for k in covered};observations.append(dict(budget=budget,margin=margin,error=row['error'],reached=stage,rollback_verified=row['rollback_verified'],message_sha256=row['transaction_sha256']))
  assert all(covered.values()),covered
  # Failure in a genuine later instruction after the complete burn/sale/close/refund/restore.
  row=v.send('actual_H_then_native_late_System_failure',[v.process_ix(),native_transfer(v.i.pubkey(),v.g.pubkey(),(1<<64)-1),v.finish()],expected=1);assert all(reached(row).values());observations.append(dict(case='late_native_System_error',error=row['error'],reached=reached(row),rollback_verified=row['rollback_verified']))
  result=dict(status='ACTUAL_H_LATE_ROLLBACK_PASS',calibration_Process_CU=proc,calibration_Finalize_CU=costs[1],covered=covered,observations=observations,limits='Reached boundaries authenticated by current H/native invocation logs and immutable source; failed-TX intermediate state is not a committed receipt; no callback/debug/callee patch')
 except BaseException:result=dict(status='FAIL',traceback=traceback.format_exc(),observations=observations)
 finally:
  save_gzip_events(out/'events.json.gz',[e for vm in ALL_VMS for e in vm.events]);assert all(file_sha(ROOT/p)==d for p,d in before.items());result['resources']=resources();save(out/'RESULT.json',result)
 print(json.dumps(result));return 0 if result['status']!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
