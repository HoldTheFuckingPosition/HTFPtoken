from runtime import *
import traceback

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);before=freeze(out);v=None
 try:
  v=AMM(label);v.initialize_pool();v.burn_initial();v.clock(9,16352,1700000000);v.prepare_tax();v.initialize_processing();v.send('actual_H_complete_Process',[v.process_ix(),v.finish()]);assert v.view('inventory')==dict(R=0,guard=0);assert v.view('custody')['spendable']==0;assert v.view('volume')['credit_scaled']==0 and v.view('volume')['sequence']==1
  result=dict(status='ACTUAL_H_NATIVE_CPMM_HAPPY_PATH_PASS',resources=resources())
 except BaseException:result=dict(status='FAIL',traceback=traceback.format_exc(),resources=resources())
 finally:
  if v:v.events_to(out/'events.json')
  result['executed_input_hashes_unchanged']=all(file_sha(ROOT/p)==d for p,d in before.items());save(out/'RESULT.json',result)
 print(json.dumps(result));return 0 if result['status']!='FAIL' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
