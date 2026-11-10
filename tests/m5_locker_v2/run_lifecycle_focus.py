"""Genuine later capital, current NFT holder, both positions and fee-only SOL."""
import argparse,traceback,gc
from runtime import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);a=p.parse_args();integrity(a.fixture);out=OUT/a.label;before=freeze(out);result=dict(status='INCOMPLETE',command=sys.argv);vm=None
 try:
  vm=VM('lifecycle');vm.setup_pool();vm.lock();vm.position_start();vm.receipts();vm.accrue();creator=vm.collect_creator();first=vm.claim();vm.unwrap(0,first['claim_accounting']['net'][0],late=True);vm.unwrap(creator['creator_accounting']['net'][0],first['claim_accounting']['net'][0]);vm.deposit_B();vm.secondary_lock();state2=bytes(vm.account('lock_state_2').data);vm.nft_transfer();vm.accrue(later=True);transferred=vm.claim(variant='transferred');assert bytes(vm.account('lock_state_2').data)==state2;vm.nft_transfer(False);vm.accrue(later=True)
  # Recreate only the legitimately closed wSOL dedicated receipt, with actual System rent/init.
  d=PROFILE['derivations']['locker_receipt_wsol'];vm.send('recreate_closed_wsol_receipt',[create_account_with_seed(dict(from_pubkey=K['payer'],to_pubkey=K['locker_receipt_wsol'],base=K['payer'],seed=d['seed_UTF8'],lamports=vm.svm.minimum_balance_for_rent_exemption(165),space=165,owner=K['legacy_token'])),ix('legacy_token',bytes([18])+bytes(K['beneficiary']),[am('locker_receipt_wsol',w=True),am('wsol_mint')])]);returned=vm.claim();state1=bytes(vm.account('lock_state_1').data);secondary=vm.claim(variant='secondary');assert bytes(vm.account('lock_state_1').data)==state1 and amt(vm.account('unrelated_lp'))==5000000000
  result.update(status='LIFECYCLE_PASS',claims=[r['claim_accounting'] for r in [first,transferred,returned,secondary]],principal=[r['principal_diagnostic'] for r in [first,transferred,returned,secondary]])
  if not all(x['holds'] for x in result['principal']):result['status']='MATERIAL_PRINCIPAL_DIAGNOSTIC_VIOLATION'
 except BaseException:result.update(status='FAILURE',error=traceback.format_exc())
 finally:
  if vm is not None:del vm;gc.collect()
  save_trace(out/'events.json.gz',EVENTS);assert source_inputs()==before;result.update(instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],source_unchanged=True,resources=resources());save(out/'RESULT.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ['claims','principal']},indent=2));return 0 if result['status']=='LIFECYCLE_PASS' else 1
if __name__=='__main__':raise SystemExit(main())
