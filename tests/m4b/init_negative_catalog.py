import json,sys,traceback
from amm import *
def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);v=None;cases={}
 try:
  v=AMM(label);base=v.native_instruction('initialize_v2');bad={}
  bad['wrong_discriminator']=ix(K['amm'],bytes(8)+bytes(base.data)[8:],list(base.accounts))
  bad['wrong_count']=ix(K['amm'],bytes(base.data),list(base.accounts)[:-1])
  for name,index,key in [('wrong_mint',4,K['mint']),('wrong_token_program',15,K['token2022']),('wrong_pool',3,K['proof_marker'])]:
   metas=list(base.accounts);old=metas[index];metas[index]=am(key,w=old.is_writable,s=old.is_signer);bad[name]=ix(K['amm'],bytes(base.data),metas)
  metas=list(base.accounts);metas[4],metas[5]=metas[5],metas[4];bad['wrong_mint_order']=ix(K['amm'],bytes(base.data),metas)
  for name,op in bad.items():
   row=v.send('init_'+name,[op],[v.g],observe=True);assert row['status']=='FAILURE';cases[name]=dict(error=row['error'],logs=row['logs'])
  a=v.account('amm_config');v.svm.set_account(K['amm_config'],Account(a.lamports,bytes(a.data),K['legacy_token']));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case='config_owner',positive_monetary_proof=False));row=v.send('init_wrong_config_owner',[base],[v.g],observe=True);assert row['status']=='FAILURE';cases['wrong_config_owner']=dict(error=row['error'],logs=row['logs'])
  status='OBSERVED_NATIVE_ERROR_CATALOG_ONLY_NOT_FINAL_SUITE'
 except BaseException:status='FAIL';cases['exception']=traceback.format_exc()
 finally:
  if v:v.events_to(out/'events.json')
  save(out/'CATALOG.json',dict(status=status,cases=cases));print(json.dumps(dict(status=status,cases=cases)))
 return 0 if status!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
