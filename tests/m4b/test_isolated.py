"""Genuine SBF settlement and transaction-wide kernel proofs; no H Process."""
import base64,json,struct,traceback,unittest,sys
from runtime import *
VM_EVENTS=[];OBSERVATIONS=[]
def guard(vm):return vm.account('proof_guard').data[11]
def volume(vm):return bytes(vm.account('proof_volume').data)
def seq(vm):return int.from_bytes(volume(vm)[59:67],'little')
def clone_ix(instruction,*,data=None,accounts=None):return ix(instruction.program_id,bytes(instruction.data) if data is None else data,list(instruction.accounts) if accounts is None else accounts)
class IsolatedTests(unittest.TestCase):
 def setUp(self):self.vms=[]
 def tearDown(self):
  for v in self.vms:VM_EVENTS.extend(v.events)
 def vm(self,suffix=''):
  v=VM(self.id().split('.')[-1]+suffix);self.vms.append(v);v.bootstrap();return v
 def test_actual_expired_blockhash_rejection(self):
  v=self.vm('-blockhash');block=v.svm.latest_blockhash();operations=[native_transfer(v.i.pubkey(),v.g.pubkey(),1000000)];tx=Transaction.new_signed_with_payer(operations,v.i.pubkey(),[v.i],block);v.svm.expire_blockhash();before=v.snapshot();result=v.svm.send_transaction(tx);self.assertIsInstance(result,FailedTransactionMetadata);self.assertIn('BlockhashNotFound',str(result.err()));self.assertEqual(v.snapshot(),before);meta=result.meta()
  v.events.append(dict(kind='transaction',fixture=v.label,name='actual_expired_blockhash_preflight',expected='BlockhashNotFound',status='FAILURE',error=str(result.err()),transaction_hex=bytes(tx).hex(),transaction_sha256=sha(bytes(tx)),message_hex=bytes(tx.message).hex(),message_version='legacy',recent_blockhash=str(block),packet_bytes=len(bytes(tx)),signatures=[str(s) for s in tx.signatures],signature_count=1,compute_units=meta.compute_units_consumed(),compute_unit_limit=1400000,heap_bytes=32768,signature_verification=True,blockhash_verification=True,fee_lamports=0,preflight_no_fee=True,rollback_verified=True,logs=meta.logs(),before=before,after=v.snapshot(),native_load=v.native,custom_program_artifacts=v.programs))
 def test_zero_output_prefund_matrix(self):
  rent=None
  for kind in ['zero','L-1','L','L+1','2L+17','large']:
   v=self.vm('-'+kind);l=v.svm.minimum_balance_for_rent_exemption(165);p={'zero':0,'L-1':l-1,'L':l,'L+1':l+1,'2L+17':2*l+17,'large':10**12}[kind]
   if p:v.send('genuine_prefund_temp',[native_transfer(v.i.pubkey(),K['proof_temp_sequence0'],p)])
   reserve0=v.account('proof_reserve').lamports;pay0=v.svm.get_balance(v.i.pubkey())
   e=v.send('native_close_refund_restore',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.proof_ix(5,b'\0'),v.finish()])
   self.assertEqual(v.account('proof_reserve').lamports,reserve0);temp=v.account('proof_temp_sequence0')
   if p:self.assertEqual((str(temp.owner),len(temp.data),temp.lamports),(str(K['system']),0,p))
   else:self.assertTrue(temp is None or temp.lamports==0 and len(temp.data)==0 and temp.owner==K['system'])
   self.assertEqual(v.svm.get_balance(v.i.pubkey()),pay0-e['fee_lamports']-1)
   self.assertEqual(guard(v),0);self.assertEqual(seq(v),1);self.assertEqual(volume(v)[67:80],bytes(13))
   events=[base64.b64decode(x.split(': ',1)[1]) for x in e['logs'] if x.startswith('Program data: ')]
   closed=next(x for x in events if x[:10]==b'M4BPEV01\1\5');self.assertEqual(len(closed),322)
   self.assertEqual(closed[266:298],bytes(K['system']));self.assertEqual(closed[298:314],bytes(16));self.assertEqual(struct.unpack_from('<Q',closed,314)[0],reserve0+p+max(0,l-p))
   OBSERVATIONS.append(dict(family='NATIVE_PREFUND_ZERO_OUTPUT',P=p,L=l,D=max(0,l-p),W0=max(0,p-l),O=0,immediate_postclose_owner='System',immediate_postclose_data_len=0,immediate_postclose_lamports=0,packet_bytes=e['packet_bytes'],compute_units=e['compute_units']))
 def test_new_sequence_uses_distinct_canonical_temp(self):
  v=self.vm('-sequences');l=v.svm.minimum_balance_for_rent_exemption(165);v.send('first_prefund',[native_transfer(v.i.pubkey(),K['proof_temp_sequence0'],l+1)]);v.send('first_complete_operation',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.proof_ix(5,b'\0'),v.finish()])
  next_temp,bump=Pubkey.find_program_address([b'm4b-proof-wsol',bytes(K['mint']),struct.pack('<Q',1)],K['proof_program']);self.assertNotEqual(next_temp,K['proof_temp_sequence0']);v.track('proof_temp_sequence1',next_temp);v.send('second_prefund',[native_transfer(v.i.pubkey(),next_temp,l-1)])
  v.send('old_temp_wrong_for_new_sequence',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.finish(2)],expected=8101)
  v.send('second_independent_sequence',[v.proof_ix(1,b'\0'),v.proof_ix(4,temp=next_temp),v.proof_ix(5,b'\0',temp=next_temp),v.finish(2)]);self.assertEqual(seq(v),2);self.assertEqual(v.account('proof_temp_sequence0').lamports,l+1);self.assertEqual(v.account('proof_temp_sequence1').lamports,l-1);self.assertEqual(guard(v),0)
 def test_distinct_deposit_and_fee_payer(self):
  v=self.vm();v.send('fund_alternate_payer',[native_transfer(v.i.pubkey(),v.g.pubkey(),10**9)])
  g0=v.svm.get_balance(v.g.pubkey());r0=v.account('proof_reserve').lamports
  e=v.send('alternate_storage_payer_refund',[v.proof_ix(1,b'\0'),v.proof_ix(4,payer=v.g),v.proof_ix(5,b'\0',payer=v.g),v.finish()],[v.g])
  self.assertEqual(v.svm.get_balance(v.g.pubkey()),g0);self.assertEqual(v.account('proof_reserve').lamports,r0);self.assertEqual(e['signature_count'],2)
 def test_late_failures_rollback_every_boundary(self):
  for boundary in [1,2,3]:
   v=self.vm('-'+str(boundary));l=v.svm.minimum_balance_for_rent_exemption(165);v.send('prefund',[native_transfer(v.i.pubkey(),K['proof_temp_sequence0'],l+1)])
   e=v.send('fail_boundary_'+str(boundary),[v.proof_ix(1,b'\0'),v.proof_ix(4),v.proof_ix(5,bytes([boundary])),v.finish()],expected=8108)
   self.assertTrue(e['rollback_verified']);self.assertEqual(guard(v),0);self.assertEqual(seq(v),0)
 def test_recovery_fence_and_multiple_probes(self):
  v=self.vm();v.send('recover_before_probe',[v.proof_ix(2)])
  v.send('probe_then_recovery_blocked',[v.proof_ix(1,b'\0'),v.proof_ix(2),v.finish()],expected=8105)
  v.send('two_probes_redeem_then_final',[v.proof_ix(1,b'\0'),v.proof_ix(3),v.proof_ix(1,b'\0'),v.finish()]);self.assertEqual(seq(v),2);self.assertEqual(guard(v),0)
  same_slot=v.svm.get_clock().slot
  v.send('next_independent_TX_same_slot',[v.proof_ix(2),v.proof_ix(1,b'\0'),v.finish(3)]);self.assertEqual(v.svm.get_clock().slot,same_slot);self.assertEqual(seq(v),3);self.assertEqual(guard(v),0)
 def test_bad_or_missing_final_tail(self):
  v=self.vm();v.send('missing_final',[v.proof_ix(1,b'\0')],expected=8105)
  v.send('wrong_nonce',[v.proof_ix(1,b'\0'),v.finish(2)],expected=8105)
  v.send('early_final',[v.proof_ix(1,b'\0'),v.finish(),v.finish()],expected=8106)
  memo=ix(Pubkey.from_string('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr'),b'after-final',[])
  v.send('instruction_after_final',[v.proof_ix(1,b'\0'),v.finish(),memo],expected=8106)
  for field in ['tag','length','count','key','flags']:
   final=v.finish()
   if field=='tag':data=bytearray(final.data);data[8]=5;final=clone_ix(final,data=bytes(data))
   if field=='length':final=clone_ix(final,data=bytes(final.data)+b'\0')
   if field=='count':final=clone_ix(final,accounts=list(final.accounts)[:-1])
   if field=='key':metas=list(final.accounts);metas[0]=am(v.g.pubkey(),s=True);final=clone_ix(final,accounts=metas)
   if field=='flags':metas=list(final.accounts);metas[1]=am(K['proof_guard']);final=clone_ix(final,accounts=metas)
   # Runtime globally promotes guard W because ProcessProbe writes it, so the flags case is a legitimate positive.
   if field=='flags':v.send('global_writable_promotion',[v.proof_ix(1,b'\0'),final]);self.assertEqual(guard(v),0)
   else:v.send('bad_final_'+field,[v.proof_ix(1,b'\0'),final],[v.g] if field=='key' else [],expected=8106)
 def test_fake_sysvar_and_bad_native_roles(self):
  v=self.vm();bad=v.proof_ix(1,b'\0');metas=list(bad.accounts);metas[5]=am(v.g.pubkey());bad=clone_ix(bad,accounts=metas)
  v.send('fake_sysvar',[bad,v.finish()],expected=8101)
  for index,key in [(8,K['amm']),(9,K['mint']),(7,K['proof_reserve'])]:
   op=v.proof_ix(4);metas=list(op.accounts);metas[index]=am(key,w=index==7,s=False);bad=clone_ix(op,accounts=metas)
   v.send('bad_settlement_role_'+str(index),[v.proof_ix(1,b'\0'),bad,v.finish()],expected=8101)
 def test_wallet_success_and_no_invocation_idle_final(self):
  v=self.vm();v.send('wallet_no_child_idle_tail',[v.wallet(6),v.finish()]);self.assertEqual(seq(v),0)
  v.send('wallet_probe_and_final',[v.wallet(0),v.finish()]);self.assertEqual(seq(v),1)
  v.send('two_wallet_probes_one_frame',[v.wallet(0,2),v.wallet(0,2),v.finish(2)]);self.assertEqual(seq(v),3)
  v.send('nested_wallet_probe',[v.wallet(4,4),v.finish(4)]);self.assertEqual(seq(v),4)
 def test_wallet_error_disposition_and_no_lock(self):
  for scenario,allowed in [(1,['8105']),(2,['8106']),(3,['8108']),(5,['8106']),(7,['8108'])]:
   v=self.vm('-'+str(scenario));e=v.send('actual_wallet_error_disposition',[v.wallet(scenario),v.finish()],observe=True)
   if e['status']=='FAILURE':self.assertTrue(any(x in e['error'] for x in allowed));self.assertTrue(e['rollback_verified']);self.assertEqual(seq(v),0)
   else:self.assertIn(scenario,[1,2,7]);self.assertTrue(any('attempted ignore' in x for x in e['logs']))
   self.assertEqual(guard(v),0);self.assertEqual(volume(v)[67:80],bytes(13));OBSERVATIONS.append(dict(family='WALLET_CPI_ERROR_DISPOSITION',scenario=scenario,status=e['status'],error=e['error']))
   v.send('next_TX_after_error',[v.proof_ix(2),v.proof_ix(1,b'\0'),v.finish(seq(v)+1)]);self.assertEqual(guard(v),0)
 def test_successful_probe_then_failed_wallet_probe_aborts_atomically(self):
  v=self.vm('-prior-success');row=v.send('successful_then_wallet_failed_probe',[v.proof_ix(1,b'\0'),v.wallet(7),v.finish()],expected=8108);self.assertTrue(row['rollback_verified']);self.assertEqual(seq(v),0);self.assertEqual(guard(v),0)
 def test_direct_wallet_recovery_and_cpi_final(self):
  v=self.vm();v.send('direct_then_wallet_recovery',[v.proof_ix(1,b'\0'),v.wallet(8),v.finish()],expected=8105)
  v.send('wallet_then_direct_recovery',[v.wallet(0),v.proof_ix(2),v.finish()],expected=8105)
  v.send('final_wallet_is_not_direct_tail',[v.proof_ix(1,b'\0'),v.wallet(5)],expected=8106)
  v.send('final_CPI_called_early',[v.proof_ix(1,b'\0'),v.wallet(5),v.finish()],expected=8106)
 def test_reentry_and_marker_failures(self):
  for mode in [0,1,2]:
   v=self.vm('-'+str(mode));e=v.send('actual_reentry',[v.proof_ix(7,bytes([mode])),v.finish()],observe=True)
   self.assertEqual(e['status'],'FAILURE');self.assertTrue('8104' in e['error'] or 'ReentrancyNotAllowed'in e['error']);self.assertEqual(guard(v),0);self.assertEqual(seq(v),0)
   OBSERVATIONS.append(dict(family='REENTRY',mode=mode,error=e['error']))
  v=self.vm('-late');v.send('after_native_marker_failure',[v.proof_ix(1,b'\1'),v.finish()],expected=8108)
  v.send('unclosed_settlement_final_rejects',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.finish()],expected=8107)
  v.send('late_native_System_error',[v.proof_ix(1,b'\0'),native_transfer(v.i.pubkey(),v.g.pubkey(),(1<<64)-1),v.finish()],expected='Custom(1)')
  v.send('actual_budget_exhaustion',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.proof_ix(5,b'\0'),v.finish()],expected='ComputationalBudgetExceeded',cu=5000)

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);import io
 stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(IsolatedTests);result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 save(out/'events.json',VM_EVENTS);save(out/'observations.json',OBSERVATIONS);(out/'unittest.txt').write_text(stream.getvalue())
 row=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),failure_details=[dict(test=str(t),traceback=e) for t,e in result.failures+result.errors],transactions=sum(e['kind']=='transaction' for e in VM_EVENTS),expected_negative_transactions=sum(e['kind']=='transaction' and e['status']=='FAILURE' for e in VM_EVENTS),resources=resources(),limitations=['Own kernel/authority only; no actual H Process/R/Volume/native sale integration','Positive receipt/CPMM dependency awaits native mint supplement','Finite deterministic cases, not exhaustive or automatic shrinking'])
 save(out/'RESULT.json',row);print(stream.getvalue());print(json.dumps(row));return 0 if row['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
