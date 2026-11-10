"""S77 only: advancing-clock nominal chronology and up to six exact-prestate cuts."""
from runtime import *
import argparse,traceback,gc

def operation(op):return dict(program_id=str(op.program_id),data_hex=bytes(op.data).hex(),accounts=[dict(pubkey=str(m.pubkey),signer=m.is_signer,writable=m.is_writable) for m in op.accounts])
def reference(row):return dict(event_index=next(i for i,r in enumerate(EVENTS) if r is row),fixture=row['fixture'],name=row['name'],transaction_sha256=row['transaction_sha256'],message_sha256=row['message_sha256'])
def prepare(label):
 v=VM(label);v.setup_pool();lock=v.lock();v.position_start();v.receipts();assert amt(v.account('creator_lp'))==0 and amt(v.account('shared_lp_escrow'))==v.initial_receipt
 for role in ['fee_key_mint_1']:
  m=M3.mint_view(bytes(v.account(role).data));assert m['supply']==1 and m['decimals']==0 and m['mint_authority'] is None and m['freeze_authority'] is None
 assert amt(v.account('fee_key_account_1'))==1 and v.account('metadata_1') is not None
 v.clock('base_active_swaps');v.accrue();v.clock('first_primary_claim');first=v.claim();assert first['principal_diagnostic']['holds'] and first['principal_diagnostic']['unadjusted_holds'];v.sentinels();v.clock('B_deposit');dep=v.deposit_B();v.sentinels();v.clock('B_secondary_lock');secondary=v.secondary_lock();assert amt(v.account('fee_key_account_2'))==1 and supply(v.account('fee_key_mint_2'))==1 and v.account('metadata_2') is not None
 v.clock('later_swaps');v.accrue(later=True);v.clock('repeat_primary_claim');v.sentinels();assert amt(v.account('unrelated_lp'))==5000000000
 return v,dict(lock=reference(lock),first_primary_claim=reference(first),capital_deposit=reference(dep),secondary_lock=reference(secondary),first_principal=first['principal_diagnostic'],capital=dep['deposit_accounting'])
def prestate(v):return dict(accounts=v.snap(),runtime=v.actual(),programs={r:v.program_view(r) for r in [*v.programs,'associated_token']},operation=operation(v.claim_ix()))
def phase(fixture):
 observed=next((e for e in reversed(EVENTS) if e.get('kind')=='synthetic_clock' and e.get('fixture')==fixture),None)
 return None if observed is None else dict(phase=observed['phase'],requested=observed['requested'],actual_clock=observed['actual']['clock'],recovered_from_retained_phase_events=True)

LEDGER_BYTES=65536
def reserve_ledger(out):
 # New per-run files only. Reserve allocated space BEFORE the first native VM.
 resources(LEDGER_BYTES+4096)
 save(out/'RESULT.json',dict(status='RUNNING_UNFINALIZED',instances=0,attempts=0,cumulative_start=HISTORY.copy(),counter_warning='If interrupted, reconcile retained native evidence before any further run.'))
 reserve=out/'FINAL_LEDGER_RESERVED.json';assert not reserve.exists();reserve.write_bytes(b' '*LEDGER_BYTES)
 with reserve.open('r+b') as f:f.flush();os.fsync(f.fileno())

def finalize(out,result,before):
 original=result['status'];errors=[]
 # Counters are independent of trace formatting, source assertions and resource probes.
 result.update(instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'])
 try:save_trace(out/'events.json.gz',EVENTS);result['trace_finalization']='COMPLETE'
 except BaseException:errors.append(dict(step='trace_finalization',error=traceback.format_exc()));result['trace_finalization']='FAILED'
 try:
  result['source_unchanged']=source_inputs()==before
  if not result['source_unchanged']:errors.append(dict(step='source_finalization',error='Source inputs changed during run'))
 except BaseException:errors.append(dict(step='source_finalization',error=traceback.format_exc()));result['source_unchanged']=False
 try:result['resources']=resources()
 except BaseException:errors.append(dict(step='resource_finalization',error=traceback.format_exc()))
 result['finalization_errors']=errors
 if errors:result.update(status='FINALIZATION_FAILURE',native_work_status_before_finalization=original)
 body=(json.dumps(result,separators=(',',':'))+'\n').encode()
 if len(body)>LEDGER_BYTES:
  result=dict(status='FINALIZATION_FAILURE',native_work_status_before_finalization=original,instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],error='Report exceeds preallocated ledger; complete trace status retained below',trace_finalization=result.get('trace_finalization'),full_result_sha256=sha(body),full_result_bytes=len(body),finalization_errors=errors)
  body=(json.dumps(result,separators=(',',':'))+'\n').encode()
 assert len(body)<=LEDGER_BYTES
 reserve=out/'FINAL_LEDGER_RESERVED.json'
 try:
  with reserve.open('r+b') as f:f.write(body+b' '*(LEDGER_BYTES-len(body)));f.flush();os.fsync(f.fileno())
  # Atomic replacement affects only this NEW run's unfinalized ledger.
  os.replace(reserve,out/'RESULT.json')
 except BaseException:
  emergency=dict(status='LEDGER_IO_FAILURE_RECONCILIATION_REQUIRED',instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],error=traceback.format_exc(),reserved_path=str(reserve))
  print(json.dumps(emergency,separators=(',',':')),file=sys.stderr,flush=True);raise
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);a=p.parse_args();integrity(a.fixture);out=OUT/a.label;before=freeze(out);reserve_ledger(out);result=dict(status='INCOMPLETE',overall_stage='INCOMPLETE_NOT_ACCEPTED',command=sys.argv,role=ROLE,fixture=FIXTURE,characterization_handoff_sha256=OVERLAY['evidence/M5_LOCKER_CHARACTERIZATION_HANDOFF.json'],old_counterexample='PRESERVED: v2 fixed-clock extra pre-first-claim branch remains strict adjusted diagnostic failure; S76 supersedes old nominal-L25.1association.',full107suite='NOT_RUN_NOT_ASSIGNED',cuts=[]);v=None;active_fixture='nominal'
 try:
  v,chronology=prepare('nominal');result['nominal_chronology']=chronology;calibration=prestate(v);EVENTS.append(dict(kind='claim_calibration_prestate',fixture=v.label,prestate=calibration,sha256=sha(json.dumps(calibration,sort_keys=True,separators=(',',':')).encode())));state2=bytes(v.account('lock_state_2').data);row=v.claim();assert bytes(v.account('lock_state_2').data)==state2 and amt(v.account('unrelated_lp'))==5000000000;assert row['before']==calibration['accounts'] and row['actual_runtime_before']==calibration['runtime'] and row['requested_instructions'][1]==calibration['operation'];result['nominal_repeat_claim']=dict(reference=reference(row),principal=row['principal_diagnostic'],accounting=row['claim_accounting'],CU=row['compute_units']);cal=row['compute_units'];v=None;gc.collect()
  for margin in [1,1000,4000,16000,40000,80000]:
   active_fixture='cut_'+str(margin);v,replay=prepare(active_fixture);candidate=prestate(v);eq=candidate==calibration;EVENTS.append(dict(kind='claim_cut_prestate_comparison',fixture=v.label,margin=margin,identical=eq,prestate=candidate,calibration_sha256=sha(json.dumps(calibration,sort_keys=True,separators=(',',':')).encode()),candidate_sha256=sha(json.dumps(candidate,sort_keys=True,separators=(',',':')).encode())));assert eq,'Fresh genuine prestate differs from nominal calibration';limit=max(5000,cal-margin);r=v.send('repeat_primary_claim_CU_margin_'+str(margin),[v.claim_ix()],[v.w],cu=limit,expected='OBSERVE');result['cuts'].append(dict(margin=margin,limit=limit,calibration_CU=cal,identical_prestate=eq,reference=reference(r),status=r['status'],error=r['error'],CU=r['compute_units'],rollback=r.get('rollback_verified'),logs=r['logs']));assert r['requested_instructions'][1]==calibration['operation'];assert r['before']==calibration['accounts'] and r['actual_runtime_before']==calibration['runtime'];assert r['status']=='FAILURE' and r['error'] in ['TransactionErrorInstructionError((1, Fieldless(ProgramFailedToComplete)))','TransactionErrorInstructionError((1, Fieldless(ComputationalBudgetExceeded)))'];assert r['compute_units']==limit and r['rollback_verified'];assert any(str(K['locker'])+' invoke [1]' in l for l in r['logs']);v.sentinels();v=None;gc.collect()
  result['status']='BOUNDED_CHARACTERIZATION_COMPLETE_NO_STAGE_ACCEPTANCE'
 except BaseException:
  diagnostics=[r for r in EVENTS if r.get('kind')=='transaction' and r.get('principal_diagnostic')];last=diagnostics[-1] if diagnostics else None;failedmetric=last is not None and (not last['principal_diagnostic']['holds'] or not last['principal_diagnostic']['unadjusted_holds']);result.update(status='STRICT_PRINCIPAL_DIAGNOSTIC_FAILURE' if failedmetric else 'SETUP_CLOCK_CALIBRATION_OR_NATIVE_FAILURE',error=traceback.format_exc(),stopped_phase=phase(active_fixture),last_principal=None if last is None else dict(reference=reference(last),diagnostic=last['principal_diagnostic']),unrun_cuts=[m for m in [1,1000,4000,16000,40000,80000] if m not in [c['margin'] for c in result['cuts']]])
 finally:
  v=None;gc.collect();result=finalize(out,result,before)
 print(json.dumps(result,indent=2));return 0 if result['status']=='BOUNDED_CHARACTERIZATION_COMPLETE_NO_STAGE_ACCEPTANCE' else 1
if __name__=='__main__':raise SystemExit(main())
