"""Offline verification and exact observations; never constructs a native VM."""
from common import *
import argparse,struct,math,traceback
from solders.transaction import Transaction

def number(s,role,offset):return struct.unpack_from('<Q',bytes.fromhex(s[role]['data_hex']),offset)[0]
def withheld(s,role):
 data=bytes.fromhex(s[role]['data_hex']);offset=166
 while offset+4<=len(data):
  typ,n=struct.unpack_from('<HH',data,offset);offset+=4
  if typ==2:assert n==8;return struct.unpack_from('<Q',data,offset)[0]
  offset+=n
 return 0
def pool(s):
 v=[number(s,r,64) for r in ['vault_wsol','vault_htfp']];p=[number(s,'pool',o) for o in [341,349]];f=[number(s,'pool',o) for o in [357,365]];c=[number(s,'pool',o) for o in [397,405]];return dict(v=v,p=p,f=f,c=c,x=[v[i]-p[i]-f[i]-c[i] for i in range(2)],L=number(s,'pool',333),supply=number(s,'lp_mint',36),escrow=0 if s['shared_lp_escrow'] is None else number(s,'shared_lp_escrow',64))
def qmin(n,d):
 q=math.isqrt(n//d);return q+(q*q*d<n)
def observed(r):return dict(status=r['status'],error=r['error'],native_error_logs=[l for l in r['logs'] if 'AnchorError' in l or l.startswith('Program log: Error:')],outer_native_programs=[i['program_id'] for i in r['requested_instructions'][1:]])
def choose(rows,c):
 selected=[(i,r) for i,r in enumerate(rows) if r.get('kind')=='transaction' and (r['fixture'],r['name'],r['transaction_sha256'])==(c['fixture'],c['name'],c['transaction_sha256'])];assert len(selected)==1,(c,len(selected));return selected[0]
def load_events(folder):
 p=folder/'events.json.gz';b=p.read_bytes();f=json.loads((folder/'events.json.gz.FORMAT.json').read_text());raw=gzip.decompress(b);assert sha(b)==f['stored_sha256'] and len(b)==f['stored_bytes'] and sha(raw)==f['decoded_sha256'] and len(raw)==f['decoded_bytes'];return json.loads(raw)
def verify_row(r):
 data=bytes.fromhex(r['transaction_hex']);assert sha(data)==r['transaction_sha256'] and len(data)==r['packet_bytes']<=1232;t=Transaction.from_bytes(data);assert bytes(t.message).hex()==r['message_hex'] and sha(bytes(t.message))==r['message_sha256'];assert len(t.signatures)==r['signature_count'];valid=True
 try:t.verify()
 except Exception:valid=False
 assert valid==(r.get('control')!='invalid_signature');assert r['compute_units']<=r['compute_unit_limit']<=1400000 and r['signature_verification'] and r['blockhash_verification']
 if r['status']=='FAILURE':
  for role,b in r['before'].items():
   expected=None if b is None else dict(b)
   if expected and expected['address']==r['payer']:expected['lamports']-=r['expected_network_fee']
   assert expected==r['after'][role],(r['fixture'],r['name'],role)
  assert r['expected_network_fee']==(0 if r.get('control') else r['signature_count']*5000)
 # Snapshots contain aliases: reconcile them before counting distinct accounts or deltas.
 for snap in [r['before'],r['after']]:
  unique={}
  for a in snap.values():
   if a is None:continue
   assert len(bytes.fromhex(a['data_hex']))==a['bytes'] and sha(bytes.fromhex(a['data_hex']))==a['data_sha256']
   if a['address'] in unique:assert unique[a['address']]==a
   unique[a['address']]=a
 return valid

def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);a=p.parse_args();integrity(a.fixture);out=OUT/a.label;before=freeze(out);result=dict(status='INCOMPLETE',command=sys.argv,instances=0,attempts=0);proof={};manifest={};associations={}
 try:
  allruns={}
  for folder in sorted(OUT.glob('*')):
   if not folder.is_dir() or folder==out or not (folder/'events.json.gz').exists():continue
   rows=load_events(folder);allruns[folder.name]=rows;tx=[r for r in rows if r.get('kind')=='transaction'];run=json.loads((folder/'RESULT.json').read_text());assert len(tx)==run['attempts'];assert len({r['fixture'] for r in rows if r.get('kind')=='native_program_artifact_associations'})==run['instances']
   for r in tx:verify_row(r)
   associations[folder.name]=dict(result_sha256=file_sha(folder/'RESULT.json'),trace_sha256=file_sha(folder/'events.json.gz'),inputs_sha256=file_sha(folder/'INPUTS.json'),instances=run['instances'],attempts=run['attempts'],native_success=sum(r['status']=='SUCCESS' for r in tx),native_failure=sum(r['status']=='FAILURE' for r in tx))
  rows=allruns['remaining-focus-001'];fixture='focused_claim_cuts';local=[r for r in rows if r.get('kind')=='transaction' and r['fixture']==fixture];lock=next(r for r in local if r['name'].startswith('standalone_Lock'));dep=next(r for r in local if r['name']=='native_B_proportional_deposit');secondary=next(r for r in local if r['name']=='native_B_secondary_lock');claim=next(r for r in reversed(local) if r['name'].startswith('native_locker_claim'))
  start=pool(lock['after']);d0=pool(dep['before']);d1=pool(dep['after']);cb=pool(claim['before']);ca=pool(claim['after']);q0=number(lock['before'],'creator_lp',64)-number(lock['after'],'creator_lp',64);assert q0==start['escrow']-pool(lock['before'])['escrow']==999999999900
  burn=cb['escrow']-ca['escrow'];assert burn==cb['L']-ca['L']==cb['supply']-ca['supply']==16036284
  bq=pool(secondary['after'])['escrow']-pool(secondary['before'])['escrow'];assert bq==5000000000;assert number(claim['after'],'unrelated_lp',64)==5000000000;assert claim['before']['lock_state_2']==claim['after']['lock_state_2'];q=q0-burn;assert q>=0 and ca['escrow']==q+bq
  k0=start['x'][0]*start['x'][1];kn=ca['x'][0]*ca['x'][1];N=d1['x'][0]*d1['x'][1]*d0['L']**2;D=d0['x'][0]*d0['x'][1]*d1['L']**2;lhs0=q*q*kn*start['L']**2;rhs0=q0*q0*k0*ca['L']**2;lhs=lhs0*D;rhs=rhs0*N;minimum=qmin(q0*q0*k0*ca['L']**2*N,kn*start['L']**2*D)
  gross=[cb['v'][i]-ca['v'][i] for i in range(2)];expected=[cb['x'][i]*burn//cb['L'] for i in range(2)];assert gross==expected and all(cb[k]==ca[k] for k in ['p','f','c']);net=[number(claim['after'],r,64)-number(claim['before'],r,64) for r in ['locker_receipt_wsol','locker_receipt_htfp']];tax=(gross[1]*800+9999)//10000;actual_tax=withheld(claim['after'],'locker_receipt_htfp')-withheld(claim['before'],'locker_receipt_htfp');assert actual_tax==tax;assert net==[gross[0],gross[1]-tax]
  deposit_lp=d1['L']-d0['L'];deposit_net=[d1['v'][i]-d0['v'][i] for i in range(2)];deposit_ceil=[(x*deposit_lp+d0['L']-1)//d0['L'] for x in d0['x']];deposit_htfp_gross=number(dep['before'],'unrelated_htfp',64)-number(dep['after'],'unrelated_htfp',64);deposit_tax=withheld(dep['after'],'vault_htfp')-withheld(dep['before'],'vault_htfp');assert deposit_lp==d1['supply']-d0['supply']==10**10 and deposit_net==deposit_ceil and deposit_htfp_gross-deposit_tax==deposit_net[1] and deposit_tax==(deposit_htfp_gross*800+9999)//10000
  keys=[x['pubkey'] for x in claim['actual_compiled_accounts']];withdraws=[];burns=[]
  for group in claim['actual_inner_instructions']:
   for op in group:
    data=bytes.fromhex(op['data_hex']);pid=keys[op['program_id_index']]
    if pid==PROFILE['identities']['amm']['base58'] and data[:8]==bytes.fromhex('b712469c946da122'):
     actual=[keys[i] for i in op['accounts']];assert actual==[PROFILE['identities'][m['role']]['base58'] for m in ABI['CPMM_inner_withdraw_audit_variants']['primary']['accounts']];withdraws.append(struct.unpack_from('<Q',data,8)[0])
    if pid==PROFILE['identities']['legacy_token']['base58'] and data and data[0] in [8,15] and keys[op['accounts'][1]]==PROFILE['identities']['lp_mint']['base58']:burns.append(struct.unpack_from('<Q',data,1)[0])
  assert withdraws==burns==[burn];assert minimum-q==2 and lhs<rhs and lhs0>=rhs0
  diagnostic=claim['principal_diagnostic'];assert all(diagnostic[k]==v for k,v in dict(q=q,lhs=lhs,rhs=rhs,qmin=minimum,shortfall_LP=2).items())
  proof=dict(status='REPRODUCED_OFFLINE_FROM_ACTUAL_RAW_NATIVE_STATE',scope='Bounded normalized effective liquidity diagnostic; not proof of theft, perpetual protection, market value or unknown native handler formula.',q0=q0,q=q,burn=burn,secondary_attributable_LP=bq,secondary_mobile_LP=5000000000,shared_escrow=ca['escrow'],K0=k0,K_now=kn,L0=start['L'],L_now=ca['L'],capital_N=N,capital_D=D,unadjusted_lhs=lhs0,unadjusted_rhs=rhs0,unadjusted_holds=lhs0>=rhs0,adjusted_lhs=lhs,adjusted_rhs=rhs,adjusted_holds=lhs>=rhs,qmin=minimum,shortfall_LP=minimum-q,actual_gross=gross,actual_net=net,HTFP_withheld=actual_tax,deposit_minted_LP=deposit_lp,deposit_net=deposit_net,deposit_source_ceil=deposit_ceil,deposit_HTFP_gross=deposit_htfp_gross,deposit_HTFP_withheld=deposit_tax,actual_clocks={r['name']:r['actual_runtime_before']['clock'] for r in [lock,dep,secondary,claim]},native_LP_burns=burns,actual_CPMM_withdraw=withdraws,conservation_holds=True,native_transaction_sha256=claim['transaction_sha256'],native_message_sha256=claim['message_sha256'],trace_path=str((OUT/'remaining-focus-001/events.json.gz').relative_to(ROOT)),fixture=fixture,name=claim['name'],event_index=next(i for i,r in enumerate(rows) if r is claim),no_tolerance_added=True)
  # Original discovery's mismatched-state CU cut is explicitly superseded, not accepted as budget exhaustion.
  for runname in ['finite-discovery-001','remaining-focus-001']:
   cases=json.loads((OUT/runname/'CASES.json').read_text());rs=allruns[runname]
   for c in cases:
    if runname=='finite-discovery-001' and c['key']=='L24.6':continue
    index,r=choose(rs,c);assert c['key'] not in manifest
    manifest[c['key']]=dict(subcase=c['subcase'],kind=c['kind'],observed=observed(r),trace_run=runname,event_index=index,fixture=r['fixture'],name=r['name'],transaction_sha256=r['transaction_sha256'],message_sha256=r['message_sha256'],acceptance='FOCUSED_OBSERVATION_ONLY_NOT_FINAL_ACCEPTANCE')
  manifest['L25.1']=dict(subcase='repeat_swaps_and_claims_after_first_claim',kind='positive_with_principal_diagnostic',observed=observed(claim),trace_run='remaining-focus-001',event_index=proof['event_index'],fixture=fixture,name=claim['name'],transaction_sha256=claim['transaction_sha256'],message_sha256=claim['message_sha256'],acceptance='FAIL_ADJUSTED_PRINCIPAL_DIAGNOSTIC',shortfall_LP=2)
  contract=json.loads((ROOT/'config/m5-locker/cases.json').read_text());required={f"{f['id']}.{i}" for f in contract['families'] for i in range(len(f['finite_subcases']))};assert set(manifest)==required and len(manifest)==107
  for key in ['L13.0','L13.1']:manifest[key]['acceptance']='LIMITED_RUNTIME_MISSING_ACCOUNT_REJECTION_NOT_SPECIFIC_TYPED_CONSTRAINT_PROOF'
  baseline=ROOT/'evidence/m5/LOCKER_CONTINUATION_PRESERVATION_BASELINE.json';base=json.loads(baseline.read_text());allow=set(base['allowed_existing_metadata_edits']);mismatch=[n for n,h in base['files_sha256'].items() if n not in allow and file_sha(ROOT/n)!=h];assert not mismatch
  result.update(status='OFFLINE_AUDIT_PASS_MATERIAL_DIAGNOSTIC_FAILURE_CONFIRMED',preservation=dict(baseline=str(baseline.relative_to(ROOT)),sha256=file_sha(baseline),files=len(base['files_sha256']),nonpermitted_mismatches=mismatch),observed_families=26,observed_subcases=107,complete_final_run='NOT_RUN_STOPPED_ON_MATERIAL_DIAGNOSTIC',cumulative_instances=HISTORY['instances'],cumulative_attempts=HISTORY['attempts'],source_unchanged=True,resources=resources())
 except BaseException:result.update(status='OFFLINE_AUDIT_FAILURE',error=traceback.format_exc())
 finally:
  save(out/'PRINCIPAL_PROOF.json',proof);save(out/'OBSERVATIONS.json',manifest);save(out/'TRIAL_ASSOCIATIONS.json',associations);assert source_inputs()==before;save(out/'RESULT.json',result)
 print(json.dumps(result,indent=2));return 0 if result['status']=='OFFLINE_AUDIT_PASS_MATERIAL_DIAGNOSTIC_FAILURE_CONFIRMED' else 1
if __name__=='__main__':raise SystemExit(main())
