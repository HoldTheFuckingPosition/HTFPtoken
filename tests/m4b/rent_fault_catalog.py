"""Bounded labeled malformed rent account observation, no compatibility inference."""
from runtime import *
from solders.sysvar import RENT
import sys,json,traceback

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);v=None
 try:
  v=VM(label);v.bootstrap();a=v.svm.get_account(RENT);v.track('malformed_rent_sysvar',RENT);v.svm.set_account(RENT,Account(a.lamports,b'\0',a.owner,False));v.events.append(dict(kind='EXPLICIT_STRUCTURAL_CORRUPTION_REJECTION_ONLY',case='rent_sysvar_truncated_to1byte',original_sha256=sha(bytes(a.data)),positive_monetary_proof=False))
  row=v.send('malformed_rent_account',[v.proof_ix(1,b'\0'),v.proof_ix(4),v.proof_ix(5,b'\0'),v.finish()],observe=True)
  result=dict(status='OBSERVATION_ONLY',actual_status=row['status'],actual_error=row['error'],logs=row['logs'])
 except BaseException:result=dict(status='FAIL',traceback=traceback.format_exc())
 finally:
  if v:v.events_to(out/'events.json')
  save(out/'RESULT.json',result);print(json.dumps(result))
if __name__=='__main__':main(sys.argv[1])
