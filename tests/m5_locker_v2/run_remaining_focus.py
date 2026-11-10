"""Corrected identical-state claim CU calibration and remaining late replay cases."""
import argparse,traceback,gc
from case_suite import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);a=p.parse_args();integrity(a.fixture);out=OUT/a.label;before=freeze(out);result=dict(status='INCOMPLETE',command=sys.argv);suite=Suite();v=None
 try:
  v=fresh('focused_claim_calibration',True,True);baseline=dict(pool=v.pool_view(),lock=bytes(v.account('lock_state_1').data).hex());calrow=v.claim();cal=calrow['compute_units'];del v;gc.collect();v=fresh('focused_claim_cuts',True,True);assert baseline==dict(pool=v.pool_view(),lock=bytes(v.account('lock_state_1').data).hex())
  for i,margin in enumerate([1,1000,4000,16000,40000,80000]):
   r=v.send('cut_claim_'+str(margin),[v.claim_ix()],[v.w],expected='OBSERVE',cu=max(5000,cal-margin));suite.record('L24',i+6,r,'diagnostic',{'calibration_CU':cal,'margin':margin,'identical_monetary_prestate':True});assert r['status']=='FAILURE' and ('ComputationalBudgetExceeded' in r['error'] or 'ProgramFailedToComplete' in r['error'])
  v.deposit_B();v.secondary_lock();suite.negative(v,'L25',0,v.lock_ix(),[v.w,v.signers['fee_key_mint_1']]);v.accrue(later=True);r=v.claim();suite.record('L25',1,r,extra=r['principal_diagnostic']);assert amt(v.account('unrelated_lp'))==5000000000;result['status']='REMAINING_FOCUS_PASS'
 except BaseException:result.update(status='INCOMPLETE_FAILURE',error=traceback.format_exc())
 finally:
  if v is not None:del v;gc.collect()
  save_trace(out/'events.json.gz',EVENTS);save(out/'CASES.json',suite.records);save(out/'CLASSIFICATIONS.json',suite.manifest);assert source_inputs()==before;result.update(instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],source_unchanged=True,resources=resources());save(out/'RESULT.json',result)
 print(json.dumps(result,indent=2));return 0 if result['status']=='REMAINING_FOCUS_PASS' else 1
if __name__=='__main__':raise SystemExit(main())
