"""Freeze exact owned sources, run required families sequentially, preserve every trial."""
from pathlib import Path
import os,sys,json,subprocess,shutil,time
from common import ROOT,OUT,save,file_sha,resources
FAMILIES=[('dependency','common.py','RESULT.json'),('isolated','test_isolated.py','RESULT.json'),('extended','test_extended.py','RESULT.json'),('amm','test_amm.py','RESULT.json'),('native-controls','native_controls.py','RESULT.json'),('volume-model','volume_model.py','RESULT.json'),('regression','regression_driver.py','report.json')]
def source_inputs():
 files=[]
 for directory in [ROOT/'tests/m4b',ROOT/'programs/m4b-proof']:
  files.extend(p for p in directory.rglob('*') if p.is_file() and p.suffix in ['.py','.rs','.toml','.lock','.md'])
 frozen=json.loads((ROOT/'evidence/m4b/design/HANDOFF.json').read_text())['files_sha256']
 files.extend(ROOT/p for p in frozen)
 files.extend(ROOT/p for p in ['evidence/m4b/design/HANDOFF.json','evidence/M4B_STAGE_B_HANDOFF.md','evidence/M4B_WSOL_MINT_FIXTURE_SUPPLEMENT.json','evidence/M4B_WSOL_MINT_SUPPLEMENT_HANDOFF.md','evidence/M4B_WSOL_MINT_SUPPLEMENT_REVIEW.json','evidence/m4b/supervisor/volume_oracle.py','evidence/m4b/supervisor/VOLUME_ORACLE_MODEL.json','evidence/m4b/author/build-003/BUILD.json'])
 return {str(p.relative_to(ROOT)):file_sha(p) for p in sorted(set(files))}
def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);before=source_inputs();save(out/'INPUTS.json',before);snapshot=out/'source'
 for p in before:
  if p.startswith(('tests/m4b/','programs/m4b-proof/')):
   dest=snapshot/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
 outcomes=[];observations=[resources()]
 for family,script,result_name in FAMILIES:
  command=[sys.executable,str(ROOT/'tests/m4b'/script),label+'/'+family]
  start=time.monotonic()
  with (out/(family+'.stdout.txt')).open('w') as log:result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy())
  path=out/family/result_name;row=json.loads(path.read_text()) if path.exists() else None
  outcomes.append(dict(family=family,command=command,exit_status=result.returncode,result_path=str(path.relative_to(ROOT)),result_sha256=file_sha(path) if path.exists() else None,status=row.get('status',row.get('result')) if row else 'NO_REPORT',elapsed_seconds=time.monotonic()-start))
  observations.append(resources());print(json.dumps(outcomes[-1]),flush=True)
  # Preserve all families even when a previous one fails; independent obligations still run.
 after=source_inputs();assert before==after,'Source/config/build input changed during final execution'
 status='PASS_BOUNDED_STAGE_B_AUTHOR_ONLY' if all(x['exit_status']==0 for x in outcomes) else 'FAIL'
 result=dict(schema='htfp-m4b-stage-b-frozen-family-run-v1',status=status,inputs_before_sha256=before,inputs_after_sha256=after,inputs_unchanged=before==after,families=outcomes,resource_observations=observations,limitations=['Author results only; supervisor reproduction/exact independent StageB review remain pending','No H Process/Volume/Finalize implementation or native H sale integration','Mixed native fixture with explicit reviewed zero-supply native mint supplement; no public runtime/source match','All failures/precursor trials remain immutable'])
 save(out/'RESULT.json',result);print(json.dumps(dict(status=status,resources=resources())));return 0 if status.startswith('PASS') else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
