from pathlib import Path
import json,struct,traceback,sys
from runtime import *

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);vm=None
 try:
  vm=VM(label);vm.bootstrap();vm.send('open_then_close_zero_output',[vm.proof_ix(1,b'\0'),vm.proof_ix(4),vm.proof_ix(5,b'\0'),vm.finish()])
  row=dict(status='NATIVE_ZERO_PREFUND_CLOSE_REFUND_PASS',resources=resources())
 except BaseException:
  row=dict(status='FAIL',traceback=traceback.format_exc(),resources=resources())
 finally:
  if vm:vm.events_to(out/'events.json')
  save(out/'RESULT.json',row);print(json.dumps(row));return 0 if row['status']!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
