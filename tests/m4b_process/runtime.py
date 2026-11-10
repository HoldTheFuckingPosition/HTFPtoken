"""Explicit new H artifact adapter around frozen monetary/AMM drivers."""
from common import *
import importlib.util,struct,base64,types

def load_module(name,path,dependencies=None):
 old={k:sys.modules.get(k) for k in dependencies or {}}
 try:
  sys.modules.update(dependencies or {});spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
 finally:
  for k,v in old.items():
   if v is None:sys.modules.pop(k,None)
   else:sys.modules[k]=v
B=load_module('frozen_stage_b_common',ROOT/'tests/m4b/common.py')
R=load_module('frozen_stage_b_runtime',ROOT/'tests/m4b/runtime.py',{'common':B})
_native_mint=load_module('native_mint_fixture',ROOT/'tests/m4b/native_mint_fixture.py',{'common':B})
K=B.K;PROFILE=B.PROFILE;NATIVE=B.NATIVE;m3=R.m3
Pubkey=R.Pubkey;Account=R.Account;Clock=R.Clock;Instruction=R.Instruction;Transaction=R.Transaction;VersionedTransaction=R.VersionedTransaction;MessageV0=R.MessageV0;FailedTransactionMetadata=R.FailedTransactionMetadata
am=R.am;ix=R.ix;native_transfer=R.native_transfer
ALL_VMS=[]
class VM(R.VM):
 def __init__(self,label,build=None,load_h=True,native_mint=True):
  super().__init__(label,'build-003',False,native_mint)
  ALL_VMS.append(self)
  self.build_label=os.environ.get('PROCESS_BUILD','build-h4b-final-002');folder=OUT/self.build_label;record=json.loads((folder/'build.json').read_text());assert record['feature']=='local-m4b' and record['exit_status']=='0'
  for p,d in record['inputs_before_sha256'].items():
   if p.startswith('programs/htfp/') or p.startswith('config/'):assert file_sha(ROOT/p)==d,('stale current H build input',p)
  expected_sources={p for p in record['inputs_before_sha256'] if p.startswith('programs/htfp/src/')}
  assert expected_sources=={str(p.relative_to(ROOT)) for p in (ROOT/'programs/htfp/src').glob('*.rs')}
  path=folder/'htfp.so';data=path.read_bytes();assert sha(data)==record['elf_sha256'];self.svm.add_program(K['program'],data);assert bytes(self.svm.get_account(K['program']).data)==data
  self.programs['program']={'path':str(path.relative_to(ROOT)),'sha256':sha(data),'feature':'local-m4b','build_record':str((folder/'build.json').relative_to(ROOT)),'build_record_sha256':file_sha(folder/'build.json'),'H_source_sha256':{p:d for p,d in record['inputs_before_sha256'].items() if p.startswith('programs/htfp/')}}
  from solders.sysvar import CLOCK,RENT
  self.track('runtime_clock',CLOCK);self.track('runtime_rent',RENT)
  self._native_send=self.svm.send_transaction;self._last_inner=[];self._tx_count=0
  def capture(tx):
   result=self._native_send(tx);meta=result.meta() if isinstance(result,FailedTransactionMetadata) else result
   self._last_native_outcome=dict(status='FAILURE' if isinstance(result,FailedTransactionMetadata) else 'SUCCESS',error=str(result.err()) if isinstance(result,FailedTransactionMetadata) else None,compute_units=meta.compute_units_consumed())
   self._last_metadata_error=None
   try:self._last_inner=[[dict(program_id_index=i.instruction().program_id_index,accounts=list(i.instruction().accounts),data_hex=bytes(i.instruction().data).hex(),stack_height=i.stack_height()) for i in group] for group in meta.inner_instructions()]
   except Exception as error:self._last_inner=[];self._last_metadata_error=repr(error)
   return result
  self.svm.send_transaction=capture
 def actual_runtime(self):
  c=self.svm.get_clock();r=self.svm.get_rent()
  return dict(clock={k:getattr(c,k) for k in ['slot','epoch_start_timestamp','epoch','leader_schedule_epoch','unix_timestamp']},rent={**{k:getattr(r,k) for k in ['lamports_per_byte_year','exemption_threshold','burn_percent']},'minimum_balances':{str(n):self.svm.minimum_balance_for_rent_exemption(n) for n in [0,82,89,165,175,178,278]}})
 def send(self,*args,**kwargs):
  self._tx_count+=1
  if self._tx_count%32==1:resources()
  before=self.actual_runtime();n=len(self.events);addresses={r:str(k) for r,k in {**K,**self.tracked}.items()}
  try:return super().send(*args,**kwargs)
  finally:
   for row in self.events[n:]:
    if row['kind']=='transaction':row['actual_runtime_before']=before;row['actual_runtime_after']=self.actual_runtime();row['addresses']=addresses;row['actual_inner_instructions']=self._last_inner;row['native_outcome_before_formatting']=self._last_native_outcome;row['metadata_instrumentation_error']=self._last_metadata_error
 def view(self,role):
  a=self.account(role);raw=bytes(a.data)
  if role=='inventory':return dict(R=struct.unpack_from('<Q',raw,12)[0],guard=raw[11])
  if role=='volume':return dict(credit_scaled=struct.unpack_from('<Q',raw,43)[0],last_refill=struct.unpack_from('<q',raw,51)[0],sequence=struct.unpack_from('<Q',raw,59)[0],active=raw[67],origin=struct.unpack_from('<H',raw,68)[0],cleanup=struct.unpack_from('<H',raw,70)[0],nonce=struct.unpack_from('<Q',raw,72)[0])
  return m3.mint_view(raw) if role=='mint' else m3.token_view(raw)
 def initialize_processing(self,payer=None):
  payer=payer or self.i;return self.send('actual_H_InitializeProcessing',[ix(K['program'],b'HTFP\1\4',[am(K['config']),am(K['inventory'],w=True),am(K['volume'],w=True),am(payer.pubkey(),w=True,s=True),am(K['system'])])],[payer] if payer!=self.i else [])
 def temp(self,sequence):return Pubkey.find_program_address([b'htfp-tmp-wsol',bytes(K['mint']),struct.pack('<Q',sequence)],K['program'])[0]
 def process_ix(self,q=16000000000,payer=None,sequence=None):
  payer=payer or self.i;sequence=self.view('volume')['sequence'] if sequence is None else sequence;temp=self.temp(sequence);self.track('H_temp_'+str(sequence),temp);self.track('storage_payer_'+str(payer.pubkey()),payer.pubkey())
  names='config inventory volume mint custody tax_authority reserve temp settle_authority payer token2022 legacy_token wsol_mint system instructions_sysvar amm amm_config amm_authority pool vault_htfp vault_wsol observation'.split();mapping={**K,'temp':temp,'payer':payer.pubkey()};w={1,2,3,4,6,7,9,18,19,20,21}
  return ix(K['program'],b'HTFP\1\3'+struct.pack('<Q',q),[am(mapping[n],i in w,i==9) for i,n in enumerate(names)])
 def finish(self,nonce=None):
  nonce=self.view('volume')['sequence']+1 if nonce is None else nonce
  return ix(K['program'],b'HTFP\1\5'+struct.pack('<Q',nonce),[am(K['config']),am(K['inventory'],w=True),am(K['volume'],w=True),am(K['instructions_sysvar'])])
 def recover_ix(self,sources=()):return m3.VM.recover_ix(self,sources)
 def redeem_ix(self,*a,**kw):return m3.VM.redeem_ix(self,*a,**kw)
 def prepare_tax(self,amount=200000000000):
  holder=m3.VM.create_token(self,'fee_holder');m3.VM.token_transfer(self,holder,amount);self.send('actual_H_Recover',[self.recover_ix([holder])]);return holder
 def load_wallet(self):
  record=json.loads((OUT/'build-wallet-final/build.json').read_text());profile=json.loads((ROOT/'tests/m4b_process/wallet_profile.json').read_text());self.wallet_key=Pubkey.from_string(profile['program_id'])
  for p,d in record['inputs_before_sha256'].items():
   if p.startswith('tests/m4b_process/wallet/') or p=='tests/m4b_process/wallet_profile.json':assert file_sha(ROOT/p)==d
  data=(OUT/'build-wallet-final/htfp_process_wallet.so').read_bytes();assert sha(data)==record['elf_sha256'];self.svm.add_program(self.wallet_key,data);self.programs['H_wallet']=dict(path='evidence/m4b/process_author/build-wallet-final/htfp_process_wallet.so',sha256=sha(data),profile_sha256=file_sha(ROOT/'tests/m4b_process/wallet_profile.json'))
 def wallet(self,scenario,q=16000000000,nonce=None,payer=None,sequence=None):
  nonce=self.view('volume')['sequence']+1 if nonce is None else nonce
  call=self.process_ix(q,payer,sequence);metas=list(call.accounts)+[am(self.i.pubkey(),s=True),am(K['program']),am(self.wallet_key)]
  return ix(self.wallet_key,b'HTFPM4W1'+bytes([scenario])+struct.pack('<QQ',q,nonce),metas)
 def events_to(self,path):save_events(path,self.events)
# The exact retained AMM setup body runs against the new VM and its actual current H artifact.
namespace={'__name__':'stage_c_captured_AMM_adapter','__file__':str(ROOT/'tests/m4b/amm.py')}
source=(ROOT/'tests/m4b/amm.py').read_text();assert source.count('from runtime import *')==1
namespace.update(globals());exec(compile(source.replace('from runtime import *',''),str(ROOT/'tests/m4b/amm.py'),'exec'),namespace)
AMM=namespace['AMM'];token_amount=namespace['token_amount'];supply=namespace['supply'];withheld=namespace['withheld']
