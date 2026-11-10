"""Bounded NEW StageB outputs, immutable input gates and cumulative accounting."""
from pathlib import Path
import os,sys,json,hashlib,gzip,shutil,importlib.util
ROOT=Path(__file__).resolve().parents[2];AUTHOROUT=ROOT/'evidence/m5/locker_author_v2';SUPERVISOROUT=ROOT/'evidence/m5/locker_supervisor/runtime_v2';ROLE=os.environ.get('HTFP_M5_LOCKER_ROLE','author');assert ROLE in ['author','supervisor'];OUT=AUTHOROUT if ROLE=='author' else SUPERVISOROUT;TEST=ROOT/'tests/m5_locker_v2';OLDOUT=ROOT/'evidence/m5/locker_author';OLDTEST=ROOT/'tests/m5_locker';FIXTURE='a0695d9d54aaa9c462067e1e3528fde4d4cecc869f329dae865ae21743f1b759'
PROFILE=json.loads((ROOT/'config/m5-locker/profile.json').read_text());ABI=json.loads((ROOT/'config/m5-locker/abi.json').read_text());NATIVE=json.loads((ROOT/'config/m5-locker/native_fixture.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
OVERLAY={
 'evidence/M5_LOCKER_EXECUTION_BUDGET_SUPPLEMENT.json':'1262dcaeb70aa43ed495f68122b430eac069787cb14d00ff24ec8f45e12172fd',
 'evidence/M5_LOCKER_EXECUTION_BUDGET_REVIEW.json':'3e96d41a3d641213830a18533a5aa98bf460b1a8bd9bad1102b41f8ca6a25360',
 'evidence/M5_LOCKER_EXECUTION_BUDGET_INDEPENDENT_REVIEW.txt':'bab50d119e41789ba21b4e356770af6e2ddb6906da47a5edff55d4352502f70f',
 'evidence/M5_LOCKER_EXECUTION_BUDGET_ACTIVATION.json':'dd0c1e5c1a18b1ce661d9f403e47ba772fde007895dac2d78f9540ccbb09dfec'}
RUN_LOCK=None

def old_counts():
 totals=dict(instances=0,attempts=0,author_instances=0,author_attempts=0,supervisor_instances=0,supervisor_attempts=0);seen=set()
 for role,folder in [('author',OLDOUT),('author',AUTHOROUT),('supervisor',SUPERVISOROUT)]:
  orphans=[str(p) for p in folder.glob('*') if p.is_dir() and not (p/'RESULT.json').exists()];assert not orphans,('Unreconciled prior run',orphans)
  for p in folder.glob('*/RESULT.json'):
   assert p.resolve() not in seen;seen.add(p.resolve());r=json.loads(p.read_text());assert 'instances' in r and 'attempts' in r
   for key in ['instances','attempts']:totals[key]+=r[key];totals[role+'_'+key]+=r[key]
 old=[json.loads(p.read_text()) for p in OLDOUT.glob('*/RESULT.json')];assert sum(r['instances'] for r in old)==2 and sum(r['attempts'] for r in old)==38
 return totals
HISTORY=old_counts();COUNTS=dict(instances=0,attempts=0);EVENTS=[]
def resources(extra=0,instances=0,attempts=0):
 size=lambda d:sum(p.stat().st_blocks*512 for p in d.rglob('*') if p.is_file());own=size(OLDOUT)+size(OLDTEST)+size(AUTHOROUT)+size(TEST);supervisor_runtime=sum(size(p) for p in (ROOT/'evidence/m5/locker_supervisor').glob('runtime*') if p.is_dir());m5=size(ROOT/'evidence/m5')+size(ROOT/'config/m5-locker')+size(TEST)+size(OLDTEST)+sum(p.stat().st_blocks*512 for p in (ROOT/'evidence').glob('M5_*') if p.is_file());free=os.statvfs(ROOT);free=free.f_bavail*free.f_frsize;cache=sum(size(p) for p in [ROOT/'programs/htfp/.cargo-local',ROOT/'programs/htfp/target',*(ROOT/'target').glob('m4b-*')]);remaining=max(0,20971520-own)
 r=dict(author_including_source_allocated_bytes=own,aggregate_M5_allocated_bytes=m5,free_disk_bytes=free,cache_targets_bytes=cache,supervisor_runtime_allocated_bytes=supervisor_runtime,author_role=ROLE,run_instances=COUNTS['instances'],role_instances=HISTORY[ROLE+'_instances']+COUNTS['instances'],shared_role_history=HISTORY.copy(),cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_native_attempts=HISTORY['attempts']+COUNTS['attempts'])
 assert own+extra<=20971520 and supervisor_runtime+extra<=20971520 and m5+extra+remaining+max(0,20971520-supervisor_runtime)+4194304<=67108864 and free-extra>=2147483648 and cache<=1073741824,r
 assert r['cumulative_instances']+instances<=160 and r['role_instances']+instances<=(100 if ROLE=='author' else 60) and COUNTS['instances']+instances<=100 and r['cumulative_native_attempts']+attempts<=5000,r
 return r

def save(p,data):
 p=Path(p);assert not p.exists();b=(json.dumps(data,separators=(',',':'))+'\n').encode();resources(((len(b)+4095)//4096)*4096);p.write_bytes(b)
def save_trace(p,data):
 raw=json.dumps(data,separators=(',',':')).encode();b=gzip.compress(raw,mtime=0);p=Path(p);assert not p.exists();resources(((len(b)+4095)//4096)*4096+4096);p.write_bytes(b);save(p.with_name(p.name+'.FORMAT.json'),dict(encoding='complete UTF8 compact inline JSON, gzip mtime0',decoded_bytes=len(raw),decoded_sha256=sha(raw),stored_bytes=len(b),stored_sha256=sha(b),no_omissions=True))
def source_inputs():
 d={str(p.relative_to(ROOT)):file_sha(p) for p in sorted(TEST.glob('*.py'))};d.update({str(p.relative_to(ROOT)):file_sha(p) for p in (ROOT/'config/m5-locker').glob('*') if p.is_file()});d.update(OVERLAY);return d

def integrity(selector):
 for n,h in OVERLAY.items():assert file_sha(ROOT/n)==h,n
 assert selector==FIXTURE,'Exact explicit --fixture selector required; default refuses all execution'
 assert Path.cwd()==ROOT and sys.dont_write_bytecode
 import platform,importlib.metadata
 assert platform.node()=='weathertrades' and sys.version_info[:3]==(3,12,3)
 assert importlib.metadata.version('solders')=='0.26.0'
 hand=ROOT/'evidence/m5/locker_design/HANDOFF.json';assert file_sha(hand)=='e6d782e220503be694e3b299960a87b6bbfc5713f3d1cfef70ddf842976f5268'
 h=json.loads(hand.read_text());assert len(h['payload_files'])==138
 for n,r in h['payload_files'].items():assert file_sha(ROOT/n)==r['sha256'] and (ROOT/n).stat().st_size==r['bytes'],n
 b=json.loads((ROOT/'config/m5-locker/binding.json').read_text());assert b['fixture_sha256']==FIXTURE and file_sha(ROOT/b['preimage_path'])==FIXTURE
 for c in b['components']:assert file_sha(ROOT/c['path'])==c['sha256']
 bindings=json.loads((ROOT/'config/m5-locker/source_bindings.json').read_text());assert len(bindings['files'])==176
 for n,r in bindings['files'].items():assert file_sha(Path(n) if Path(n).is_absolute() else ROOT/n)==r['sha256'],n
 return resources()
def freeze(out):
 global RUN_LOCK
 import fcntl
 assert RUN_LOCK is None;RUN_LOCK=os.open(ROOT/'evidence/M5_LOCKER_EXECUTION_BUDGET_ACTIVATION.json',os.O_RDONLY);fcntl.flock(RUN_LOCK,fcntl.LOCK_EX|fcntl.LOCK_NB);reconciled=old_counts();HISTORY.clear();HISTORY.update(reconciled)
 assert out.parent==OUT;OUT.mkdir(exist_ok=True);out.mkdir(exist_ok=False);before=source_inputs();save(out/'INPUTS.json',dict(fixture=FIXTURE,role=ROLE,output_directory=str(out),cumulative_history=HISTORY.copy(),execution_overlay=OVERLAY,source=before,source_bindings_sha256=file_sha(ROOT/'config/m5-locker/source_bindings.json')))
 for p in TEST.glob('*.py'):
  dst=out/'source'/p.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(p,dst)
 return before

def load_source(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
