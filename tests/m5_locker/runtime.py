"""Explicit native adapter; no old VM/AMM constructor, route or artifact defaults."""
from common import *
import struct,base64,gc
from solders.account import Account
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.clock import Clock
from solders.litesvm import LiteSVM
from solders.instruction import Instruction,AccountMeta
from solders.transaction import Transaction
from solders.hash import Hash
from solders.transaction_metadata import FailedTransactionMetadata
from solders.compute_budget import set_compute_unit_limit,ComputeBudget
from solders.system_program import transfer,create_account,create_account_with_seed
K={r:Pubkey.from_string(v['base58']) for r,v in PROFILE['identities'].items()}
M3=load_source('m5_frozen_M3_instruction_source',ROOT/'tests/m3/harness.py')
QUOTE=load_source('m5_independent_frozen_quote',ROOT/'tests/m4b/quote_oracle.py')
def am(k,*,w=False,s=False):return AccountMeta(K[k] if isinstance(k,str) else k,s,w)
def ix(program,data,metas):return Instruction(K[program] if isinstance(program,str) else program,bytes(data),metas)
def sol(sender,to,n):return transfer(dict(from_pubkey=sender,to_pubkey=to,lamports=n))
def amt(a):return 0 if a is None else struct.unpack_from('<Q',bytes(a.data),64)[0]
def supply(a):return struct.unpack_from('<Q',bytes(a.data),36)[0]
def raw_program(spec):
 if 'raw_sha256' in spec:
  stored=(ROOT/spec['path']).read_bytes();assert sha(stored)==spec['stored_sha256'];b=gzip.decompress(stored);assert sha(b)==spec['raw_sha256'] and len(b)==spec['raw_bytes'];return b
 b=(ROOT/spec['path']).read_bytes();assert sha(b)==spec.get('sha256',spec.get('full_sha256'));return b
class VM:
 def __init__(self,label):
  COUNTS['instances']+=1;resources();self.label=label;self.svm=LiteSVM().with_sigverify(True).with_blockhash_check(True);assert ComputeBudget().heap_size==32768;self.events=EVENTS;self.programs={};self.tracked={r:k for r,k in K.items() if r not in ['system','program','token2022','legacy_token','associated_token','amm','locker','metadata','memo']};self.signers={}
  # All deliberately public RFC8032 test material. In-memory only, never key files.
  vectors={'payer':'9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60','mint_signer':'4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb','beneficiary':'c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7','fee_key_mint_1':'f5e5767cf153319517630f226876b86c8160cc583bc013744c6bf255f5cc0ee5','fee_key_mint_2':'833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42','unrelated_owner':'0305334e381af78f141cb666f6199f57bc3495335a256a95bd2a55bf546663f6'}
  for r,h in vectors.items():self.signers[r]=Keypair.from_seed(bytes.fromhex(h));assert self.signers[r].pubkey()==K[r]
  self.initializer=self.signers['payer'];self.holder=self.signers['beneficiary'];self.mint_signer=self.signers['mint_signer'];self.p=self.initializer;self.w=self.holder;self.b=self.signers['unrelated_owner']
  before={r:self.program_view(r) for r in ['associated_token','memo','metadata']};container=Path(NATIVE['ATA']['container']).read_bytes();ata=NATIVE['ATA'];assert sha(container)==ata['container_sha256'];assert before['associated_token']['sha256']==ata['ELF_sha256'] and bytes(self.svm.get_account(K['associated_token']).data)==container[ata['slice_offset']:ata['slice_offset']+ata['slice_bytes']]
  for role,spec in [('token2022',NATIVE['Token2022']),('legacy_token',NATIVE['legacy_Token']),('amm',NATIVE['CPMM']),('locker',NATIVE['locker']),('metadata',NATIVE['metadata']['code']),('memo',NATIVE['memo']['code']),('program',NATIVE['H_initialization_artifact'])]:
   data=raw_program(spec);self.svm.add_program(K[role],data);assert bytes(self.svm.get_account(K[role]).data)==data;self.programs[role]=dict(path=spec['path'],sha256=sha(data),bytes=len(data),association_only_not_runtime_pass=True)
  EVENTS.append(dict(kind='native_program_artifact_associations',fixture=label,before=before,selected=self.programs,ATA=before['associated_token'],loader_fidelity='Synthetic BPF2 add_program with possible suppressed loader errors; real outcomes required. Mixed snapshots; public equivalence UNPROVEN.'))
  self.svm.airdrop(K['payer'],int(PROFILE['funding']['synthetic_initial_payer_lamports']));EVENTS.append(dict(kind='artificial_System_funding',fixture=label,role='payer',lamports=PROFILE['funding']['synthetic_initial_payer_lamports'],native_program_positive_state=False))
  mintkey=K['wsol_mint'];assert self.svm.get_account(mintkey) is None;raw=(ROOT/NATIVE['native_mint_data']['path']).read_bytes();assert sha(raw)==NATIVE['native_mint_data']['sha256'] and len(raw)==82 and struct.unpack_from('<Q',raw,36)[0]==0;rent=self.svm.minimum_balance_for_rent_exemption(82);self.svm.set_account(mintkey,Account(rent,raw,K['legacy_token']));EVENTS.append(dict(kind='reviewed_static_native_mint_dependency',fixture=label,bytes=82,sha256=sha(raw),local_actual_rent=rent,no_public_lamports=True,no_positive_supply=True));self.clock('bootstrap')
 def program_view(self,role):
  a=self.svm.get_account(K[role]);return None if a is None else dict(address=str(K[role]),owner=str(a.owner),executable=a.executable,bytes=len(a.data),sha256=sha(bytes(a.data)))
 def account(self,role):return self.svm.get_account(K[role] if isinstance(role,str) else role)
 def snap(self):
  rows={}
  for role,key in self.tracked.items():
   a=self.svm.get_account(key);rows[role]=None if a is None else dict(address=str(key),owner=str(a.owner),lamports=a.lamports,data_hex=bytes(a.data).hex(),data_sha256=sha(bytes(a.data)),bytes=len(a.data),executable=a.executable)
  return rows
 def actual(self):
  c=self.svm.get_clock();r=self.svm.get_rent();return dict(clock={k:getattr(c,k) for k in ['slot','epoch_start_timestamp','epoch','leader_schedule_epoch','unix_timestamp']},rent={k:getattr(r,k) for k in ['lamports_per_byte_year','exemption_threshold','burn_percent']},rent_minima={str(n):self.svm.minimum_balance_for_rent_exemption(n) for n in [0,82,165,178,256,278]})
 def clock(self,phase):
  d=PROFILE['clock'][phase];self.svm.warp_to_slot(d['slot']);self.svm.set_clock(Clock(d['slot'],0,d['epoch'],d['epoch'],d['unix_timestamp']));EVENTS.append(dict(kind='synthetic_clock',fixture=self.label,phase=phase,**d))
 def send(self,name,instructions,signers=(),expected=None,payer=None,cu=1400000,control=None):
  resources();payer=payer or self.p;before=self.snap();runtime=self.actual();self.svm.expire_blockhash();block=self.svm.latest_blockhash();block=Hash.default() if control=='expired_blockhash' else block;ops=[set_compute_unit_limit(cu),*instructions];signing={str(payer.pubkey()):payer};signing.update({str(s.pubkey()):s for s in signers});tx=Transaction.new_signed_with_payer(ops,payer.pubkey(),list(signing.values()),block)
  if control=='invalid_signature':b=bytearray(bytes(tx));b[1]^=1;tx=Transaction.from_bytes(bytes(b))
  data=bytes(tx);COUNTS['attempts']+=1;result=self.svm.send_transaction(tx);failed=isinstance(result,FailedTransactionMetadata);meta=result.meta() if failed else result;after=self.snap();message=tx.message;head=message.header;keys=list(message.account_keys)
  row=dict(kind='transaction',fixture=self.label,name=name,expected=expected,control=control,status='FAILURE' if failed else 'SUCCESS',error=str(result.err()) if failed else None,logs=meta.logs(),compute_units=meta.compute_units_consumed(),compute_unit_limit=cu,heap_bytes=32768,signature_verification=True,blockhash_verification=True,transaction_hex=data.hex(),transaction_sha256=sha(data),message_hex=bytes(message).hex(),recent_blockhash=str(block),signatures=[str(s) for s in tx.signatures],signature_count=len(tx.signatures),packet_bytes=len(data),payer=str(payer.pubkey()),payer_before=self.svm.get_balance(payer.pubkey()) if False else next(a['lamports'] for a in before.values() if a and a['address']==str(payer.pubkey())),payer_after=self.svm.get_balance(payer.pubkey()),before=before,after=after,actual_runtime_before=runtime,actual_runtime_after=self.actual(),addresses={r:str(k) for r,k in self.tracked.items()},custom_native_artifacts=self.programs,requested_instructions=[dict(program_id=str(op.program_id),data_hex=bytes(op.data).hex(),accounts=[dict(pubkey=str(m.pubkey),signer=m.is_signer,writable=m.is_writable) for m in op.accounts]) for op in ops],actual_compiled_accounts=[dict(index=i,pubkey=str(k),signer=i<head.num_required_signatures,writable=(i<head.num_required_signatures-head.num_readonly_signed_accounts if i<head.num_required_signatures else i<len(keys)-head.num_readonly_unsigned_accounts)) for i,k in enumerate(keys)],actual_compiled_instructions=[dict(program_id_index=i.program_id_index,accounts=list(i.accounts),data_hex=bytes(i.data).hex()) for i in message.instructions])
  EVENTS.append(row) # Actual result is retained before assertions or optional formatting.
  try:row['actual_inner_instructions']=[[dict(program_id_index=i.instruction().program_id_index,accounts=list(i.instruction().accounts),data_hex=bytes(i.instruction().data).hex(),stack_height=i.stack_height()) for i in g] for g in meta.inner_instructions()]
  except Exception as e:row['metadata_error']=repr(e);raise
  row['expected_network_fee']=0 if control else len(tx.signatures)*5000
  if failed:
   changes=[]
   for role,old in before.items():
    want=None if old is None else dict(old)
    if want and want['address']==str(payer.pubkey()):want['lamports']-=row['expected_network_fee']
    if after[role]!=want:changes.append(role)
   row['rollback_verified']=not changes;row['rollback_mismatches']=changes;assert not changes,changes
  assert len(data)<=1232 and row['compute_units']<=cu<=1400000
  if control:assert failed and ('SignatureFailure' in row['error'] if control=='invalid_signature' else 'BlockhashNotFound' in row['error'])
  elif expected=='OBSERVE':pass
  elif expected is None:assert not failed,(name,row['error'],row['logs'])
  else:assert failed and str(expected) in row['error'],(name,row['error'])
  return row
 def native_abi(self,name,mapping=None,data=None):
  spec=ABI['CPMM_instructions'][name];mapping=mapping or {};return ix('amm',bytes.fromhex(spec['primary_data_hex']) if data is None else data,[am(mapping.get(m['role'],K.get(m['role'])),w=m['writable'],s=m['signer']) for m in spec['accounts']])
 def ata(self,role,mint,token,owner):return self.send('native_ATA_'+role,[ix('associated_token',b'\1',[am('payer',w=True,s=True),am(role,w=True),am(owner),am(mint),am('system'),am(token)])])
 def transfer_htfp(self,source,dest,n,owner):return self.send('native_HTFP_transfer_'+str(n),[ix('token2022',bytes([12])+struct.pack('<QB',n,7),[am(source,w=True),am('mint'),am(dest,w=True),am(owner.pubkey(),s=True)])],[owner])
 def setup_pool(self):
  M3.VM.genesis(self);self.send('genuine_fixed_H_Initialize',[M3.VM.initialize_ix(self)]);self.send('native_fund_W_B_Reserve_sentinel',[sol(K['payer'],K['beneficiary'],10**12),sol(K['payer'],K['unrelated_owner'],10**12),sol(K['payer'],K['reserve'],10**9)])
  for role,mint,t,owner in [('creator_wsol','wsol_mint','legacy_token','beneficiary'),('creator_htfp','mint','token2022','beneficiary'),('unrelated_wsol','wsol_mint','legacy_token','unrelated_owner'),('unrelated_htfp','mint','token2022','unrelated_owner')]:self.ata(role,mint,t,owner)
  self.send('native_wrap_W_120SOL',[sol(K['beneficiary'],K['creator_wsol'],120000000000),ix('legacy_token',b'\x11',[am('creator_wsol',w=True)])],[self.w]);self.send('native_wrap_B_20SOL',[sol(K['unrelated_owner'],K['unrelated_wsol'],20000000000),ix('legacy_token',b'\x11',[am('unrelated_wsol',w=True)])],[self.b]);self.transfer_htfp('genesis_holding','creator_htfp',11000000000000,self.w);self.transfer_htfp('genesis_holding','unrelated_htfp',10000000000000,self.w)
  raw=(ROOT/NATIVE['config0']['path']).read_bytes();self.svm.set_account(K['amm_config'],Account(self.svm.minimum_balance_for_rent_exemption(236),raw,K['amm']));l=self.svm.minimum_balance_for_rent_exemption(165);self.svm.set_account(K['creation_fee_receiver'],Account(l,bytes(165),K['legacy_token']));EVENTS.append(dict(kind='reviewed_static_nonmonetary_dependencies',fixture=self.label,config_sha256=sha(raw),fee_receiver_zero_buffer_bytes=165,fee_receiver_rent=l,no_positive_token_state=True));self.send('native_initialize_zero_fee_receiver',[ix('legacy_token',bytes([18])+bytes(K['beneficiary']),[am('creation_fee_receiver',w=True),am('wsol_mint')])]);self.send('genuine_Some_BothToken_pool_0pct',[self.native_abi('initialize_v2')],[self.w]);self.initial_receipt=amt(self.account('creator_lp'))
  pool=bytes(self.account('pool').data);assert self.initial_receipt==999999999900 and supply(self.account('lp_mint'))==self.initial_receipt and struct.unpack_from('<Q',pool,333)[0]==10**12;assert pool[389:391]==bytes([0,1]);assert amt(self.account('vault_wsol'))==10**11 and amt(self.account('vault_htfp'))==10**13;assert self.svm.get_balance(K['reserve'])==10**9;assert bytes(self.account('inventory').data)[11:20]==bytes(9);self.clock('lock_initial');return self
 def lock_ix(self,writable=False,metadata=True,secondary=False):
  spec=ABI['secondary_lock_template'] if secondary else ABI['instructions']['lock_cp_liquidity'];data=bytearray.fromhex(spec['wire_hex']);data[-1]=int(metadata);metas=[am(m['role'],w=(writable if i==8 else m['writable']),s=m['signer']) for i,m in enumerate(spec['metas'])];return ix('locker',data,metas)
 def lock(self,writable=False,metadata=True,observe=False):return self.send('standalone_Lock_'+('CPI_W' if writable else 'SDK_R')+'_metadata'+str(metadata),[self.lock_ix(writable,metadata)],[self.w,self.signers['fee_key_mint_1']],expected='OBSERVE' if observe else None)
