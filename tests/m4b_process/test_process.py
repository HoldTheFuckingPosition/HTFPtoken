"""Actual H native processing/F17/volume/settlement; no mock monetary outcome."""
from runtime import *
import unittest,io,traceback,importlib.util,random
from solders.keypair import Keypair
ORACLE=load_module('stage_c_fraction_oracle',ROOT/'evidence/m4b/supervisor/volume_oracle.py')
PARAMS=ORACLE.Parameters.from_profile(PROFILE);COMPARISONS=[];COVERAGE=[]
def clone(op,data=None,accounts=None):return ix(op.program_id,bytes(op.data) if data is None else data,list(op.accounts) if accounts is None else accounts)
def events(row,tag):
 stack=[];found=[]
 for line in row['logs']:
  if line.startswith('Program ') and ' invoke [' in line:stack.append(line.split()[1])
  elif line.startswith('Program ') and (' success' in line or ' failed:' in line):
   if stack and stack[-1]==line.split()[1]:stack.pop()
  elif line.startswith('Program data: ') and stack and stack[-1]==str(K['program']):
   raw=base64.b64decode(line.split(': ',1)[1])
   if raw[:10]==b'HTFPEVT1\1'+bytes([tag]):found.append(raw)
 return found
class ProcessTests(unittest.TestCase):
 def make(self,name='',tax_gross=200000000000,initialize=True):
  v=AMM(self.id().split('.')[-1]+name);v.initialize_pool();v.burn_initial();v.clock(9,16352,1700000000);v.prepare_tax(tax_gross)
  if initialize:v.initialize_processing()
  return v
 def compare(self,v,q,error=None,payer=None,extra=(),nonce=None,cu=1400000):
  before=v.view('volume');r=v.view('inventory')['R'];pool=bytes(v.account('pool').data);fees=[struct.unpack_from('<Q',pool,p)[0] for p in [349,365,405]];amount=token_amount(v.account('vault_htfp'));now=v.svm.get_clock().unix_timestamp
  state=ORACLE.VolumeState.from_scaled(before['credit_scaled'],before['last_refill'],before['sequence'],PARAMS);request=ORACLE.Request(now,q,r,amount,*fees)
  row=v.send('actual_H_Process_Q_'+str(q),[v.process_ix(q,payer),*extra,v.finish(nonce)],[] if payer is None or payer==v.i else [payer],expected=error,cu=cu)
  after=v.view('volume');observed=dict(credit_scaled=after['credit_scaled'],last_refill=after['last_refill'],sequence=after['sequence'],recovered_R=v.view('inventory')['R']);comparison=ORACLE.compare_observation(PARAMS,state,request,observed,successful=error is None);self.assertTrue(comparison['matches'],comparison)
  COMPARISONS.append(dict(case=v.label,Q=q,actual_runtime_now=now,before=before,after=observed,comparison=comparison,status=row['status'],message_sha256=row['transaction_sha256']))
  if error is None:
   pe=events(row,3);self.assertEqual(len(pe),1);self.assertEqual(len(pe[0]),362);self.assertEqual(v.view('inventory')['guard'],0);self.assertEqual(after['active'],0)
  return row
 def corrupt(self,v,role,change,reason):
  a=v.account(role);d=bytearray(a.data);result=change(d,a.lamports,a.owner);d,l,o=(d,a.lamports,a.owner) if result is None else result;v.svm.set_account(v.tracked[role],Account(l,bytes(d),o,a.executable,a.rent_epoch));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_REJECTION_FIXTURE',role=role,reason=reason,data_hex=bytes(d).hex(),lamports=l,owner=str(o),positive_monetary_proof=False))
 def test_happy_donation_and_native_fee_separation(self):
  for donation in [False,True]:
   v=self.make('-'+str(donation))
   if donation:v.transfer_htfp(K['genesis_holding'],K['custody'],5000000000,v.g)
   s0=v.view('mint')['supply'];r0=v.svm.get_balance(K['reserve']) or 0;row=self.compare(v,16000000000);self.assertEqual(v.view('mint')['supply'],s0-6000000000);self.assertEqual(v.view('inventory')['R'],0);self.assertEqual(v.view('custody')['spendable'],4600000000 if donation else 0);self.assertEqual(v.view('custody')['withheld'],400000000 if donation else 0);self.assertEqual(withheld(v.account('vault_htfp')),800000000);self.assertEqual(v.view('mint')['mint_withheld'],0);self.assertGreater(v.svm.get_balance(K['reserve'])-r0,0)
 def test_permissionless_bootstrap_replay_and_standalone_redeem(self):
  v=self.make(initialize=False);self.assertIsNone(v.account('volume'));v.initialize_processing(v.g);self.assertEqual(v.view('volume')['credit_scaled'],30000000000)
  v.send('bootstrap_replay_reject',[ix(K['program'],b'HTFP\1\4',[am(K['config']),am(K['inventory'],w=True),am(K['volume'],w=True),am(v.g.pubkey(),w=True,s=True),am(K['system'])])],[v.g],expected=7017)
  bare=VM('standalone_redemption');bare.clock(7,4064,1699999970);m3.VM.genesis(bare);bare.send('initialize_only',[m3.VM.initialize_ix(bare)]);bare.send('fund_reserve_and_payee',[native_transfer(bare.i.pubkey(),K['reserve'],10**9),native_transfer(bare.i.pubkey(),bare.g.pubkey(),10**9)]);bare.send('redeem_without_Volume_or_pool',[bare.redeem_ix(10**17)],[bare.g]);self.assertIsNone(bare.account('volume'));self.assertIsNone(bare.account('pool'))
 def test_multiple_process_payers_temps_and_redeem_preserve_frame(self):
  for redeem in [False,True]:
   v=self.make('-'+str(redeem));operations=[v.process_ix(8000000000,sequence=0)]
   if redeem:operations.append(v.redeem_ix(10**15))
   operations += [v.process_ix(8000000000,payer=v.g,sequence=1),v.finish(1)];row=v.send('two_real_Processes_shared_tail',operations,[v.g]);pe=events(row,3);self.assertEqual(len(pe),2);self.assertEqual([struct.unpack_from('<Q',e,354)[0] for e in pe],[1,1]);self.assertNotEqual(pe[0][74:106],pe[1][74:106]);self.assertEqual(v.view('volume')['sequence'],2);self.assertEqual(v.view('volume')['credit_scaled'],0);self.assertEqual(v.view('inventory'),dict(R=0,guard=0));self.assertEqual(v.view('volume')['active'],0)
 def test_same_transaction_recycling_rejected_and_same_slot_later_allowed(self):
  for harvest in [False,True]:
   v=self.make('-'+str(harvest));ops=[v.process_ix(8000000000)]
   if harvest:ops.append(ix(K['token2022'],bytes([26,4]),[am(K['mint'],w=True),am(K['vault_htfp'],w=True)]))
   ops += [v.recover_ix([] if harvest else [K['vault_htfp']]),v.process_ix(400000000,sequence=1),v.finish(1)];v.send('actual_sale_fee_recycling_blocked',ops,expected=7021);self.assertEqual(v.view('inventory')['R'],16000000000);self.assertEqual(withheld(v.account('vault_htfp')),0)
  v=self.make('-independent');self.compare(v,8000000000);slot=v.svm.get_clock().slot;v.send('next_independent_same_slot_recovery',[v.recover_ix([K['vault_htfp']])]);self.assertEqual(v.view('inventory')['R'],8400000000);self.compare(v,400000000,payer=v.g);self.assertEqual(v.svm.get_clock().slot,slot);self.assertEqual(v.view('inventory')['guard'],0)
 def test_wallet_and_nested_actual_processing(self):
  for scenario in [0,4]:
   v=self.make('-'+str(scenario));v.load_wallet();row=v.send('genuine_wallet_Process',[v.wallet(scenario),v.finish()]);self.assertEqual(v.view('inventory')['R'],0);self.assertEqual(v.view('volume')['sequence'],1);self.assertEqual(len(events(row,3)),1)
  for scenario in [1,5,8,9]:
   v=self.make('-error'+str(scenario));v.load_wallet();code=7022 if scenario==9 else 7021;v.send('wallet_recycling_or_CPI_finalize_reject',[v.wallet(scenario),v.finish()],expected=code);self.assertEqual(v.view('inventory')['R'],16000000000);self.assertEqual(v.view('volume')['sequence'],0)
 def test_two_wallet_processes_share_first_nonce_and_distinct_temps(self):
  v=self.make();v.load_wallet();row=v.send('two_wallet_Processes_shared_direct_tail',[v.wallet(0,8000000000,sequence=0),v.wallet(0,8000000000,payer=v.g,sequence=1),v.finish(1)],[v.g]);pe=events(row,3);self.assertEqual(len(pe),2);self.assertEqual([struct.unpack_from('<Q',e,354)[0] for e in pe],[1,1]);self.assertNotEqual(pe[0][74:106],pe[1][74:106]);self.assertEqual(v.view('inventory'),dict(R=0,guard=0));self.assertEqual(v.view('volume')['sequence'],2);self.assertEqual(v.view('volume')['active'],0)
 def test_initial_failed_wallet_child_attempt_ignore_then_idle_final(self):
  v=self.make();v.load_wallet();slot=v.svm.get_clock().slot;before=v.view('volume');row=v.send('initial_failed_Process_attempt_ignore_before_idle_final',[v.wallet(10,q=0),v.finish(1)],expected=7006);self.assertEqual(v.view('volume'),before);self.assertEqual(v.view('inventory'),dict(R=16000000000,guard=0));self.assertEqual(events(row,3),[]);self.assertTrue(row['rollback_verified'])
  row=v.send('independent_same_slot_wallet_Process_after_failed_child',[v.wallet(0),v.finish(1)]);self.assertEqual(v.svm.get_clock().slot,slot);self.assertEqual(v.view('inventory'),dict(R=0,guard=0));self.assertEqual(len(events(row,3)),1)
 def test_direct_wallet_crossings_and_idle_final(self):
  v=self.make();v.load_wallet();v.send('wallet_no_child_valid_idle_final',[v.wallet(6),v.finish()]);self.assertEqual(v.view('volume')['sequence'],0)
  v.send('direct_Process_then_wallet_Recover',[v.process_ix(),v.wallet(2),v.finish()],expected=7021)
  v.send('wallet_Process_then_direct_Recover',[v.wallet(0),v.recover_ix(),v.finish()],expected=7021)
  v.send('wallet_cannot_be_last_cleanup',[v.process_ix(),v.wallet(3)],expected=7022)
  v.send('CPI_finalize_early_before_real_final',[v.process_ix(),v.wallet(3),v.finish()],expected=7022)
 def test_tail_wire_nonce_meta_and_promotion(self):
  v=self.make();v.send('missing_final',[v.process_ix()],expected=7021);v.send('wrong_nonce',[v.process_ix(),v.finish(2)],expected=7021);v.send('early_finalize',[v.process_ix(),v.finish(1),v.finish(1)],expected=7022)
  for kind in ['tag','version','length','count','order','key']:
   final=v.finish();d=bytearray(final.data);metas=list(final.accounts)
   if kind=='tag':d[5]=4
   if kind=='version':d[4]=2
   if kind=='length':d+=b'\0'
   if kind=='count':metas=metas[:-1]
   if kind=='order':metas[1],metas[2]=metas[2],metas[1]
   if kind=='key':metas[2]=am(K['inventory'],w=True)
   v.send('bad_tail_'+kind,[v.process_ix(),clone(final,bytes(d),metas)],expected=7022)
  final=v.finish();metas=list(final.accounts);metas[1]=am(K['inventory']);row=v.send('legitimate_writable_promotion',[v.process_ix(),clone(final,accounts=metas)]);self.assertEqual(v.view('inventory')['guard'],0)
 def test_native_state_precedes_invalid_amount_and_other_state_rejections(self):
  cases=[('pool_owner',7025),('pool_layout',7025),('config_hash',7025),('volume_binding',7018),('volume_reserved',7019),('inflight',7012),('barrier_no_frame',7021),('unknown_guard',7002),('sequence_max',7026)]
  for kind,code in cases:
   v=self.make('-'+kind)
   if kind=='pool_owner':self.corrupt(v,'pool',lambda d,l,o:(d,l,K['system']),kind)
   if kind=='pool_layout':self.corrupt(v,'pool',lambda d,l,o:(d[:-1],l,o),kind)
   if kind=='config_hash':self.corrupt(v,'amm_config',lambda d,l,o:(d[:-1]+bytes([d[-1]^1]),l,o),kind)
   if kind=='volume_binding':self.corrupt(v,'volume',lambda d,l,o:(d[:11]+bytes(32)+d[43:],l,o),kind)
   if kind=='volume_reserved':self.corrupt(v,'volume',lambda d,l,o:(d[:80]+b'\1'+d[81:],l,o),kind)
   if kind in ['inflight','barrier_no_frame','unknown_guard']:self.corrupt(v,'inventory',lambda d,l,o:(d[:11]+bytes([{'inflight':3,'barrier_no_frame':2,'unknown_guard':8}[kind]])+d[12:],l,o),kind)
   if kind=='sequence_max':self.corrupt(v,'volume',lambda d,l,o:(d[:59]+struct.pack('<Q',(1<<64)-1)+d[67:],l,o),kind)
   q=0 if kind.startswith('pool_') else 400;nonce=1;v.send('reject_native_state_'+kind,[v.process_ix(q),v.finish(nonce)],expected=code)
 def test_invalid_Q_zero_native_output_and_aliases(self):
  v=self.make()
  for q in [0,1,7,16000000001,(1<<64)-1]:self.compare(v,q,error=7006)
  for q in [8,200]:self.compare(v,q,error=2505)
  for kind in ['alias','missing_signature','fake_sysvar']:
   call=v.process_ix();metas=list(call.accounts)
   if kind=='alias':metas[7]=am(K['reserve'],w=True);code=7003
   if kind=='missing_signature':metas[9]=am(v.g.pubkey(),w=True);code=7005
   if kind=='fake_sysvar':metas[14]=am(v.g.pubkey());code=7001
   v.send('reject_'+kind,[clone(call,accounts=metas),v.finish()],expected=code)
 def test_per_call_and_global_exact_one_over_limits(self):
  v=self.make('-alpha');v.swap(False,10**9);d=bytes(v.account('pool').data);x=token_amount(v.account('vault_htfp'))-sum(struct.unpack_from('<Q',d,p)[0] for p in [349,365,405]);k=(x//1000)//5;self.compare(v,(k+1)*8,error=7020);self.compare(v,k*8)
  v=self.make('-global',tax_gross=400000000000);self.compare(v,8000000000);self.compare(v,8000000008,error=7020);self.compare(v,8000000000)
 def test_fractional_refill_equal_backward_and_pre_anchor(self):
  v=self.make('-fractional',tax_gross=400000000000);self.compare(v,16000000000);self.compare(v,400,error=7020)
  for offset,credit in [(1,5),(2,10)]:
   v.clock(9,16352+offset,1700000000+offset);self.compare(v,2666664);self.assertEqual(v.view('volume')['credit_scaled'],credit)
  v=self.make('-backwards');self.compare(v,8000000000);v.clock(9,16353,1699999999);self.compare(v,400);self.assertEqual(v.view('volume')['last_refill'],1700000000)
  v=self.make('-preanchor');v.clock(9,16353,1699999999);self.compare(v,16000000000);self.assertEqual(v.view('volume')['last_refill'],1700000000)
 def test_saturation_does_not_bank_time_and_extreme_timestamps(self):
  v=self.make(tax_gross=800000000000);v.clock(9,16353,1701000000);self.compare(v,16000000000);self.compare(v,400,error=7020);v.clock(9,16354,1701000060);self.compare(v,160000000);self.assertEqual(v.view('volume')['credit_scaled'],0)
  v.clock(9,16355,(1<<63)-1);self.compare(v,8000000000);v.clock(9,16356,-(1<<63));self.compare(v,400);self.assertEqual(v.view('volume')['last_refill'],(1<<63)-1)
 def test_actual_H_prefund_and_small_reserve_matrix(self):
  for p_kind in ['zero','L-1','L','L+1','2L+17','large']:
   for q in [400,16000000000]:
    v=self.make('-'+p_kind+'-Q'+str(q));l=v.svm.minimum_balance_for_rent_exemption(165);p={'zero':0,'L-1':l-1,'L':l,'L+1':l+1,'2L+17':2*l+17,'large':10**12}[p_kind];temp=v.temp(0);v.track('prefund_temp',temp)
    if p:v.send('genuine_H_temp_prefund',[native_transfer(v.i.pubkey(),temp,p)])
    row=self.compare(v,q);event=events(row,3)[0];self.assertEqual(struct.unpack_from('<Q',event,274)[0],p);a=v.svm.get_account(temp);self.assertTrue(a is None and p==0 or a.owner==K['system'] and len(a.data)==0 and a.lamports==p)
  for b in [0,890879,890880]:
   v=self.make('-reserve'+str(b));v.svm.set_account(K['reserve'],Account(b,b'',K['system']));v.events.append(dict(kind='SYNTHETIC_STARTING_SYSTEM_RESERVE',B=b,not_public_creation_proof=True));row=self.compare(v,400);self.assertEqual(v.svm.get_balance(K['reserve']),b+1)
 def test_prefund_rejection_and_intermediate_overflow(self):
  for kind,code in [('allocated_system',7023),('preowned_token',7023),('reserve_overflow',7010),('prefund_overflow',7010)]:
   v=self.make('-'+kind);temp=v.temp(0);v.track('malformed_temp',temp)
   if kind=='allocated_system':v.svm.set_account(temp,Account(3000000,bytes(4),K['system']))
   if kind=='preowned_token':v.svm.set_account(temp,Account(3000000,bytes(165),K['legacy_token']))
   if kind=='reserve_overflow':v.svm.set_account(K['reserve'],Account((1<<64)-1,b'',K['system']))
   if kind=='prefund_overflow':v.svm.set_account(temp,Account((1<<64)-1,b'',K['system']))
   v.events.append(dict(kind='EXPLICIT_STRUCTURAL_REJECTION_FIXTURE',case=kind,positive_monetary_proof=False));v.send('reject_'+kind,[v.process_ix(),v.finish()],expected=code)

def main(label,focus=None):
 out=OUT/label;out.mkdir(exist_ok=False);before=freeze(out);stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProcessTests)
 if focus:suite=unittest.TestSuite(t for t in suite if focus in t.id())
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);all_events=[e for v in ALL_VMS for e in v.events];save_gzip_events(out/'events.json.gz',all_events);save(out/'volume_comparisons.json',COMPARISONS);(out/'unittest.txt').write_text(stream.getvalue());assert all(file_sha(ROOT/p)==d for p,d in before.items())
 tx=[e for e in all_events if e['kind']=='transaction'];record=dict(status='PASS' if result.wasSuccessful() and result.testsRun and not result.skipped and all(not r.get('metadata_instrumentation_error') for r in tx) else 'FAIL',scope='FOCUSED' if focus else 'FULL_H_SUITE',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),details=[dict(test=str(t),traceback=e) for t,e in result.failures+result.errors],transactions=len(tx),native_negative_transactions=sum(e['status']=='FAILURE' for e in tx),independent_oracle_comparisons=len(COMPARISONS),source_unchanged=True,resources=resources(),limits=['Finite deterministic actual H tests, no public runtime/source equality','Captured native callees have no genuine H callback; actual in-flight callback runtime proof NOT_RUN, source/structural guard rejection distinguished'])
 save(out/'RESULT.json',record);print(stream.getvalue());print(json.dumps(record));return 0 if record['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None))
