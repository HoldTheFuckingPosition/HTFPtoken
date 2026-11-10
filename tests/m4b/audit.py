"""Read retained raw evidence independently; no native load, signing or execution."""
from pathlib import Path
import base64,json,struct,sys
from common import ROOT,OUT,K,file_sha,sha,save,resources

def u64(raw,off):return struct.unpack_from('<Q',raw,off)[0]
def raw(row):return bytes.fromhex(row['data_hex'])
def audit(label):
 directory=OUT/label;run=json.loads((directory/'RESULT.json').read_text());assert run['status']=='PASS_BOUNDED_STAGE_B_AUTHOR_ONLY' and run['inputs_unchanged']
 before=run['inputs_before_sha256'];assert all(file_sha(ROOT/p)==d for p,d in before.items())
 old=json.loads((OUT/'PRESERVED_INPUTS.json').read_text());changed=[p for p,d in old['payload_sha256'].items() if file_sha(ROOT/p)!=d];cache_changed=[p for p,d in old['cache_source_archive_sha256'].items() if file_sha(ROOT/p)!=d];assert not changed and not cache_changed
 family_counts={};transactions=[];close_events=0;kernel_successes=0
 for family in ['isolated','extended','amm']:
  rows=json.loads((directory/family/'events.json').read_text());tx=[r for r in rows if r['kind']=='transaction'];family_counts[family]={'transactions':len(tx),'success':sum(r['status']=='SUCCESS' for r in tx),'negative':sum(r['status']=='FAILURE' for r in tx)}
  for row in tx:
   packet=bytes.fromhex(row['transaction_hex']);assert len(packet)==row['packet_bytes']<=1232 and sha(packet)==row['transaction_sha256'];assert row['compute_units']<=row['compute_unit_limit']<=1400000 and row['heap_bytes']==32768 and row['signature_verification'] and row['blockhash_verification'];assert len(row['signatures'])==row['signature_count']
   if row['status']=='FAILURE':assert row['rollback_verified']
   if row['status']=='SUCCESS':
    g=row['after']['proof_guard'];v=row['after']['proof_volume']
    if g is not None:
     assert raw(g)[11]==0 and raw(v)[67:80]==bytes(13);kernel_successes+=1
    for line in row['logs']:
     if not line.startswith('Program data: '):continue
     event=base64.b64decode(line.split(': ',1)[1])
     if event[:10]!=b'M4BPEV01\1\5':continue
     assert len(event)==322;record=event[10:266];p,l,d,w,o,v0=[u64(record,off) for off in [52,60,68,76,84,92]]
     assert d==max(0,l-p) and w==max(0,p-l);assert event[266:298]==bytes(K['system']) and event[298:314]==bytes(16);assert u64(event,314)==v0+p+d+o
     assert row['after']['proof_reserve']['lamports']==v0+o
     temp_key=record[108:140];matches=[a for a in row['after'].values() if a is not None and bytes(__import__('solders.pubkey',fromlist=['Pubkey']).Pubkey.from_string(a['address']))==temp_key]
     if p:assert len(matches)==1 and matches[0]['owner']==str(K['system']) and matches[0]['bytes']==0 and matches[0]['lamports']==p
     else:assert not matches or matches[0]['lamports']==0 and matches[0]['bytes']==0 and matches[0]['owner']==str(K['system'])
     close_events+=1
  transactions+=tx
 # Unchanged H/native recovery raw state, not just event claims.
 control=json.loads((directory/'native-controls/events.json').read_text());recoveries=0
 for row in control:
  if row['kind']!='transaction':continue
  for hx in row['htfp_event_hex']:
   e=bytes.fromhex(hx)
   if e[:10]!=b'HTFPEVT1\1\1':continue
   b,a=row['before'],row['after'];rb=u64(raw(b['inventory']),12);ra=u64(raw(a['inventory']),12);cb=u64(raw(b['custody']),64);ca=u64(raw(a['custody']),64)
   assert ra-rb==ca-cb==u64(e,74) and rb==u64(e,82) and ra==u64(e,90);assert u64(raw(b['mint']),36)==u64(raw(a['mint']),36);recoveries+=1
 family_counts['native-controls']={'transactions':sum(r['kind']=='transaction' for r in control),'raw_recoveries_audited':recoveries}
 report=json.loads((directory/'regression/report.json').read_text());messages=json.loads((directory/'regression/serialized_transactions.json').read_text());assert report['result']=='PASS';assert (int(report['tests_run']),int(report['transaction_count']),int(report['expected_failures']),int(report['failures']),int(report['errors']),int(report['skipped']))==(33,788,93,0,0,0);assert len(messages)==789
 for m in messages:assert len(bytes.fromhex(m['transaction_hex']))==m['packet_bytes']<=1232 and m['compute_units']<=1400000
 family_counts['regression']={'methods':33,'harness_transactions':788,'negative_harness_transactions':93,'all_native_send_attempts_including_invalid_signature_control':789}
 assert sum(p.stat().st_size for p in (directory/'regression').rglob('*') if p.is_file())<=128*1024**2
 # Autofixer source association, with explicitly unknown native framework coverage.
 for crate,record_name in [('kernel','autofixer-kernel-003.json'),('wallet','autofixer-wallet-001.json')]:
  r=json.loads((OUT/record_name).read_text());assert all(file_sha(ROOT/p)==d for p,d in r['source_sha256'].items());s=r['response']['structuredContent'];assert s['framework_detected']=='unknown' and s['require_another_tool_call_after_fixing'] is False
 totals=dict(new_runtime_transactions=len(transactions)+family_counts['native-controls']['transactions'],original_M3_harness_transactions=788,extra_original_invalid_signature_control=1,all_native_send_attempts=len(transactions)+family_counts['native-controls']['transactions']+789,new_suite_methods=29,original_suite_methods=33,methods_total=62,model_cases=json.loads((directory/'volume-model/RESULT.json').read_text())['cases'])
 row=dict(schema='htfp-m4b-raw-evidence-audit-v1',status='AUTHOR_RAW_EVIDENCE_AUDIT_PASS_ONLY',frozen_run=label,input_hashes_unchanged=True,preserved_payload_files=len(old['payload_sha256']),preserved_cache_source_archive_files=len(old['cache_source_archive_sha256']),changed_old_files=changed,changed_cache_files=cache_changed,family_counts=family_counts,totals=totals,successful_closed_kernel_transactions_with_idle_guard_and_frame=kernel_successes,actual_SBF_close_event_equations_checked=close_events,raw_H_recoveries_checked=recoveries,max_new_packet_bytes=max(r['packet_bytes'] for r in transactions),max_new_compute_units=max(r['compute_units'] for r in transactions),max_original_packet_bytes=max(r['packet_bytes'] for r in messages),max_original_CU=max(r['compute_units'] for r in messages),resources=resources(),limitations=['Author audit only, no independent supervisor reproduction/Review','No H Process/Volume/Finalize or public runtime/source match','Malformed Rent is rejected by LiteSVM cache before SBF, not a handler transaction rejection','Finite case coverage, no exhaustive/PBT shrinking claim'])
 save(directory/'RAW_AUDIT.json',row);print(json.dumps(row));return row
if __name__=='__main__':audit(sys.argv[1])
