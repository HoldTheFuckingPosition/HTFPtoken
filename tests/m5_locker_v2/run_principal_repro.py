"""Minimal monetary replay of the retained two-LP adjusted diagnostic failure.
For root's separate execution only, HTFP_M5_LOCKER_ROLE=supervisor redirects NEW
outputs to its dedicated runtime_v2 role. No native run is performed
by importing this module. Default remains the bounded author namespace.
"""
import argparse,traceback,gc
from case_suite import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--fixture',required=True);p.add_argument('--label',required=True);a=p.parse_args();integrity(a.fixture);out=OUT/a.label;before=freeze(out);result=dict(status='INCOMPLETE',command=sys.argv,role=ROLE,fixture=FIXTURE,author_native_execution='NOT_RUN_FOR_THIS_NEW_MINIMAL_ENTRYPOINT',chronology='Exact monetary branch of remaining-focus-001: no prior successful claim, eight base swaps, genuine B deposit/secondary lock, four later swaps, primary MAX claim. Six fully reverted CU cuts and relock rejection omitted. Clock remains frozen E9/time1700000001 exactly as retained native trial; later +60/+32 progression NOT implemented in that trial.');v=None
 try:
  v=fresh('minimal_principal_repro',True,True);v.deposit_B();v.secondary_lock();v.accrue(later=True);row=v.claim();result.update(status='UNEXPECTED_DIAGNOSTIC_PASS',diagnostic=row['principal_diagnostic'])
 except BaseException:
  candidates=[r for r in EVENTS if r.get('kind')=='transaction' and r.get('principal_diagnostic')];diagnostic=candidates[-1]['principal_diagnostic'] if candidates else None;result.update(status='ADJUSTED_PRINCIPAL_DIAGNOSTIC_FAILED' if diagnostic and not diagnostic['holds'] else 'INSTRUMENTATION_OR_NATIVE_FAILURE',error=traceback.format_exc(),diagnostic=diagnostic)
 finally:
  if v is not None:del v;gc.collect()
  save_trace(out/'events.json.gz',EVENTS);assert source_inputs()==before;result.update(instances=COUNTS['instances'],attempts=COUNTS['attempts'],cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_attempts=HISTORY['attempts']+COUNTS['attempts'],source_unchanged=True,resources=resources());save(out/'RESULT.json',result)
 print(json.dumps(result,indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
