"""Source-frozen real accrued claims and collection-order probe, no modeled positives."""
import argparse,traceback,gc
from runtime import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);args=p.parse_args();integrity(args.fixture);out=OUT/args.label;before=freeze(out);result=dict(status='INCOMPLETE',phase='ACCRUED_CLAIM_PREREQUISITE',fixture=FIXTURE,command=sys.argv);vm=None;branches=[]
 try:
  for order in ['creator_then_locker','locker_then_creator']:
   vm=VM(order);vm.setup_pool();vm.lock();vm.position_start();vm.receipts();vm.accrue();baseline=dict(pool=vm.pool_view(),state=bytes(vm.account('lock_state_1').data).hex(),receipts=[vm.token(r) for r in ['creator_wsol','creator_htfp','locker_receipt_wsol','locker_receipt_htfp']]);branch=dict(order=order,baseline=baseline);branches.append(branch)
   if order=='creator_then_locker':creator=vm.collect_creator();claim=vm.claim(observe=True)
   else:claim=vm.claim(observe=True);creator=vm.collect_creator()
   branch.update(creator=creator.get('creator_accounting'),claim_status=claim['status'],claim_error=claim['error'],claim=claim.get('claim_accounting'),principal=claim.get('principal_diagnostic'),final=vm.pool_view())
   if claim['status']!='SUCCESS':result['status']='MATERIAL_NATIVE_CLAIM_BLOCKER';break
   del vm;vm=None;gc.collect()
  if len(branches)==2 and all(b['claim_status']=='SUCCESS' for b in branches):
   assert branches[0]['baseline']==branches[1]['baseline'];compare={k:branches[0][k]==branches[1][k] for k in ['creator','claim','final']};result['order_comparison']=compare
   # The before/after claim pools differ by intentionally outstanding creator liabilities; compare actual payout fields.
   fields=['burn','gross','net','withheld'];same=all(branches[0]['claim'][k]==branches[1]['claim'][k] for k in fields);result['order_payouts_identical']=same;result['status']='PREREQUISITES_PASS' if same else 'MATERIAL_COLLECTION_ORDER_DISCREPANCY'
   if not all(b['principal']['holds'] for b in branches):result['status']='MATERIAL_PRINCIPAL_DIAGNOSTIC_VIOLATION'
 except BaseException:result.update(status='INSTRUMENTATION_OR_NATIVE_FAILURE',error=traceback.format_exc())
 finally:
  if vm is not None:del vm;gc.collect()
  save_trace(out/'events.json.gz',EVENTS);assert source_inputs()==before;result.update(branches=branches,instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],source_unchanged=True,resources=resources());save(out/'RESULT.json',result)
 print(json.dumps(result,indent=2));return 0 if result['status']=='PREREQUISITES_PASS' else 1
if __name__=='__main__':raise SystemExit(main())
