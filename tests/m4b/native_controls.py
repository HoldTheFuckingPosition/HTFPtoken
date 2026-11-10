"""Unchanged H/native withholding provenance under mixed fixture, no H Process."""
import json,sys,traceback
from runtime import *
from solders.litesvm import LiteSVM

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);packets=[];original=LiteSVM.send_transaction;old_events=m3.EVENTS;old_fixture=m3.NATIVE_FIXTURE;m3.EVENTS=[]
 def recording(self,tx):
  r=original(self,tx);meta=r.meta() if isinstance(r,FailedTransactionMetadata) else r
  packets.append(dict(transaction_hex=bytes(tx).hex(),recent_blockhash=str(tx.message.recent_blockhash),signatures=[str(s) for s in tx.signatures],packet_bytes=len(bytes(tx)),compute_units=meta.compute_units_consumed(),signature_verification=True,blockhash_verification=True,heap_bytes=32768,status='FAILURE' if isinstance(r,FailedTransactionMetadata) else 'SUCCESS'))
  assert len(bytes(tx))<=1232 and meta.compute_units_consumed()<=1400000;return r
 try:
  for env,kind,feature in [('M3_ELF','htfp','local-m3'),('M3_DEFAULT_ELF','htfp','DEFAULT_DISABLED'),('M3_HELPER_ELF','helper','local-m3')]:
   a=M3_ARTIFACTS[env];data,record=validate_artifact(a['path'],kind,feature);assert sha(data)==a['sha256'];os.environ[env]=a['path'];m3.ARTIFACTS[env]=data
  m3.NATIVE_FIXTURE=MixedFixture();LiteSVM.send_transaction=recording
  class FrozenHControlVM(m3.VM):
   def clock(self,e):
    p=PROFILE['clock'];slot={7:p['genesis_slot'],8:p['epoch8_slot'],9:p['active_slot']}[e];unix={7:p['genesis_unix'],8:p['epoch8_unix'],9:p['active_unix']}[e]
    self.svm.warp_to_slot(slot);self.svm.set_clock(Clock(slot,0,e,e,unix));m3.EVENTS.append(dict(kind='synthetic_clock',epoch=e,slot=slot,unix=unix))
  v=FrozenHControlVM(label);v.clock(9);holder=v.create_token('actual_withheld_holder');v.token_transfer(holder,200000000000);assert v.view('actual_withheld_holder')['withheld']==16000000000
  v.send('unchanged_H_recover_actual_1600HTFP',[v.recover_ix([holder])]);assert v.view('inventory')['R']==16000000000 and v.view('custody')['spendable']==16000000000
  v.token_transfer(m3.K['custody'],5000000000);assert v.view('inventory')['R']==16000000000 and v.view('custody')['spendable']==20600000000 and v.view('custody')['withheld']==400000000
  v.send('later_independent_H_recover_donation_tax',[v.recover_ix()]);assert v.view('inventory')['R']==16400000000 and v.view('custody')['spendable']==21000000000 and v.view('custody')['withheld']==0
  row=dict(status='ACTUAL_UNCHANGED_H_NATIVE_PROVENANCE_PASS',initial_recovery=16000000000,donation_gross=5000000000,donation_spendable_outside_R=4600000000,donation_withheld_later_recovered=400000000,final_R=16400000000,final_custody=21000000000,transactions=len(packets),native_fixture=m3.NATIVE_FIXTURE.describe(),H_artifact=M3_ARTIFACTS['M3_ELF'],resources=resources(),limitations=['No Process/Volume/F17 H integration','No native wSOL mint dependency restoration in this independent control'])
 except BaseException:row=dict(status='FAIL',traceback=traceback.format_exc(),resources=resources())
 finally:
  LiteSVM.send_transaction=original;save(out/'events.json',m3.EVENTS);save(out/'serialized_transactions.json',packets);m3.EVENTS=old_events;m3.NATIVE_FIXTURE=old_fixture;save(out/'RESULT.json',row)
 print(json.dumps(row));return 0 if row['status']!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
