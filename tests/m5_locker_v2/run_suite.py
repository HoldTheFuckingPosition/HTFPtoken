"""Discover exact native outcomes, then replay all107cases against frozen classifications."""
import argparse,traceback,gc
from case_suite import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);p.add_argument('--phase',choices=['discover','final'],required=True);p.add_argument('--classifications');a=p.parse_args();integrity(a.fixture);expected=None
 if a.phase=='final':
  raise RuntimeError('Final dependent execution remains gated on separate disposition of remaining-focus-001 adjusted-principal2LP failure. No tolerance or observation may be discarded.')
  assert a.classifications;expected=json.loads(Path(a.classifications).read_text());assert len(expected)==107
 else:assert not a.classifications
 out=OUT/a.label;before=freeze(out);result=dict(status='INCOMPLETE',phase=a.phase,command=sys.argv,fixture=FIXTURE,classifications_input=None if expected is None else dict(path=a.classifications,sha256=file_sha(a.classifications)));suite=Suite(expected)
 try:
  suite.run();result['status']='DISCOVERY_COMPLETE' if a.phase=='discover' else 'ALL_26_107_NATIVE_CASES_PASS'
 except BaseException:result.update(status='INCOMPLETE_FAILURE',error=traceback.format_exc())
 finally:
  suite.main=None;gc.collect();save_trace(out/'events.json.gz',EVENTS);save(out/'CASES.json',suite.records);save(out/'CLASSIFICATIONS.json',suite.manifest);assert source_inputs()==before;result.update(case_count=len(suite.records),family_count=len(set(r['family'] for r in suite.records)),instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],source_unchanged=True,resources=resources());save(out/'RESULT.json',result)
 print(json.dumps(result,indent=2));return 0 if result['status'] in ['DISCOVERY_COMPLETE','ALL_26_107_NATIVE_CASES_PASS'] else 1
if __name__=='__main__':raise SystemExit(main())
