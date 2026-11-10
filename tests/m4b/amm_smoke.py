import json,traceback,sys
from amm import *
def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);v=None
 try:
  v=AMM(label);v.initialize_pool();v.burn_initial();v.clock(9,16352,1700000000);v.swap(True,10**10);v.swap(False,10**9);v.collect();row=dict(status='ACTUAL_CPMM_INIT_LP_BURN_CREATOR_SMOKE_PASS',initial_LP_receipt=v.initial_receipt,resources=resources())
 except BaseException:row=dict(status='FAIL',traceback=traceback.format_exc(),resources=resources())
 finally:
  if v:v.events_to(out/'events.json')
  save(out/'RESULT.json',row);print(json.dumps(row));return 0 if row['status']!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
