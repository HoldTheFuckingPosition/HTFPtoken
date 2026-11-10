"""Explicit native adapter; no old VM/AMM constructor, route or artifact defaults."""
from common import *
import struct,base64,gc,weakref
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
ACTIVE_VMS=weakref.WeakSet()
class VM:
 def __init__(self,label):
  assert len(ACTIVE_VMS)<2;resources(instances=1);ACTIVE_VMS.add(self);COUNTS['instances']+=1;self.label=label;self.svm=LiteSVM().with_sigverify(True).with_blockhash_check(True);assert ComputeBudget().heap_size==32768;self.events=EVENTS;self.programs={};self.tracked={r:k for r,k in K.items() if r not in ['system','program','token2022','legacy_token','associated_token','amm','locker','metadata','memo']};self.signers={}
  # All deliberately public RFC8032 test material. In-memory only, never key files.
  vectors={'payer':'9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60','mint_signer':'4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb','beneficiary':'c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7','fee_key_mint_1':'f5e5767cf153319517630f226876b86c8160cc583bc013744c6bf255f5cc0ee5','fee_key_mint_2':'833fe62409237b9d62ec77587520911e9a759cec1d19755b7da901b96dca3d42','unrelated_owner':'0305334e381af78f141cb666f6199f57bc3495335a256a95bd2a55bf546663f6'}
  for r,h in vectors.items():self.signers[r]=Keypair.from_seed(bytes.fromhex(h));assert self.signers[r].pubkey()==K[r]
  self.initializer=self.signers['payer'];self.holder=self.signers['beneficiary'];self.mint_signer=self.signers['mint_signer'];self.p=self.initializer;self.w=self.holder;self.b=self.signers['unrelated_owner']
  before={r:self.program_view(r) for r in ['associated_token','memo','metadata']};container=Path(NATIVE['ATA']['container']).read_bytes();ata=NATIVE['ATA'];assert sha(container)==ata['container_sha256'];assert before['associated_token']['sha256']==ata['ELF_sha256'] and bytes(self.svm.get_account(K['associated_token']).data)==container[ata['slice_offset']:ata['slice_offset']+ata['slice_bytes']]
  for role,spec in [('token2022',NATIVE['Token2022']),('legacy_token',NATIVE['legacy_Token']),('amm',NATIVE['CPMM']),('locker',NATIVE['locker']),('metadata',NATIVE['metadata']['code']),('memo',NATIVE['memo']['code']),('program',NATIVE['H_initialization_artifact'])]:
   data=raw_program(spec);self.svm.add_program(K[role],data);assert bytes(self.svm.get_account(K[role]).data)==data;self.programs[role]=dict(path=spec['path'],sha256=sha(data),bytes=len(data),association_only_not_runtime_pass=True)
  EVENTS.append(dict(kind='native_program_artifact_associations',fixture=label,before=before,selected=self.programs,post_override_actual_getters={r:self.program_view(r) for r in [*self.programs,'associated_token']},ATA=before['associated_token'],loader_fidelity='Synthetic BPF2 add_program with possible suppressed loader errors; real outcomes required. Mixed snapshots; public equivalence UNPROVEN.'))
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
  data=bytes(tx);resources(attempts=1);COUNTS['attempts']+=1;result=self.svm.send_transaction(tx);failed=isinstance(result,FailedTransactionMetadata);meta=result.meta() if failed else result;after=self.snap();message=tx.message;head=message.header;keys=list(message.account_keys)
  row=dict(kind='transaction',fixture=self.label,name=name,expected=expected,control=control,status='FAILURE' if failed else 'SUCCESS',error=str(result.err()) if failed else None,logs=meta.logs(),compute_units=meta.compute_units_consumed(),compute_unit_limit=cu,heap_bytes=32768,signature_verification=True,blockhash_verification=True,transaction_hex=data.hex(),transaction_sha256=sha(data),message_hex=bytes(message).hex(),message_sha256=sha(bytes(message)),recent_blockhash=str(block),signatures=[str(s) for s in tx.signatures],signature_count=len(tx.signatures),packet_bytes=len(data),payer=str(payer.pubkey()),payer_before=self.svm.get_balance(payer.pubkey()) if False else next(a['lamports'] for a in before.values() if a and a['address']==str(payer.pubkey())),payer_after=self.svm.get_balance(payer.pubkey()),before=before,after=after,actual_runtime_before=runtime,actual_runtime_after=self.actual(),addresses={r:str(k) for r,k in self.tracked.items()},custom_native_artifacts=self.programs,requested_instructions=[dict(program_id=str(op.program_id),data_hex=bytes(op.data).hex(),accounts=[dict(pubkey=str(m.pubkey),signer=m.is_signer,writable=m.is_writable) for m in op.accounts]) for op in ops],actual_compiled_accounts=[dict(index=i,pubkey=str(k),signer=i<head.num_required_signatures,writable=(i<head.num_required_signatures-head.num_readonly_signed_accounts if i<head.num_required_signatures else i<len(keys)-head.num_readonly_unsigned_accounts)) for i,k in enumerate(keys)],actual_compiled_instructions=[dict(program_id_index=i.program_id_index,accounts=list(i.accounts),data_hex=bytes(i.data).hex()) for i in message.instructions])
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
 def pool_view(self):
  d=bytes(self.account('pool').data);p=[struct.unpack_from('<Q',d,o)[0] for o in [341,349]];f=[struct.unpack_from('<Q',d,o)[0] for o in [357,365]];c=[struct.unpack_from('<Q',d,o)[0] for o in [397,405]];v=[amt(self.account(r)) for r in ['vault_wsol','vault_htfp']];x=[v[i]-p[i]-f[i]-c[i] for i in range(2)];assert min(x)>=0
  return dict(v=v,p=p,f=f,c=c,x=x,L=struct.unpack_from('<Q',d,333)[0],mint_supply=supply(self.account('lp_mint')),escrow=amt(self.account('shared_lp_escrow')))
 def token(self,role):return M3.token_view(bytes(self.account(role).data))
 def sentinels(self):
  assert self.svm.get_balance(K['reserve'])==10**9 and bytes(self.account('inventory').data)[11:20]==bytes(9) and amt(self.account('custody'))==0
  assert supply(self.account('mint'))==10**19
 def receipts(self):
  for role,mint,token,n in [('locker_receipt_wsol','wsol_mint','legacy_token',165),('locker_receipt_htfp','mint','token2022',178),('creator_unwrap_wsol','wsol_mint','legacy_token',165)]:
   d=PROFILE['derivations'][role];assert Pubkey.create_with_seed(K['payer'],d['seed_UTF8'],K[token])==K[role]
   op=create_account_with_seed(dict(from_pubkey=K['payer'],to_pubkey=K[role],base=K['payer'],seed=d['seed_UTF8'],lamports=self.svm.minimum_balance_for_rent_exemption(n),space=n,owner=K[token]))
   self.send('native_zero_receipt_'+role,[op,ix(token,bytes([18])+bytes(K['beneficiary']),[am(role,w=True),am(mint)])]);assert amt(self.account(role))==0
 def position_start(self):
  v=self.pool_view();self.position=dict(q0=self.initial_receipt,K0=v['x'][0]*v['x'][1],L0=v['L'],burned=0);return dict(self.position)
 def swap(self,htfp_in,n,observe=False):
  before=self.pool_view();j=int(htfp_in);q=QUOTE.quote(n,before['x'][j],before['x'][1-j],htfp_in,True,0,True)
  rin='creator_htfp' if htfp_in else 'creator_wsol';rout='creator_wsol' if htfp_in else 'creator_htfp';bi=self.token(rin);bo=self.token(rout);vh=self.token('vault_htfp')
  mapping={r:K[v] for r,v in dict(input_authority='beneficiary',input_token=rin,output_token=rout,input_vault='vault_htfp' if htfp_in else 'vault_wsol',output_vault='vault_wsol' if htfp_in else 'vault_htfp',input_token_program='token2022' if htfp_in else 'legacy_token',output_token_program='legacy_token' if htfp_in else 'token2022',input_mint='mint' if htfp_in else 'wsol_mint',output_mint='wsol_mint' if htfp_in else 'mint').items()}
  data=bytes.fromhex(ABI['CPMM_instructions']['swap_base_input']['anchor_discriminator_hex'])+struct.pack('<QQ',n,0);row=self.send('native_swap_'+('HTFP' if htfp_in else 'wSOL')+'_'+str(n),[self.native_abi('swap_base_input',mapping,data)],[self.w],expected='OBSERVE' if observe else None);row['independent_quote']=q
  if row['status']=='SUCCESS':
   after=self.pool_view();ai=self.token(rin);ao=self.token(rout);row['swap_accounting']=dict(before=before,after=after,input_before=bi,input_after=ai,output_before=bo,output_after=ao)
   assert bi['spendable']-ai['spendable']==n and ao['spendable']-bo['spendable']==q['recipient_out']
   assert after['v'][j]-before['v'][j]==q['actual_input'] and before['v'][1-j]-after['v'][1-j]==q['gross_out']
   for key,qkey in [('p','protocol_fee'),('f','fund_fee'),('c','creator_fee')]:assert after[key][j]-before[key][j]==q[qkey] and after[key][1-j]==before[key][1-j]
   assert (self.token('vault_htfp')['withheld']-vh['withheld'] if htfp_in else ao['withheld']-bo['withheld'])==(q['native_in_tax'] if htfp_in else q['native_out_tax']);self.sentinels()
  return row
 def accrue(self,later=False):
  self.clock('trades')
  for unused in range(2 if later else 4):self.swap(True,20000000000 if later else 10000000000);self.swap(False,200000000 if later else 100000000)
 def claim_ix(self,request=2**64-1,mapping=None):
  mapping=mapping or {};s=ABI['instructions']['collect_cp_fees'];return ix('locker',bytes.fromhex(s['wire_hex'])[:8]+struct.pack('<Q',request),[am(mapping.get(m['role'],K[m['role']]),w=m['writable'],s=m['signer']) for m in s['metas']])
 def collect_creator(self):
  before=self.pool_view();b=[self.token(r) for r in ['creator_wsol','creator_htfp']];row=self.send('native_creator_collection',[self.native_abi('collect_creator_fee_permissionless')]);after=self.pool_view();a=[self.token(r) for r in ['creator_wsol','creator_htfp']];gross=[before['v'][i]-after['v'][i] for i in range(2)];row['creator_accounting']=dict(before=before,after=after,gross=gross,net=[a[i]['spendable']-b[i]['spendable'] for i in range(2)],withheld=[a[i]['withheld']-b[i]['withheld'] for i in range(2)])
  assert before['x']==after['x'] and gross==before['c'] and after['c']==[0,0];assert row['creator_accounting']['net']==[gross[0],gross[1]-QUOTE.token_tax(gross[1])];assert row['creator_accounting']['withheld']==[0,QUOTE.token_tax(gross[1])];self.sentinels();return row
 def claim(self,request=2**64-1,observe=False,variant='primary'):
  spec=ABI['instructions']['collect_cp_fees'] if variant=='primary' else ABI['transferred_FeeKey1_claim_template'] if variant=='transferred' else ABI['secondary_FeeKey2_claim_template'];recips=['locker_receipt_wsol','locker_receipt_htfp'] if variant=='primary' else ['unrelated_wsol','unrelated_htfp'];op=ix('locker',bytes.fromhex(spec['wire_hex'])[:8]+struct.pack('<Q',request),[am(m['role'],w=m['writable'],s=m['signer']) for m in spec['metas']]);before=self.pool_view();b=[self.token(r) for r in recips];row=self.send('native_locker_claim_'+variant+'_'+str(request),[op],[self.w if variant=='primary' else self.b],expected='OBSERVE' if observe else None)
  if row['status']!='SUCCESS':return row
  after=self.pool_view();a=[self.token(r) for r in recips];burn=before['escrow']-after['escrow'];gross=[before['v'][i]-after['v'][i] for i in range(2)];inner=[]
  keys=[x['pubkey'] for x in row['actual_compiled_accounts']]
  for group in row['actual_inner_instructions']:
   for op in group:
    data=bytes.fromhex(op['data_hex']);pid=keys[op['program_id_index']]
    if pid==str(K['amm']) and data[:8]==bytes.fromhex('b712469c946da122'):inner.append(dict(amount=struct.unpack_from('<Q',data,8)[0],accounts=[keys[i] for i in op['accounts']]))
  row['claim_accounting']=dict(before=before,after=after,burn=burn,gross=gross,net=[a[i]['spendable']-b[i]['spendable'] for i in range(2)],withheld=[a[i]['withheld']-b[i]['withheld'] for i in range(2)],actual_withdraws=inner)
  lp_burns=[]
  for group in row['actual_inner_instructions']:
   for op in group:
    data=bytes.fromhex(op['data_hex']);pid=keys[op['program_id_index']]
    if pid==str(K['legacy_token']) and data and data[0] in [8,15] and keys[op['accounts'][1]]==str(K['lp_mint']):lp_burns.append(struct.unpack_from('<Q',data,1)[0])
  row['claim_accounting']['actual_legacy_LP_burns']=lp_burns
  assert len(inner)==1 and inner[0]['amount']==burn>0 and sum(lp_burns)==burn and burn<=request;assert before['mint_supply']-after['mint_supply']==before['L']-after['L']==burn
  expected=[x*burn//before['L'] for x in before['x']];row['claim_accounting']['floor_residual_numerators']=[x*burn-g*before['L'] for x,g in zip(before['x'],gross)];row['claim_accounting']['floor_residual_denominator']=before['L'];assert all(0<=r<before['L'] for r in row['claim_accounting']['floor_residual_numerators']);assert gross==expected,(gross,expected);assert all(before[k]==after[k] for k in ['p','f','c'])
  assert row['claim_accounting']['net']==[gross[0],gross[1]-QUOTE.token_tax(gross[1])];assert row['claim_accounting']['withheld']==[0,QUOTE.token_tax(gross[1])]
  # C-A01: compare the actual native inner withdrawal destinations to selected outer recipients.
  audit=ABI['CPMM_inner_withdraw_audit_variants'][{'primary':'primary','transferred':'transferred_FeeKey1','secondary':'secondary_FeeKey2'}[variant]];actual=inner[0]['accounts'];roles={m['role']:actual[i] for i,m in enumerate(audit['accounts'])};row['actual_withdraw_roles']=roles
  assert all(actual[i]==str(K[m['role']]) for i,m in enumerate(audit['accounts']))
  p=self.position if variant!='secondary' else self.secondary_position;p['burned']+=burn;assert 0<=p['burned']<=p['q0'];q=p['q0']-p['burned'];assert q>=0;kn=after['x'][0]*after['x'][1];lhs=q*q*kn*p['L0']**2;rhs=p['q0']**2*p['K0']*after['L']**2
  import math
  numerator=p['q0']**2*p['K0']*after['L']**2;denominator=kn*p['L0']**2;qmin=math.isqrt(numerator//denominator)
  if qmin*qmin*denominator<numerator:qmin+=1
  unadjusted_lhs=lhs;unadjusted_rhs=rhs;lhs*=p.get('capital_D',1);rhs*=p.get('capital_N',1)
  numerator*=p.get('capital_N',1);denominator*=p.get('capital_D',1);qmin=math.isqrt(numerator//denominator)
  if qmin*qmin*denominator<numerator:qmin+=1
  row['principal_diagnostic']=dict(unadjusted_lhs=unadjusted_lhs,unadjusted_rhs=unadjusted_rhs,position=p.copy(),q=q,K_now=kn,L_now=after['L'],lhs=lhs,rhs=rhs,holds=lhs>=rhs,qmin=qmin,shortfall_LP=max(0,qmin-q),scope='bounded normalized effective liquidity metric; unknown native growth formula, no perpetual guarantee');assert lhs>=rhs,row['principal_diagnostic'];positions=[self.position]+([self.secondary_position] if hasattr(self,'secondary_position') else []);assert after['escrow']==sum(p['q0']-p['burned'] for p in positions);self.sentinels();return row
 def deposit_B(self):
  if self.account('unrelated_lp') is None:self.ata('unrelated_lp','lp_mint','legacy_token','unrelated_owner')
  before=self.pool_view();bh=self.token('unrelated_htfp');bs=amt(self.account('unrelated_wsol'));mapping={r:K[v] for r,v in dict(genesis_owner='unrelated_owner',creator_lp='unrelated_lp',creator_wsol='unrelated_wsol',creator_htfp='unrelated_htfp').items()};row=self.send('native_B_proportional_deposit',[self.native_abi('deposit',mapping)],[self.b]);after=self.pool_view();net=[after['v'][i]-before['v'][i] for i in range(2)];want=[(x*10**10+before['L']-1)//before['L'] for x in before['x']];gross_h=bh['spendable']-self.token('unrelated_htfp')['spendable'];active=self.actual()['clock']['epoch']>=9
  row['deposit_accounting']=dict(before=before,after=after,net=net,expected_source_ceil=want,gross_htfp=gross_h,normalization_N=after['x'][0]*after['x'][1]*before['L']**2,normalization_D=before['x'][0]*before['x'][1]*after['L']**2)
  assert after['L']-before['L']==after['mint_supply']-before['mint_supply']==10**10 and net==want and bs-amt(self.account('unrelated_wsol'))==net[0];assert gross_h-QUOTE.token_tax(gross_h,active)==net[1];assert amt(self.account('unrelated_lp'))==10**10
  if hasattr(self,'position'):
   p=self.position;p['capital_N']=p.get('capital_N',1)*row['deposit_accounting']['normalization_N'];p['capital_D']=p.get('capital_D',1)*row['deposit_accounting']['normalization_D']
  return row
 def secondary_lock(self):
  before=self.pool_view();self.secondary_position=dict(q0=5000000000,K0=before['x'][0]*before['x'][1],L0=before['L'],burned=0);row=self.send('native_B_secondary_lock',[self.lock_ix(secondary=True)],[self.b,self.signers['fee_key_mint_2']]);after=self.pool_view();assert after['escrow']-before['escrow']==5000000000 and amt(self.account('unrelated_lp'))==5000000000;return row
 def nft_transfer(self,to_B=True):
  if self.account('transferred_fee_key_1') is None:self.ata('transferred_fee_key_1','fee_key_mint_1','legacy_token','unrelated_owner')
  source,dest,owner=('fee_key_account_1','transferred_fee_key_1',self.w) if to_B else ('transferred_fee_key_1','fee_key_account_1',self.b)
  row=self.send('native_FeeKey1_transfer_'+('W_to_B' if to_B else 'B_to_W'),[ix('legacy_token',bytes([12])+struct.pack('<QB',1,0),[am(source,w=True),am('fee_key_mint_1'),am(dest,w=True),am(owner.pubkey(),s=True)])],[owner]);assert amt(self.account(source))==0 and amt(self.account(dest))==1;return row
 def unwrap(self,creator_delta,locker_delta,late=False):
  if creator_delta:
   assert amt(self.account('creator_unwrap_wsol'))==0
   self.send('native_creator_transfer_exact_new_fee',[ix('legacy_token',bytes([12])+struct.pack('<QB',creator_delta,9),[am('creator_wsol',w=True),am('wsol_mint'),am('creator_unwrap_wsol',w=True),am('beneficiary',s=True)])],[self.w])
  rows=[]
  for role,n in [('creator_unwrap_wsol',creator_delta),('locker_receipt_wsol',locker_delta)]:
   if not n:continue
   assert amt(self.account(role))==n;deposit=self.account(role).lamports-n;p0=self.svm.get_balance(K['payer']);w0=self.svm.get_balance(K['beneficiary']);ops=[ix('legacy_token',bytes([9]),[am(role,w=True),am('payer',w=True),am('beneficiary',s=True)]),sol(K['payer'],K['beneficiary'],n)]
   if late:ops.append(sol(K['payer'],K['beneficiary'],2**64-1))
   row=self.send('native_unwrap_exact_'+role+('_late_failure' if late else ''),ops,[self.w],expected='OBSERVE' if late else None);row['unwrap_accounting']=dict(fee_output=n,advanced_storage=deposit,creator_bankroll_excluded=True)
   if not late:assert (self.account(role) is None or (self.account(role).lamports==0 and len(self.account(role).data)==0 and self.account(role).owner==K['system'])) and self.svm.get_balance(K['beneficiary'])-w0==n and self.svm.get_balance(K['payer'])-p0==deposit-row['expected_network_fee']
   else:assert row['status']=='FAILURE' and 'Custom(1)' in row['error'] and row['rollback_verified']
   self.sentinels();rows.append(row)
  return rows
