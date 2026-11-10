"""Captured binary AMM/LP/creator and actual-output settlement assertions."""
import base64,io,json,struct,sys,unittest,traceback,random
from amm import *
from quote_oracle import quote,token_tax
ALL_EVENTS=[];CHECKS=[]
def pool(v):
 a=v.account('pool');data=bytes(a.data);assert a.owner==K['amm'] and len(data)==637
 result={}
 for f in NABI['account_layouts']['PoolState']['fields']:
  raw=data[f['offset']:f['offset']+f['bytes']]
  if f['type'] in ['u64LE','u8','u8 bool']:result[f['name']]=int.from_bytes(raw,'little')
  elif f['type']=='pubkey':result[f['name']]=Pubkey.from_bytes(raw)
 return result
class ActualAMMTests(unittest.TestCase):
 def setUp(self):self.vms=[]
 def tearDown(self):
  for v in self.vms:ALL_EVENTS.extend(v.events)
 def vm(self,mode='primary',suffix=''):
  v=AMM(self.id().split('.')[-1]+suffix,mode=mode);self.vms.append(v);v.initialize_pool();return v
 def check_pool_bindings(self,v):
  p=pool(v)
  for field,role in [('amm_config','amm_config'),('pool_creator','genesis_owner'),('vault0','vault_wsol'),('vault1','vault_htfp'),('lp_mint','lp_mint'),('mint0','wsol_mint'),('mint1','mint'),('program0','legacy_token'),('program1','token2022'),('observation','observation')]:self.assertEqual(p[field],K[role])
  self.assertEqual((p['lp_decimals'],p['mint0_decimals'],p['mint1_decimals']),(9,9,7));self.assertEqual(p['auth_bump'],PROFILE['derivations']['amm_authority']['bump']);self.assertEqual(p['open_time'],1699999980)
  obs=v.account('observation');self.assertEqual((obs.owner,len(obs.data)),(K['amm'],4075));self.assertEqual(bytes(obs.data)[:8].hex(),NABI['account_discriminators']['ObservationState'])
  self.assertEqual(sha(bytes(v.account('amm_config').data)),NATIVE['raw_config0']['sha256']);self.assertEqual(supply(v.account('wsol_mint')),0)
 def checked_swap(self,v,htfp,n):
  p=pool(v);vi='vault_htfp' if htfp else 'vault_wsol';vo='vault_wsol' if htfp else 'vault_htfp';side=1 if htfp else 0
  input_role='creator_htfp' if htfp else 'creator_wsol';output_role='creator_wsol' if htfp else 'creator_htfp'
  x=token_amount(v.account(vi))-sum(p[f'{s}{side}'] for s in ['protocol','fund','creator_fee']);other=1-side;y=token_amount(v.account(vo))-sum(p[f'{s}{other}'] for s in ['protocol','fund','creator_fee'])
  expected=quote(n,x,y,htfp,bool(p['creator_fee_enabled']),p['creator_fee_side'],v.svm.get_clock().epoch>=9)
  ib=token_amount(v.account(input_role));ob=token_amount(v.account(output_role));iv=token_amount(v.account(vi));ov=token_amount(v.account(vo));iw=withheld(v.account(vi)) if htfp else 0;ow=withheld(v.account(output_role)) if not htfp else 0;S=supply(v.account('mint'))
  result=v.swap(htfp,n);after=pool(v)
  self.assertEqual(ib-token_amount(v.account(input_role)),n);self.assertEqual(token_amount(v.account(output_role))-ob,expected['recipient_out']);self.assertEqual(token_amount(v.account(vi))-iv,expected['actual_input']);self.assertEqual(ov-token_amount(v.account(vo)),expected['gross_out'])
  if htfp:self.assertEqual(withheld(v.account(vi))-iw,expected['native_in_tax'])
  else:self.assertEqual(withheld(v.account(output_role))-ow,expected['native_out_tax'])
  for s,field in [('protocol','protocol_fee'),('fund','fund_fee')]:self.assertEqual(after[f'{s}{side}']-p[f'{s}{side}'],expected[field])
  creator_side=side if expected['creator_fee_on_input'] else other
  self.assertEqual(after[f'creator_fee{creator_side}']-p[f'creator_fee{creator_side}'],expected['creator_fee']);self.assertEqual(after[f'creator_fee{1-creator_side}'],p[f'creator_fee{1-creator_side}'])
  self.assertEqual(supply(v.account('mint')),S);self.check_pool_bindings(v)
  for role in ['vault_wsol','creator_wsol']:
   a=v.account(role);self.assertEqual(a.lamports-token_amount(a),int.from_bytes(bytes(a.data)[113:121],'little'))
  CHECKS.append(dict(family='EXACT_INTEGER_QUOTE_VS_ACTUAL_NATIVE_DELTAS',mode=v.mode,htfp_in=htfp,input=n,effective_x=x,effective_y=y,oracle=expected,packet_bytes=result['packet_bytes'],CU=result['compute_units']))
 def checked_collect(self,v,permissionless=False):
  before=pool(v);r0=v.account('reserve');r0=None if r0 is None else (r0.lamports,bytes(r0.data));cust=bytes(v.account('custody').data)
  balances=[token_amount(v.account(x)) for x in ['creator_wsol','creator_htfp']];held=withheld(v.account('creator_htfp'));vaults=[token_amount(v.account(x)) for x in ['vault_wsol','vault_htfp']]
  result=v.collect(permissionless);after=pool(v)
  due=[before['creator_fee0'],before['creator_fee1']];self.assertGreater(sum(due),0)
  self.assertEqual(token_amount(v.account('creator_wsol'))-balances[0],due[0]);self.assertEqual(token_amount(v.account('creator_htfp'))-balances[1],due[1]-token_tax(due[1]));self.assertEqual(withheld(v.account('creator_htfp'))-held,token_tax(due[1]))
  for side,role in enumerate(['vault_wsol','vault_htfp']):
   self.assertEqual(vaults[side]-token_amount(v.account(role)),due[side]);self.assertEqual(after[f'creator_fee{side}'],0);self.assertEqual(after[f'protocol{side}'],before[f'protocol{side}'])
  current=v.account('reserve');self.assertEqual(None if current is None else (current.lamports,bytes(current.data)),r0);self.assertEqual(bytes(v.account('custody').data),cust)
  CHECKS.append(dict(family='CREATOR_AFTER_EXACT_INITIAL_BURN',mode=v.mode,permissionless=permissionless,native_gross_receipt0=due[0],native_gross_receipt1=due[1],native_HTFP_collection_tax=token_tax(due[1]),LP_creator_balance=token_amount(v.account('creator_lp')),LP_mint_supply=supply(v.account('lp_mint'))))
  v.collect(permissionless,expected=6014)
  return result
 def test_primary_two_postburn_collection_cycles(self):
  v=self.vm();self.check_pool_bindings(v);v.burn_initial();self.assertEqual(token_amount(v.account('creator_lp')),0);self.assertEqual(supply(v.account('lp_mint')),0);v.clock(9,16352,1700000000)
  for permissionless in [False,True]:self.checked_swap(v,True,10**10);self.checked_swap(v,False,10**9);self.checked_collect(v,permissionless)
 def test_fee_side_variants_native_tax_and_disabled(self):
  for mode in ['HTFP_tax_collection','both_input_fee','creator_disabled']:
   v=self.vm(mode);v.burn_initial();v.clock(9,16352,1700000000);self.checked_swap(v,True,10**10);self.checked_swap(v,False,10**9)
   if mode=='creator_disabled':self.assertEqual(pool(v)['creator_fee_enabled'],0);self.assertEqual(pool(v)['creator_fee0']+pool(v)['creator_fee1'],0);v.collect(expected=6014)
   else:self.checked_collect(v,mode=='both_input_fee')
 def test_later_and_third_party_LP_preserved(self):
  v=self.vm();v.send('genuine_CPMM_extra_LP_deposit',[v.native_instruction('deposit')],[v.g]);self.assertEqual(token_amount(v.account('creator_lp')),v.initial_receipt+1000000);self.assertEqual(pool(v)['lp_supply'],1000001000000)
  v.ata('other_lp','lp_mint','legacy_token',owner=v.i.pubkey());v.send('native_transfer_unrelated_LP',[ix(K['legacy_token'],bytes([12])+struct.pack('<QB',500000,9),[am(K['creator_lp'],w=True),am(K['lp_mint']),am(K['other_lp'],w=True),am(v.g.pubkey(),s=True)])],[v.g])
  v.burn_initial();self.assertEqual(token_amount(v.account('creator_lp')),500000);self.assertEqual(token_amount(v.account('other_lp')),500000);self.assertEqual(supply(v.account('lp_mint')),1000000)
  v.clock(9,16352,1700000000);self.checked_swap(v,True,10**10);self.checked_collect(v);self.assertEqual(token_amount(v.account('other_lp')),500000);self.assertEqual(token_amount(v.account('creator_lp')),500000)
 def test_actual_AMM_output_closes_to_proof_reserve(self):
  v=self.vm();v.burn_initial();v.clock(9,16352,1700000000);v.bootstrap();l=v.svm.minimum_balance_for_rent_exemption(165);p=l+1;v.send('prefund',[native_transfer(v.i.pubkey(),K['proof_temp_sequence0'],p)])
  r0=v.account('proof_reserve').lamports;pk=pool(v);x=token_amount(v.account('vault_htfp'))-sum(pk[f'{s}1'] for s in ['protocol','fund','creator_fee']);y=token_amount(v.account('vault_wsol'))-sum(pk[f'{s}0'] for s in ['protocol','fund','creator_fee']);expected=quote(10**10,x,y,True,True,1)
  ops=[v.proof_ix(1,b'\0'),v.proof_ix(4),v.swap_ix(True,10**10,K['proof_temp_sequence0']),v.proof_ix(5,b'\0'),v.finish()]
  result=v.send('actual_AMM_receipt_close_refund_restore',ops,[v.g]);o=v.account('proof_reserve').lamports-r0;self.assertEqual(o,expected['recipient_out']);self.assertGreater(o,0)
  a=v.account('proof_temp_sequence0');self.assertEqual((a.owner,len(a.data),a.lamports),(K['system'],0,p));self.assertEqual(v.account('proof_guard').data[11],0)
  CHECKS.append(dict(family='ACTUAL_CPMM_OUTPUT_NATIVE_CLOSE_REFUND_RESTORE',P=p,L=l,D=0,W0=1,O=o,packet_bytes=result['packet_bytes'],CU=result['compute_units'],native_quote=expected))
 def test_deterministic_swap_quantity_rounding_cases(self):
  v=self.vm();v.burn_initial();v.clock(9,16352,1700000000);rng=random.Random(0x4d3442)
  for htfp,n in [(True,250),(True,251),(True,10**7),(False,10**6),(False,10**9)]+[(bool(i%2),rng.randint(10**6,10**8)) for i in range(8)]:self.checked_swap(v,htfp,n)
  self.checked_collect(v)
 def test_initialization_ABI_account_negatives(self):
  v=AMM(self.id().split('.')[-1]);self.vms.append(v);base=v.native_instruction('initialize_v2')
  v.send('init_wrong_discriminator',[ix(K['amm'],bytes(8)+bytes(base.data)[8:],list(base.accounts))],[v.g],expected=101)
  v.send('init_wrong_count',[ix(K['amm'],bytes(base.data),list(base.accounts)[:-1])],[v.g],expected=3005)
  for name,index,key,code in [('wrong_mint',4,K['mint'],2003),('wrong_token_program',15,K['token2022'],2022),('wrong_pool',3,K['proof_marker'],2006)]:
   metas=list(base.accounts);old=metas[index];metas[index]=am(key,w=old.is_writable,s=old.is_signer);v.send('init_'+name,[ix(K['amm'],bytes(base.data),metas)],[v.g],expected=code)
  metas=list(base.accounts);metas[4],metas[5]=metas[5],metas[4];v.send('init_wrong_mint_order',[ix(K['amm'],bytes(base.data),metas)],[v.g],expected=2003)
  a=v.account('amm_config');v.svm.set_account(K['amm_config'],Account(a.lamports,bytes(a.data),K['legacy_token']));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case='config_owner',positive_monetary_proof=False));v.send('init_wrong_config_owner',[base],[v.g],expected=3007)
 def test_creator_account_constraint_negatives(self):
  v=self.vm();v.burn_initial();v.clock(9,16352,1700000000);self.checked_swap(v,True,10**10);base=v.native_instruction('collect_creator_fee')
  for name,index,key,sign,code in [('wrong_creator',0,K['initializer'],True,2015),('missing_creator_signature',0,K['genesis_owner'],False,3010),('wrong_receiver',8,K['creator_htfp'],False,2014),('wrong_share_key',14,K['initializer'],False,2006),('wrong_program',10,K['system'],False,3008),('wrong_mint',6,K['mint'],False,2014)]:
   metas=list(base.accounts);old=metas[index];metas[index]=am(key,w=old.is_writable,s=sign);v.send('creator_negative_'+name,[ix(K['amm'],bytes(base.data),metas)],[] if name in ['wrong_creator','missing_creator_signature'] else [v.g],expected=code)
  v.send('creator_wrong_count',[ix(K['amm'],bytes(base.data),list(base.accounts)[:-1])],[v.g],expected=3005)
  a=v.account('creator_wsol');v.svm.set_account(K['creator_wsol'],Account(a.lamports,bytes(a.data),K['system']));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case='creator_token_runtime_owner',positive_monetary_proof=False))
  row=v.send('creator_wrong_owner',[base],[v.g],expected=0);self.assertTrue(any('already in use' in x for x in row['logs']))
 def test_native_opening_and_zero_amount_constraints(self):
  v=self.vm();v.burn_initial();v.clock(8,8160,1699999979);v.send('native_pool_not_yet_open',[v.swap_ix(True,10**10)],[v.g],expected=6000)
  v.clock(9,16352,1700000000);v.send('native_swap_zero_input',[v.swap_ix(True,0)],[v.g],expected=2505)
  v.send('native_tax_consumes_tiny_input',[v.swap_ix(True,1)],[v.g],expected=2505)
  for n in [125,126]:v.send('native_discovered_zero_output_'+str(n),[v.swap_ix(True,n)],[v.g],expected=2505)

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ActualAMMTests))
 save(out/'events.json',ALL_EVENTS);save(out/'asserted_native_checks.json',CHECKS);(out/'unittest.txt').write_text(stream.getvalue())
 row=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),failure_details=[dict(test=str(t),traceback=e) for t,e in result.failures+result.errors],transactions=sum(e['kind']=='transaction' for e in ALL_EVENTS),asserted_negative_transactions=sum(e['kind']=='transaction' and e['status']=='FAILURE' for e in ALL_EVENTS),resources=resources(),limits=['Captured native binary integration in mixed local fixture, no public runtime/source equality','No H Process/Volume integration','External admin positive lifecycle NOT_RUN; actual authority unavailable'])
 save(out/'RESULT.json',row);print(stream.getvalue());print(json.dumps(row));return 0 if row['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
