"""Observe exact target rejection codes for the frozen mandatory bad-account cases."""
import json,sys,traceback
from amm import *

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);v=None;catalog={}
 try:
  v=AMM(label);v.initialize_pool();v.burn_initial();v.clock(9,16352,1700000000);v.swap(True,10**10)
  base=v.native_instruction('collect_creator_fee')
  cases={}
  for name,index,replacement,sign in [('wrong_creator',0,K['initializer'],True),('missing_creator_signature',0,K['genesis_owner'],False),('wrong_receiver',8,K['creator_htfp'],False),('wrong_share_key',14,K['initializer'],False),('wrong_program',10,K['system'],False),('wrong_mint',6,K['mint'],False)]:
   accounts=list(base.accounts);old=accounts[index];accounts[index]=am(replacement,w=old.is_writable,s=sign);cases[name]=ix(K['amm'],bytes(base.data),accounts)
  cases['wrong_count']=ix(K['amm'],bytes(base.data),list(base.accounts)[:-1])
  for name,instruction in cases.items():
   row=v.send(name,[instruction],[] if name in ['wrong_creator','missing_creator_signature'] else [v.g],observe=True);assert row['status']=='FAILURE';catalog[name]=dict(error=row['error'],logs=row['logs'])
  a=v.account('creator_wsol');v.svm.set_account(K['creator_wsol'],Account(a.lamports,bytes(a.data),K['system']));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case='wrong_creator_token_runtime_owner',positive_monetary_proof=False))
  row=v.send('wrong_owner',[base],[v.g],observe=True);assert row['status']=='FAILURE';catalog['wrong_owner']=dict(error=row['error'],logs=row['logs'])
  status='OBSERVED_NATIVE_ERROR_CATALOG_ONLY_NOT_FINAL_SUITE'
 except BaseException:status='FAIL';catalog['exception']=traceback.format_exc()
 finally:
  if v:v.events_to(out/'events.json')
  save(out/'CATALOG.json',dict(status=status,cases=catalog));print(json.dumps(dict(status=status,cases=catalog)))
 return 0 if status!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
