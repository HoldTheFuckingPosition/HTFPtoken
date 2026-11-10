"""Bounded NEW StageB outputs, immutable input gates and cumulative accounting."""
from pathlib import Path
import os,sys,json,hashlib,gzip,shutil,importlib.util
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'evidence/m5/locker_author';TEST=ROOT/'tests/m5_locker';FIXTURE='a0695d9d54aaa9c462067e1e3528fde4d4cecc869f329dae865ae21743f1b759'
PROFILE=json.loads((ROOT/'config/m5-locker/profile.json').read_text());ABI=json.loads((ROOT/'config/m5-locker/abi.json').read_text());NATIVE=json.loads((ROOT/'config/m5-locker/native_fixture.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def old_counts():
 rows=[json.loads(p.read_text()) for p in OUT.glob('*/RESULT.json')];return dict(instances=sum(r.get('instances',0) for r in rows),attempts=sum(r.get('attempts',0) for r in rows))
HISTORY=old_counts();COUNTS=dict(instances=0,attempts=0);EVENTS=[]
def resources(extra=0):
 size=lambda d:sum(p.stat().st_blocks*512 for p in d.rglob('*') if p.is_file());own=size(OUT)+size(TEST);m5=size(ROOT/'evidence/m5')+size(ROOT/'config/m5-locker')+size(TEST)+sum(p.stat().st_blocks*512 for p in (ROOT/'evidence').glob('M5_*') if p.is_file());free=os.statvfs(ROOT);free=free.f_bavail*free.f_frsize;cache=sum(size(p) for p in [ROOT/'programs/htfp/.cargo-local',ROOT/'programs/htfp/target',*(ROOT/'target').glob('m4b-*')]);remaining=max(0,20971520-own)
 r=dict(author_including_source_allocated_bytes=own,aggregate_M5_allocated_bytes=m5,free_disk_bytes=free,cache_targets_bytes=cache,cumulative_instances=HISTORY['instances']+COUNTS['instances'],cumulative_native_attempts=HISTORY['attempts']+COUNTS['attempts'])
 assert own+extra<=20971520 and m5+extra+remaining+20971520+4194304<=67108864 and free-extra>=2147483648 and cache<=1073741824,r
 assert r['cumulative_instances']<=100 and r['cumulative_native_attempts']<=5000,r
 return r

def save(p,data):
 p=Path(p);assert not p.exists();b=(json.dumps(data,separators=(',',':'))+'\n').encode();resources(((len(b)+4095)//4096)*4096);p.write_bytes(b)
def save_trace(p,data):
 raw=json.dumps(data,separators=(',',':')).encode();b=gzip.compress(raw,mtime=0);p=Path(p);assert not p.exists();resources(((len(b)+4095)//4096)*4096+4096);p.write_bytes(b);save(p.with_name(p.name+'.FORMAT.json'),dict(encoding='complete UTF8 compact inline JSON, gzip mtime0',decoded_bytes=len(raw),decoded_sha256=sha(raw),stored_bytes=len(b),stored_sha256=sha(b),no_omissions=True))
def source_inputs():
 d={str(p.relative_to(ROOT)):file_sha(p) for p in sorted(TEST.glob('*.py'))};d.update({str(p.relative_to(ROOT)):file_sha(p) for p in (ROOT/'config/m5-locker').glob('*') if p.is_file()});return d

def integrity(selector):
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
 out.mkdir(exist_ok=False);before=source_inputs();save(out/'INPUTS.json',dict(fixture=FIXTURE,source=before,source_bindings_sha256=file_sha(ROOT/'config/m5-locker/source_bindings.json')))
 for p in TEST.glob('*.py'):
  dst=out/'source'/p.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(p,dst)
 return before

def load_source(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
