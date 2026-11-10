"""Actual signed local transactions with raw deltas and fixed dependency identities."""
from pathlib import Path
import base64,json,os,struct,sys
from common import ROOT,OUT,K,PROFILE,NATIVE,MixedFixture,save,file_sha,sha,resources
from solders.account import Account
from solders.clock import Clock
from solders.instruction import AccountMeta,Instruction
from solders.transaction import Transaction,VersionedTransaction
from solders.message import MessageV0
from solders.transaction_metadata import FailedTransactionMetadata
from solders.compute_budget import set_compute_unit_limit,ComputeBudget
from solders.system_program import transfer,create_account
from solders.pubkey import Pubkey
sys.path.insert(0,str(ROOT/'tests/m3'))
import harness as m3
from evidence_policy import validate_artifact
M3_RECORD=ROOT/'evidence/m3/author/native-target/captured-full-001/environment.json'
M3_ARTIFACTS=json.loads(M3_RECORD.read_text())['artifacts']
def am(key,w=False,s=False):return AccountMeta(key,s,w)
def ix(program,data,metas):return Instruction(program,data,metas)
def native_transfer(source,dest,n):return transfer(dict(from_pubkey=source,to_pubkey=dest,lamports=n))
class VM:
 def __init__(self,label,build='build-003',load_h=False,native_mint=False):
  from solders.litesvm import LiteSVM
  self.label=label;self.svm=LiteSVM().with_sigverify(True).with_blockhash_check(True);self.fixture=MixedFixture();self.events=[]
  self.native=self.fixture.install(self.svm);self.i=m3.pubtest_signer(1);self.g=m3.pubtest_signer(3)
  assert self.i.pubkey()==K['initializer'] and self.g.pubkey()==K['genesis_owner']
  self.svm.airdrop(self.i.pubkey(),20_000_000_000_000)
  self.initializer=self.i;self.holder=self.g;self.mint_signer=m3.pubtest_signer(2)
  if native_mint:
   from native_mint_fixture import install
   self.events.append(install(self.svm))
  self.tracked={r:k for r,k in K.items() if r not in ['program','token2022','system','amm','legacy_token','associated_token','instructions_sysvar','proof_program','wallet_program']}
  self.programs={}
  record=json.loads((OUT/build/'BUILD.json').read_text());assert record['status']=='BUILD_PASS'
  for package,role in [('m4b_proof_kernel','proof_program'),('m4b_restricted_wallet','wallet_program')]:
   artifact=record['artifacts'][package];data=(ROOT/artifact['path']).read_bytes();assert sha(data)==artifact['sha256'];self.svm.add_program(K[role],data);assert bytes(self.svm.get_account(K[role]).data)==data;self.programs[role]=artifact
  if load_h:
   for env_key,kind,feature in [('M3_ELF','htfp','local-m3'),('M3_DEFAULT_ELF','htfp','DEFAULT_DISABLED'),('M3_HELPER_ELF','helper','local-m3')]:
    a=M3_ARTIFACTS[env_key];data,record=validate_artifact(a['path'],kind,feature);assert sha(data)==a['sha256'];os.environ[env_key]=a['path'];m3.ARTIFACTS[env_key]=data
   self.svm.add_program(K['program'],m3.ARTIFACTS['M3_ELF'])
  assert ComputeBudget().heap_size==32768
 def snapshot(self):
  result={}
  for role,k in self.tracked.items():
   a=self.svm.get_account(k)
   result[role]=None if a is None else dict(address=str(k),owner=str(a.owner),lamports=a.lamports,data_hex=bytes(a.data).hex(),bytes=len(a.data),data_sha256=sha(bytes(a.data)),executable=a.executable)
  return result
 def track(self,role,key):self.tracked[role]=key
 def clock(self,epoch,slot,unix):self.svm.warp_to_slot(slot);self.svm.set_clock(Clock(slot,0,epoch,epoch,unix));self.events.append(dict(kind='synthetic_clock',epoch=epoch,slot=slot,unix_timestamp=unix))
 def send(self,name,instructions,signers=(),expected=None,payer=None,observe=False,cu=1400000,versioned=None):
  payer=payer or self.i;before=self.snapshot();payer_before=self.svm.get_balance(payer.pubkey());self.svm.expire_blockhash();block=self.svm.latest_blockhash()
  operations=[set_compute_unit_limit(cu)]+list(instructions);signing={str(payer.pubkey()):payer};signing.update({str(s.pubkey()):s for s in signers})
  if versioned is None:tx=Transaction.new_signed_with_payer(operations,payer.pubkey(),list(signing.values()),block)
  else:tx=VersionedTransaction(MessageV0.try_compile(payer.pubkey(),operations,versioned,block),list(signing.values()))
  assert len(bytes(tx))<=1232,(name,len(bytes(tx)))
  result=self.svm.send_transaction(tx);failed=isinstance(result,FailedTransactionMetadata);meta=result.meta() if failed else result;after=self.snapshot();units=meta.compute_units_consumed();assert units<=cu<=1400000
  row=dict(kind='transaction',fixture=self.label,name=name,expected='OBSERVE' if observe else ('SUCCESS' if expected is None else expected),status='FAILURE' if failed else 'SUCCESS',error=str(result.err()) if failed else None,transaction_hex=bytes(tx).hex(),transaction_sha256=sha(bytes(tx)),message_hex=bytes(tx.message).hex(),recent_blockhash=str(block),message_version='legacy' if versioned is None else 'v0',packet_bytes=len(bytes(tx)),signatures=[str(s) for s in tx.signatures],signature_count=len(tx.signatures),compute_units=units,compute_unit_limit=cu,heap_bytes=32768,signature_verification=True,blockhash_verification=True,payer=str(payer.pubkey()),payer_before=payer_before,payer_after=self.svm.get_balance(payer.pubkey()),fee_lamports=len(tx.signatures)*5000,logs=meta.logs(),before=before,after=after,native_load=self.native,custom_program_artifacts=self.programs)
  self.events.append(row)
  if failed:
   for role,old in before.items():
    want=old
    if old is not None and old['address']==str(payer.pubkey()):want=dict(old);want['lamports']-=len(tx.signatures)*5000
    assert after[role]==want,(name,role,old,after[role])
   assert row['payer_before']-row['payer_after']==row['fee_lamports'];row['rollback_verified']=True
  if not observe:
   if expected is None:assert not failed,(name,row['error'],row['logs'])
   else:
    assert failed,(name,'expected failure')
    if isinstance(expected,int):assert getattr(getattr(result.err(),'err',None),'code',None)==expected,(name,row['error'],row['logs'])
    else:assert expected in row['error'],(name,row['error'],expected)
  return row
 def proof_ix(self,tag,payload=b'',payer=None,temp=None):
  names={0:'initializer proof_guard proof_volume proof_record proof_reserve proof_marker system',1:'initializer proof_guard proof_volume proof_record proof_marker instructions_sysvar system',2:'initializer proof_guard proof_volume proof_record proof_marker instructions_sysvar system',3:'initializer proof_guard proof_volume proof_record proof_marker instructions_sysvar system',4:'initializer proof_guard proof_volume proof_record proof_reserve temp proof_settle_authority storage_payer legacy_token wsol_mint system instructions_sysvar',5:'initializer proof_guard proof_volume proof_record proof_reserve temp proof_settle_authority storage_payer legacy_token wsol_mint system instructions_sysvar',6:'initializer proof_guard proof_volume proof_record instructions_sysvar',7:'initializer proof_guard proof_volume proof_record proof_marker instructions_sysvar system proof_program wallet_program',8:'initializer proof_guard proof_volume proof_record proof_marker instructions_sysvar system'}[tag].split()
  write={0:{0,1,2,3,4,5},1:{0,1,2,3,4},2:{0,1,2,3,4},3:{0,1,2,3,4},4:{1,2,3,4,5,7},5:{1,2,3,4,5,7},6:{1,2,3},7:{0,1,2,3,4},8:{0,1,2,3,4}}[tag]
  keymap={**K,'storage_payer':(payer or self.i).pubkey(),'temp':temp or K['proof_temp_sequence0']}
  return ix(K['proof_program'],b'M4BPRF01'+bytes([tag])+payload,[am(keymap[n],j in write,j==0 or n=='storage_payer') for j,n in enumerate(names)])
 def finish(self,nonce=1):return self.proof_ix(6,struct.pack('<Q',nonce))
 def bootstrap(self):return self.send('proof_bootstrap',[self.proof_ix(0)])
 def wallet(self,scenario,nonce=1):
  base=self.proof_ix(7,b'\0');return ix(K['wallet_program'],b'M4BWAL01'+bytes([scenario])+struct.pack('<Q',nonce),base.accounts)
 def account(self,role):return self.svm.get_account(self.tracked[role])
 def events_to(self,p):save(p,self.events)
