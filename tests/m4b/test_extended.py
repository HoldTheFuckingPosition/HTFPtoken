"""Receipt/prefund products, explicitly labeled malformed-state rejection, rollback."""
import base64,io,json,struct,unittest,sys,traceback
from runtime import *
from solders.system_program import create_account_with_seed
from amm import AMM,token_amount,supply
EVENTS=[];CHECKS=[]
def prefund_values(l):return [0,l-1,l,l+1,2*l+17,10**12]
def raw_events(row,tag):return [base64.b64decode(x.split(': ',1)[1]) for x in row['logs'] if x.startswith('Program data: ') and base64.b64decode(x.split(': ',1)[1])[:10]==b'M4BPEV01\1'+bytes([tag])]
class Extended(unittest.TestCase):
 def setUp(self):self.vms=[]
 def tearDown(self):
  for v in self.vms:EVENTS.extend(v.events)
 def vm(self,suffix=''):
  v=VM(self.id().split('.')[-1]+suffix,native_mint=True);self.vms.append(v);v.bootstrap();return v
 def source(self,v,amount=100000000,settle=False):
  seed='m4b-native-receipt-v1' if not settle else 'm4b-native-zero-v1';key=Pubkey.create_with_seed(v.i.pubkey(),seed,K['legacy_token']);v.track('native_receipt_source',key);l=v.svm.minimum_balance_for_rent_exemption(165)
  create=create_account_with_seed(dict(from_pubkey=v.i.pubkey(),to_pubkey=key,base=v.i.pubkey(),seed=seed,lamports=l+amount,space=165,owner=K['legacy_token']))
  v.send('genuine_native_wrapped_source',[create,ix(K['legacy_token'],b'\x12'+bytes(K['proof_settle_authority'] if settle else v.i.pubkey()),[am(key,w=True),am(K['wsol_mint'])])]);return key
 def mutate(self,v,role,mutator,reason):
  before=v.account(role);raw=bytearray(before.data);lamports=before.lamports;owner=before.owner
  result=mutator(raw,lamports,owner)
  if result is None:result=(raw,lamports,owner)
  d,l,o=result;v.svm.set_account(v.tracked[role],Account(l,bytes(d),o,before.executable,before.rent_epoch))
  v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',role=role,reason=reason,before=dict(owner=str(owner),lamports=lamports,data_hex=bytes(before.data).hex()),after=dict(owner=str(o),lamports=l,data_hex=bytes(d).hex()),positive_monetary_proof=False))
 def test_positive_receipt_prefund_cartesian_product(self):
  for receipt in [1,10000000]:
   for which in range(6):
    v=self.vm(f'-{receipt}-{which}');source=self.source(v);l=v.svm.minimum_balance_for_rent_exemption(165);p=prefund_values(l)[which]
    if p:v.send('genuine_temp_prefund',[native_transfer(v.i.pubkey(),K['proof_temp_sequence0'],p)])
    r0=v.account('proof_reserve').lamports;i0=v.svm.get_balance(v.i.pubkey());source0=token_amount(v.account('native_receipt_source'))
    transfer=ix(K['legacy_token'],b'\x0c'+struct.pack('<QB',receipt,9),[am(source,w=True),am(K['wsol_mint']),am(K['proof_temp_sequence0'],w=True),am(v.i.pubkey(),s=True)])
    row=v.send('captured_native_receipt_close_refund_restore',[v.proof_ix(1,b'\0'),v.proof_ix(4),transfer,v.proof_ix(5,b'\0'),v.finish()]);self.assertEqual(v.account('proof_reserve').lamports,r0+receipt);self.assertEqual(v.svm.get_balance(v.i.pubkey()),i0-row['fee_lamports']-1);self.assertEqual(token_amount(v.account('native_receipt_source')),source0-receipt)
    temp=v.account('proof_temp_sequence0');self.assertTrue(temp is None and p==0 or temp is not None and temp.owner==K['system'] and len(temp.data)==0 and temp.lamports==p)
    event=raw_events(row,5)[0];self.assertEqual(event[266:298],bytes(K['system']));self.assertEqual(event[298:314],bytes(16));self.assertEqual(struct.unpack_from('<Q',event,94)[0],receipt)
    CHECKS.append(dict(family='PREFUND_X_GENUINE_CHECKED_RECEIPT',P=p,L=l,D=max(0,l-p),W0=max(0,p-l),O=receipt,packet=row['packet_bytes'],CU=row['compute_units']))
 def test_preexisting_temp_allocations_and_aliases(self):
  for kind in ['legacy_initialized','system_allocated','wrong_owner']:
   v=self.vm('-'+kind);source=self.source(v,0,True);a=v.account('native_receipt_source');l=a.lamports
   data=bytes(a.data) if kind!='system_allocated' else bytes(4);owner=K['legacy_token'] if kind=='legacy_initialized' else K['system'] if kind=='system_allocated' else K['token2022']
   v.svm.set_account(K['proof_temp_sequence0'],Account(l,data,owner));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case=kind,positive_monetary_proof=False))
   v.send('preexisting_temp_rejected',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.finish()],expected=8107)
  v=self.vm('-aliases');op=v.proof_ix(4);metas=list(op.accounts);metas[5]=am(K['proof_reserve'],w=True);v.send('temp_equals_reserve_rejected',[v.proof_ix(1,b'\0'),ix(op.program_id,bytes(op.data),metas),v.finish()],expected=8103)
  v.send('fund_real_alternate_payer',[native_transfer(v.i.pubkey(),v.g.pubkey(),10**9)])
  op=v.proof_ix(4,payer=v.g);metas=list(op.accounts);metas[7]=am(v.g.pubkey(),w=True);v.send('missing_alternate_payer_signature',[v.proof_ix(1,b'\0'),ix(op.program_id,bytes(op.data),metas),v.finish()],expected=8101)
  poor=self.vm('-poor');poor.send('fund_payer_rent_only',[native_transfer(poor.i.pubkey(),poor.g.pubkey(),poor.svm.minimum_balance_for_rent_exemption(0))]);poor.send('insufficient_exact_deposit',[poor.proof_ix(1,b'\0'),poor.proof_ix(4,payer=poor.g),poor.finish()],[poor.g],expected=8107)
 def test_native_state_faults_fail_before_close(self):
  for kind in ['wrong_mint','wrong_authority','native_none','wrong_native_reserve','delegate','close_authority','stale_amount','frozen']:
   v=self.vm('-'+kind);source=self.source(v,0,True);genuine=v.account('native_receipt_source');l=genuine.lamports
   # Complete native flow supplies exact record/header bytes. All following fabricated prestate is rejection-only.
   good=v.send('genuine_native_zero_receipt_baseline',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.proof_ix(5,b'\0'),v.finish()]);record=bytearray(raw_events(good,4)[0][10:]);record[11]=1;record[100:108]=struct.pack('<Q',v.svm.get_balance(v.i.pubkey())-5000+l)
   gd=bytearray(v.account('proof_guard').data);gd[11]=2;vd=bytearray(v.account('proof_volume').data);vd[67]=1;vd[68:72]=struct.pack('<HH',1,2);vd[72:80]=struct.pack('<Q',1)
   data=bytearray(genuine.data);lamports=l
   if kind=='wrong_mint':data[:32]=bytes(K['mint'])
   if kind=='wrong_authority':data[32:64]=bytes(v.g.pubkey())
   if kind=='native_none':data[109:113]=bytes(4)
   if kind=='wrong_native_reserve':data[113:121]=struct.pack('<Q',l+1)
   if kind=='delegate':data[72:76]=struct.pack('<I',1);data[76:108]=bytes(v.g.pubkey());data[121:129]=struct.pack('<Q',1)
   if kind=='close_authority':data[129:133]=struct.pack('<I',1);data[133:165]=bytes(v.g.pubkey())
   if kind=='stale_amount':lamports=l+1
   if kind=='frozen':data[108]=2
   for role,raw in [('proof_guard',gd),('proof_volume',vd),('proof_record',record)]:
    a=v.account(role);v.svm.set_account(v.tracked[role],Account(a.lamports,bytes(raw),a.owner))
   v.svm.set_account(K['proof_temp_sequence0'],Account(lamports,bytes(data),K['legacy_token']));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case=kind,record_source='actual prior OpenSettlement event',native_token_source='actual genuine zero-amount native token account',positive_monetary_proof=False))
   row=v.send('malformed_native_state_rejected_'+kind,[v.proof_ix(5,b'\0'),v.finish()],expected=8107);self.assertFalse(any('Instruction: CloseAccount' in line for line in row['logs']))
 def test_reserve_baselines_and_intermediate_overflow(self):
  for kind in ['reserve_overflow','prefund_overflow']:
   v=self.vm('-'+kind)
   if kind=='reserve_overflow':self.mutate(v,'proof_reserve',lambda d,n,o:(d,(1<<64)-1,o),kind)
   else:
    v.svm.set_account(K['proof_temp_sequence0'],Account((1<<64)-1,b'',K['system']));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case=kind,positive_monetary_proof=False))
   v.send('reject_'+kind,[v.proof_ix(1,b'\0'),v.proof_ix(4),v.finish()],expected=8109)
  for baseline_name in ['zero','under_rent','exempt','exempt_extra']:
   v=self.vm('-'+baseline_name);source=self.source(v);l0=v.svm.minimum_balance_for_rent_exemption(0);baseline={'zero':0,'under_rent':l0-1,'exempt':l0,'exempt_extra':l0+10000000}[baseline_name]
   v.svm.set_account(K['proof_reserve'],Account(baseline,b'',K['system']));v.events.append(dict(kind='SYNTHETIC_STARTING_BASELINE',role='proof_reserve',owner=str(K['system']),data_bytes=0,lamports=baseline,not_public_creation_proof=True,positive_token_or_supply_or_AMM_outcome_injected=False))
   receipt=10000000;transfer=ix(K['legacy_token'],b'\x0c'+struct.pack('<QB',receipt,9),[am(source,w=True),am(K['wsol_mint']),am(K['proof_temp_sequence0'],w=True),am(v.i.pubkey(),s=True)])
   payer0=v.svm.get_balance(v.i.pubkey());row=v.send('complete_native_baseline_'+baseline_name,[v.proof_ix(1,b'\0'),v.proof_ix(4),transfer,v.proof_ix(5,b'\0'),v.finish()]);self.assertEqual(v.account('proof_reserve').lamports,baseline+receipt);self.assertGreaterEqual(baseline+receipt,l0);self.assertEqual(v.svm.get_balance(v.i.pubkey()),payer0-row['fee_lamports']-1)
   event=raw_events(row,5)[0];self.assertEqual(struct.unpack_from('<Q',event,78)[0],v.svm.minimum_balance_for_rent_exemption(165));self.assertEqual(event[266:298],bytes(K['system']));self.assertEqual(event[298:314],bytes(16));CHECKS.append(dict(family='COMPLETE_NATIVE_RESERVE_STARTING_BASELINE',baseline=baseline_name,B=baseline,O=receipt,final_reserve=baseline+receipt,P=0,D=v.svm.minimum_balance_for_rent_exemption(165)))
 def test_frame_wire_and_reserved_rejections(self):
  for kind in ['guard_unknown','guard_inflight','volume_reserved','record_reserved','inactive_frame','future_nonce','zero_nonce','wrong_cleanup','sequence_exhausted','wrong_binding','wrong_bump','wrong_owner']:
   v=self.vm('-'+kind)
   if kind=='guard_unknown':self.mutate(v,'proof_guard',lambda d,n,o:(d[:11]+bytes([8])+d[12:],n,o),kind)
   elif kind=='guard_inflight':self.mutate(v,'proof_guard',lambda d,n,o:(d[:11]+bytes([1])+d[12:],n,o),kind)
   elif kind=='volume_reserved':self.mutate(v,'proof_volume',lambda d,n,o:(d[:80]+b'\1'+d[81:],n,o),kind)
   elif kind=='record_reserved':self.mutate(v,'proof_record',lambda d,n,o:(d[:204]+b'\1'+d[205:],n,o),kind)
   elif kind=='sequence_exhausted':self.mutate(v,'proof_volume',lambda d,n,o:(d[:59]+struct.pack('<Q',(1<<64)-1)+d[67:],n,o),kind)
   elif kind=='wrong_binding':self.mutate(v,'proof_volume',lambda d,n,o:(d[:11]+bytes(32)+d[43:],n,o),kind)
   elif kind=='wrong_bump':self.mutate(v,'proof_volume',lambda d,n,o:(d[:10]+bytes([d[10]^1])+d[11:],n,o),kind)
   elif kind=='wrong_owner':self.mutate(v,'proof_guard',lambda d,n,o:(d,n,K['legacy_token']),kind)
   else:
    gd=bytearray(v.account('proof_guard').data);gd[11]=2;a=v.account('proof_guard');v.svm.set_account(K['proof_guard'],Account(a.lamports,bytes(gd),a.owner));vd=bytearray(v.account('proof_volume').data);vd[59:67]=struct.pack('<Q',1);vd[67]=0 if kind=='inactive_frame' else 1;vd[68:72]=struct.pack('<HH',1,3 if kind=='wrong_cleanup' else 2);vd[72:80]=struct.pack('<Q',0 if kind=='zero_nonce' else 2 if kind=='future_nonce' else 1);a=v.account('proof_volume');v.svm.set_account(K['proof_volume'],Account(a.lamports,bytes(vd),a.owner));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case=kind,positive_monetary_proof=False))
   expected=8104 if kind=='guard_inflight' else 8109 if kind=='sequence_exhausted' else 8105 if kind in ['inactive_frame','future_nonce','zero_nonce','wrong_cleanup'] else 8102
   nonce=2 if kind=='future_nonce' else 0 if kind=='zero_nonce' else 1
   v.send('reject_'+kind,[v.proof_ix(1,b'\0'),v.finish(nonce)],expected=expected)
  v=self.vm('-wrong-pda');op=v.proof_ix(1,b'\0');metas=list(op.accounts);metas[2]=am(K['inventory'],w=True);v.send('wrong_volume_PDA',[ix(op.program_id,bytes(op.data),metas),v.finish()],expected=8101)
  v=self.vm('-missing-controller');v.send('fund_real_fee_payer',[native_transfer(v.i.pubkey(),v.g.pubkey(),10**9)]);op=v.proof_ix(1,b'\0');metas=list(op.accounts);metas[0]=am(v.i.pubkey(),w=True);tail=v.finish();fm=list(tail.accounts);fm[0]=am(v.i.pubkey());v.send('missing_controller_signature',[ix(op.program_id,bytes(op.data),metas),ix(tail.program_id,bytes(tail.data),fm)],payer=v.g,expected=8101)
  v=self.vm('-wire');bad=v.proof_ix(1,b'\0');data=bytearray(bad.data);data[7]=ord('2');v.send('bad_wire_version',[ix(bad.program_id,bytes(data),list(bad.accounts)),v.finish()],expected=8100)
  final=v.finish();metas=list(final.accounts);metas[1],metas[2]=metas[2],metas[1];v.send('wrong_tail_order',[v.proof_ix(1,b'\0'),ix(final.program_id,bytes(final.data),metas)],expected=8106)
 def test_genuine_unexplained_lamports_and_payer_state_changes(self):
  from solders.system_program import allocate
  v=self.vm('-stale');v.send('fund_distinct_actor',[native_transfer(v.i.pubkey(),v.g.pubkey(),10**9)])
  row=v.send('unexplained_lamports_after_native_init',[v.proof_ix(1,b'\0'),v.proof_ix(4),native_transfer(v.g.pubkey(),K['proof_temp_sequence0'],1),v.proof_ix(5,b'\0'),v.finish()],[v.g],expected=8107);self.assertFalse(any('Instruction: CloseAccount' in x for x in row['logs']))
  v=self.vm('-changed-payer');v.send('fund_distinct_storage_payer',[native_transfer(v.i.pubkey(),v.g.pubkey(),10**9)])
  op=allocate(dict(pubkey=v.g.pubkey(),space=8));v.send('payer_allocated_after_open',[v.proof_ix(1,b'\0'),v.proof_ix(4,payer=v.g),op,v.proof_ix(5,b'\0',payer=v.g),v.finish()],[v.g],expected=8101)
 def test_malformed_rent_input_rejected_by_runtime_cache(self):
  from solders.sysvar import RENT
  v=self.vm('-rent');a=v.svm.get_account(RENT)
  with self.assertRaisesRegex(Exception,'Invalid Rent sysvar data'):
   v.svm.set_account(RENT,Account(a.lamports,b'\0',a.owner,False))
  v.events.append(dict(kind='MALFORMED_RENT_RUNTIME_FIXTURE_REJECTION',actual_error='LiteSVMError: Invalid Rent sysvar data.',stage='before any SBF transaction with malformed sysvar',positive_monetary_proof=False,limitations='Harness/runtime cache validates structural sysvar input; this is not a handler custom-error or transaction rollback assertion'))
 def test_real_burn_and_swap_late_failure_rollback(self):
  for failure in ['after_burn','after_swap','after_close','after_refund','after_restore']:
   v=AMM(self.id().split('.')[-1]+'-'+failure);self.vms.append(v);v.initialize_pool();v.burn_initial();v.clock(9,16352,1700000000);v.bootstrap();p=v.svm.minimum_balance_for_rent_exemption(165)-1;v.send('prefund',[native_transfer(v.i.pubkey(),K['proof_temp_sequence0'],p)])
   burn=ix(K['token2022'],b'\x0f'+struct.pack('<QB',6000000000,7),[am(K['creator_htfp'],w=True),am(K['mint'],w=True),am(v.g.pubkey(),s=True)])
   if failure=='after_burn':operations=[burn,v.proof_ix(8)]
   else:
    operations=[burn,v.proof_ix(1,b'\0'),v.proof_ix(4),v.swap_ix(True,10**10,K['proof_temp_sequence0'])]
    if failure=='after_swap':operations += [v.proof_ix(8),v.proof_ix(5,b'\0')]
    else:operations += [v.proof_ix(5,bytes([{'after_close':1,'after_refund':2,'after_restore':3}[failure]]))]
    operations += [v.finish()]
   row=v.send('real_burn_swap_'+failure,operations,[v.g],expected=8108);self.assertTrue(row['rollback_verified']);self.assertTrue(any('Instruction: BurnChecked' in x for x in row['logs']))
   if failure!='after_burn':self.assertTrue(any('Instruction: SwapBaseInput' in x for x in row['logs']))
   CHECKS.append(dict(family='GENUINE_BURN_AND_SWAP_LATE_ROLLBACK',boundary=failure,rollback_verified=True,packet=row['packet_bytes'],CU=row['compute_units']))

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Extended))
 save(out/'events.json',EVENTS);save(out/'checks.json',CHECKS);(out/'unittest.txt').write_text(stream.getvalue());row=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),failure_details=[dict(test=str(t),traceback=e) for t,e in result.failures+result.errors],transactions=sum(e['kind']=='transaction' for e in EVENTS),asserted_negative_transactions=sum(e['kind']=='transaction' and e['status']=='FAILURE' for e in EVENTS),resources=resources(),limits=['Structural corruption is exclusively rejected negative fixture, no fabricated successful monetary outcomes','Separate own-kernel and direct actual native/AMM transactions, no H Process implementation'])
 save(out/'RESULT.json',row);print(stream.getvalue());print(json.dumps(row));return 0 if row['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
