"""Frozen finite native cases. Discovery binds exact observations for a separate final run."""
from runtime import *
import gc,json
CASES=json.loads((ROOT/'config/m5-locker/cases.json').read_text())
def classification(row):
 return dict(status=row['status'],error=row['error'],native_error_logs=[l for l in row['logs'] if 'AnchorError' in l or l.startswith('Program log: Error:')],outer_native_programs=[op['program_id'] for op in row['requested_instructions'][1:]])
def change(op,indices=None,data=None):
 metas=list(op.accounts)
 for i,kwargs in (indices or {}).items():
  m=metas[i];metas[i]=AccountMeta(kwargs.get('key',m.pubkey),kwargs.get('s',m.is_signer),kwargs.get('w',m.is_writable))
 return Instruction(op.program_id,bytes(op.data) if data is None else data,metas)
def fresh(label,locked=False,earned=False,metadata=True):
 v=VM(label);v.setup_pool()
 if locked:v.lock(metadata=metadata);v.position_start();v.receipts()
 if earned:v.accrue()
 return v
class Suite:
 def __init__(self,expected=None):self.records=[];self.expected=expected;self.manifest={};self.main=None
 def record(self,fid,index,row,kind='positive',extra=None):
  spec=next(x for x in CASES['families'] if x['id']==fid);key=f'{fid}.{index}';assert not any(r['key']==key for r in self.records);r=dict(key=key,family=fid,subcase=spec['finite_subcases'][index],kind=kind,status=row['status'],error=row['error'],transaction_sha256=row['transaction_sha256'],message_sha256=row['message_sha256'],fixture=row['fixture'],name=row['name'],compute_units=row['compute_units'],extra=extra);self.records.append(r)
  observed=classification(row)
  if kind=='negative':assert row['status']=='FAILURE' and row.get('rollback_verified'),r
  elif kind=='positive':assert row['status']=='SUCCESS',r
  else:assert kind=='diagnostic'
  if row['status']=='FAILURE' and not row.get('control'):assert any('invoke [1]' in x for x in row['logs']),r
  if self.expected is not None:assert observed==self.expected[key],(key,observed,self.expected[key])
  self.manifest[key]=observed
  print(key,row['status'],row['error'] or '',flush=True)
  if row.get('principal_diagnostic'):assert row['principal_diagnostic']['holds'],row['principal_diagnostic']
  return row
 def negative(self,v,fid,index,op,signers=(),payer=None,extra=None):return self.record(fid,index,v.send(f'{fid}_{index}',[op],signers,expected='OBSERVE',payer=payer),'negative',extra)
 def run(self):
  v=VM('suite_main');self.main=v
  for i,c in enumerate([None,'invalid_signature','expired_blockhash']):self.record('L01',i,v.send('runtime_'+str(c),[sol(K['payer'],K['beneficiary'],1)],control=c),'positive' if i==0 else 'negative')
  v.setup_pool();poolrow=next(r for r in reversed(EVENTS) if r.get('name')=='genuine_Some_BothToken_pool_0pct');self.record('L02',0,poolrow)
  lock=v.lock();self.record('L03',0,lock,extra={'compiled_LP_writable':next(x['writable'] for x in lock['actual_compiled_accounts'] if x['pubkey']==str(K['lp_mint']))});self.record('L04',0,lock);self.record('L05',0,lock);assert amt(v.account('creator_lp'))==0 and amt(v.account('shared_lp_escrow'))==v.initial_receipt
  mint=M3.mint_view(bytes(v.account('fee_key_mint_1').data));assert mint['supply']==1 and mint['decimals']==0 and mint['mint_authority'] is None and mint['freeze_authority'] is None
  v.position_start();v.receipts()
  w=fresh('L03_CPI');r=w.lock(writable=True);self.record('L03',1,r,extra={'compiled_LP_writable':next(x['writable'] for x in r['actual_compiled_accounts'] if x['pubkey']==str(K['lp_mint']))});assert self.records[-1]['extra']['compiled_LP_writable'];del w;gc.collect()
  w=fresh('L04_false');r=w.lock(metadata=False);self.record('L04',1,r,extra={'metadata_exists':w.account('metadata_1') is not None,'metadata_program_getter':w.program_view('metadata')});del w;gc.collect()
  w=fresh('L06_preexisting');w.deposit_B();w.secondary_lock();assert amt(w.account('shared_lp_escrow'))==5000000000;s2=bytes(w.account('lock_state_2').data);r=w.lock();w.position_start();assert w.position['q0']==w.initial_receipt and amt(w.account('shared_lp_escrow'))==5000000000+w.initial_receipt and bytes(w.account('lock_state_2').data)==s2;self.record('L06',0,r);del w;gc.collect()
  # Empty claim uses fresh native state before any trading.
  w=fresh('L19_empty',True);r=w.send('empty_MAX',[w.claim_ix()],[w.w],expected='OBSERVE');self.record('L19',0,r,'diagnostic');assert r['status']=='FAILURE' or w.pool_view()['escrow']==w.initial_receipt;del w;gc.collect()
  v.accrue();creator=v.collect_creator();first=v.claim();self.record('L08',0,first,extra={'creator':creator['creator_accounting'],'locker':first['claim_accounting'],'principal':first['principal_diagnostic']});firstcreator=creator['creator_accounting']['net'][0];firstlocker=first['claim_accounting']['net'][0]
  r=v.send('repeat_MAX',[v.claim_ix()],[v.w],expected='OBSERVE');self.record('L19',1,r,'diagnostic');assert r['status']=='FAILURE' or amt(v.account('locker_receipt_wsol'))==firstlocker
  w=fresh('L08_reverse',True,True);second=w.claim();cr=w.collect_creator();assert all(second['claim_accounting'][k]==first['claim_accounting'][k] for k in ['burn','gross','net','withheld']) and all(cr['creator_accounting'][k]==creator['creator_accounting'][k] for k in ['gross','net','withheld']);self.record('L08',1,second,extra={'creator':cr['creator_accounting'],'locker':second['claim_accounting'],'principal':second['principal_diagnostic'],'order_payout_match':True});del w;gc.collect()
  # Genuine fee-only close routes; demonstrate atomic rollback before successful close.
  late=v.unwrap(0,firstlocker,True)[0];self.record('L26',2,late,'negative');rows=v.unwrap(firstcreator,firstlocker);self.record('L26',0,rows[0]);self.record('L26',1,rows[1]);self.recreate_wsol(v)
  dep=v.deposit_B();self.record('L07',0,dep,extra=dep['deposit_accounting']);v.secondary_lock();v.accrue(later=True);s1=bytes(v.account('lock_state_1').data);r=v.claim(variant='secondary');assert bytes(v.account('lock_state_1').data)==s1 and amt(v.account('unrelated_lp'))==5000000000;self.record('L07',1,r,extra=r['principal_diagnostic'])
  # Authority failures from genuine complete states, before and after actual NFT transfers.
  v.ata('payer_fee_key_1_wrong','fee_key_mint_1','legacy_token','payer');v.ata('transferred_fee_key_1','fee_key_mint_1','legacy_token','unrelated_owner')
  self.negative(v,'L10',0,v.claim_ix(mapping={'beneficiary':K['payer'],'fee_key_account_1':K['payer_fee_key_1_wrong']}))
  self.negative(v,'L10',2,v.claim_ix(mapping={'beneficiary':K['unrelated_owner'],'fee_key_account_1':K['transferred_fee_key_1']}),[v.b])
  self.negative(v,'L10',3,v.claim_ix(mapping={'fee_key_account_1':K['creator_lp']}),[v.w]);self.negative(v,'L10',4,v.claim_ix(mapping={'fee_key_account_1':K['transferred_fee_key_1']}),[v.w]);self.negative(v,'L10',5,v.claim_ix(mapping={'fee_key_account_1':K['fee_key_account_2'],'beneficiary':K['unrelated_owner']}),[v.b])
  v.nft_transfer();self.negative(v,'L10',1,v.claim_ix(),[v.w]);v.accrue(later=True);s2=bytes(v.account('lock_state_2').data);r=v.claim(variant='transferred');assert bytes(v.account('lock_state_2').data)==s2;v.nft_transfer(False);v.accrue(later=True);r2=v.claim();self.record('L09',0,r2,extra={'transferred_claim':r['claim_accounting'],'returned_claim':r2['claim_accounting'],'principal':r2['principal_diagnostic']})
  # Lock negatives may share only fully reverted valid prestate.
  w=fresh('lock_relationships')
  substitutions=[(0,'amm_authority'),(8,'wsol_mint'),(9,'unrelated_wsol'),(10,'creator_lp'),(6,'inventory'),(11,'creator_wsol'),(18,'legacy_token'),(16,'token2022')]
  for i,(index,role) in enumerate(substitutions):self.negative(w,'L13',i,change(w.lock_ix(),{index:{'key':K[role]}}),[w.w,w.signers['fee_key_mint_1']])
  aliases=[(9,'shared_lp_escrow'),(8,'fee_key_mint_1'),(7,'metadata_1'),(10,'creator_lp')]
  # L16 state-as-NFT is a claim-side substitution below; other three are Lock contexts.
  for caseindex,(index,role) in zip([1,2,3],aliases[1:]):self.negative(w,'L16',caseindex,change(w.lock_ix(),{index:{'key':K[role]}}),[w.w,w.signers['fee_key_mint_1']])
  del w;gc.collect()
  for i,n in enumerate([1000000000000-99,2**64-1]):
   w=fresh('L12_'+str(i));op=w.lock_ix();data=bytes(op.data)[:8]+struct.pack('<Q',n)+bytes([1]);self.negative(w,'L12',i,change(op,data=data),[w.w,w.signers['fee_key_mint_1']]);del w;gc.collect()
  # Claim relationships, one supplied relation at a time on a complete valid earned setup.
  v.accrue(later=True)
  substitutions=[(3,'lock_state_2'),(6,'inventory'),(7,'wsol_mint'),(14,'unrelated_lp'),(10,'creator_wsol'),(13,'wsol_mint'),(4,'locker'),(17,'legacy_token'),(9,'creator_wsol')]
  for i,(index,role) in enumerate(substitutions):self.negative(v,'L14',i,change(v.claim_ix(),{index:{'key':K[role]}}),[v.w])
  self.negative(v,'L16',0,change(v.claim_ix(),{2:{'key':K['lock_state_1']}}),[v.w]);self.negative(v,'L16',4,change(v.claim_ix(),{8:{'key':K['vault_htfp']}}),[v.w])
  # Genuine burn (zero) and explicitly rejection-only amount2 corruption use separate instances.
  for i in range(2):
   w=fresh('L11_'+str(i),True,True)
   if i==0:w.send('native_burn_FeeKey1',[ix('legacy_token',bytes([8])+struct.pack('<Q',1),[am('fee_key_account_1',w=True),am('fee_key_mint_1',w=True),am('beneficiary',s=True)])],[w.w])
   else:
    a=w.account('fee_key_account_1');data=bytearray(a.data);struct.pack_into('<Q',data,64,2);w.svm.set_account(K['fee_key_account_1'],Account(a.lamports,bytes(data),a.owner,a.executable,a.rent_epoch));EVENTS.append(dict(kind='explicit_rejection_only_corruption',fixture=w.label,role='fee_key_account_1',amount=2,never_positive_entitlement=True))
   self.negative(w,'L11',i,w.claim_ix(),[w.w]);del w;gc.collect()
  # Missing-signature cases explicitly remove the requested privilege and signer; P-negative uses B fee payer.
  for i in range(5):
   w=fresh('L15_'+str(i),i>=3,i>=3)
   if i<3:
    index=[2,4,1][i];op=change(w.lock_ix(),{index:{'s':False}});signers=[w.w,w.signers['fee_key_mint_1']];payer=None
    if i==0:signers=[w.signers['fee_key_mint_1']]
    if i==1:signers=[w.w]
    if i==2:payer=w.b
    self.negative(w,'L15',i,op,signers,payer)
   else:self.negative(w,'L15',i,change(w.claim_ix(),{3 if i==3 else 8:{'w':False}}),[w.w])
   del w;gc.collect()
  # Valid finite domain: all selected sizes execute, with enough genuine balances and no filtering.
  w=fresh('L17_finite',True);w.clock('trades')
  for i,spec in enumerate(CASES['families'][16]['finite_subcases']):self.record('L17',i,w.swap(spec['input']=='HTFP',int(spec['gross'])))
  del w;gc.collect()
  for i,spec in enumerate(CASES['families'][17]['finite_subcases']):
   w=fresh('L18_'+str(i),True);w.clock('trades');r=w.swap(spec['input']=='HTFP',int(spec['gross']),observe=True);self.record('L18',i,r,'diagnostic');del w;gc.collect()
  w=fresh('L19_zero',True,True);before=w.pool_view();r=w.send('zero_request',[w.claim_ix(0)],[w.w],expected='OBSERVE');self.record('L19',2,r,'diagnostic');assert r['status']=='FAILURE' or w.pool_view()['escrow']==before['escrow'];del w;gc.collect()
  for i,n in enumerate([1,2,5,1000000,2**64-1]):
   w=fresh('L20_'+str(i),True,True);r=w.send('finite_fee_LP_'+str(n),[w.claim_ix(n)],[w.w],expected='OBSERVE');self.record('L20',i,r,'diagnostic')
   if r['status']=='SUCCESS':self.audit_raw_claim(w,r,n)
   del w;gc.collect()
  # Mint-correct P-owned recipients: explicitly measure destination authorization, do not assume rejection.
  v.ata('payer_wsol','wsol_mint','legacy_token','payer');v.ata('payer_htfp','mint','token2022','payer');r=v.send('holder_directed_P_owned_recipients',[v.claim_ix(mapping={'locker_receipt_wsol':K['payer_wsol'],'locker_receipt_htfp':K['payer_htfp']})],[v.w],expected='OBSERVE');self.record('L21',0,r,'diagnostic',{'destination_owned_by_P':True})
  if r['status']=='SUCCESS':self.audit_raw_claim(v,r,2**64-1,recips=['payer_wsol','payer_htfp']);v.position['burned']+=r['raw_claim_audit']['burn']
  # Later transaction failure must occur after native Lock success and revert all creation/storage effects.
  for i,metadata in enumerate([True,False]):
   w=fresh('L22_'+str(i));r=w.send('Lock_then_late_System',[w.lock_ix(metadata=metadata),sol(K['payer'],K['beneficiary'],2**64-1)],[w.w,w.signers['fee_key_mint_1']],expected='OBSERVE');self.record('L22',i,r,'negative');assert any(str(K['locker'])+' success' in s for s in r['logs']) and r['error']=='TransactionErrorInstructionError((2, Tagged(Custom(InstructionErrorCustom(1)))))';del w;gc.collect()
  v.accrue(later=True);r=v.send('claim_then_late_System',[v.claim_ix(),sol(K['payer'],K['beneficiary'],2**64-1)],[v.w],expected='OBSERVE');self.record('L23',0,r,'negative');assert any(str(K['locker'])+' success' in s for s in r['logs'])
  # Independent operation calibrations followed by exact meter cuts. Each failed cut restores the same prestate.
  w=fresh('L24_lock_calibration');cal=w.lock()['compute_units'];del w;gc.collect();w=fresh('L24_lock_cuts')
  for i,margin in enumerate([1,1000,4000,16000,40000,80000]):
   r=w.send('cut_Lock_'+str(margin),[w.lock_ix()],[w.w,w.signers['fee_key_mint_1']],expected='OBSERVE',cu=max(5000,cal-margin));self.record('L24',i,r,'diagnostic',{'calibration_CU':cal,'margin':margin,'phase_logs':r['logs']});assert r['status']=='FAILURE' and ('ComputationalBudgetExceeded' in r['error'] or 'ProgramFailedToComplete' in r['error'])
  del w;gc.collect();w=fresh('L24_claim_calibration',True,True);cal=w.claim()['compute_units'];del w;gc.collect();w=fresh('L24_claim_cuts',True,True)
  for i,margin in enumerate([1,1000,4000,16000,40000,80000]):
   r=w.send('cut_claim_'+str(margin),[w.claim_ix()],[w.w],expected='OBSERVE',cu=max(5000,cal-margin));self.record('L24',i+6,r,'diagnostic',{'calibration_CU':cal,'margin':margin,'phase_logs':r['logs']});assert r['status']=='FAILURE' and ('ComputationalBudgetExceeded' in r['error'] or 'ProgramFailedToComplete' in r['error'])
  del w;gc.collect()
  self.negative(v,'L25',0,v.lock_ix(),[v.w,v.signers['fee_key_mint_1']]);v.accrue(later=True);r=v.claim();self.record('L25',1,r,extra=r['principal_diagnostic']);assert amt(v.account('unrelated_lp'))==5000000000
  assert len(self.records)==107 and len(set(r['family'] for r in self.records))==26,(len(self.records),[r['key'] for r in self.records]);del v;self.main=None;gc.collect();return self.records
 def recreate_wsol(self,v):
  d=PROFILE['derivations']['locker_receipt_wsol'];v.send('recreate_closed_wsol_receipt',[create_account_with_seed(dict(from_pubkey=K['payer'],to_pubkey=K['locker_receipt_wsol'],base=K['payer'],seed=d['seed_UTF8'],lamports=v.svm.minimum_balance_for_rent_exemption(165),space=165,owner=K['legacy_token'])),ix('legacy_token',bytes([18])+bytes(K['beneficiary']),[am('locker_receipt_wsol',w=True),am('wsol_mint')])])
 def audit_raw_claim(self,v,r,requested,recips=None):
  recips=recips or ['locker_receipt_wsol','locker_receipt_htfp'];b=r['before'];a=r['after'];raw=lambda d,k:bytes.fromhex(d[k]['data_hex']);u=lambda d,k,o:struct.unpack_from('<Q',raw(d,k),o)[0];burn=u(b,'shared_lp_escrow',64)-u(a,'shared_lp_escrow',64);L=u(b,'pool',333);x=[u(b,k,64)-sum(u(b,'pool',o) for o in offsets) for k,offsets in [('vault_wsol',[341,357,397]),('vault_htfp',[349,365,405])]];gross=[u(b,k,64)-u(a,k,64) for k in ['vault_wsol','vault_htfp']];net=[u(a,k,64)-u(b,k,64) for k in recips];withheld=M3.token_view(raw(a,recips[1]))['withheld']-M3.token_view(raw(b,recips[1]))['withheld'];r['raw_claim_audit']=dict(burn=burn,gross=gross,net=net,HTFPwithheld=withheld,source_floor=[q*burn//L for q in x]);assert 0<=burn<=requested and gross==[q*burn//L for q in x] and net==[gross[0],gross[1]-QUOTE.token_tax(gross[1])] and withheld==QUOTE.token_tax(gross[1]);assert burn==u(b,'pool',333)-u(a,'pool',333)==u(b,'lp_mint',36)-u(a,'lp_mint',36)
