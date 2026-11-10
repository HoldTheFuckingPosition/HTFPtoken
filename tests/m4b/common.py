"""Fixed local-only Stage B inputs, native loading, resource/preservation audit."""
from pathlib import Path
import hashlib,json,os,platform,sys
from solders.pubkey import Pubkey
from solders.litesvm import LiteSVM
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evidence/m4b/author'
PROFILE=json.loads((ROOT/'config/m4b/local_profile.json').read_text())
NATIVE=json.loads((ROOT/'config/m4b/native_fixture.json').read_text())
K={n:Pubkey.from_string(v['base58']) for n,v in PROFILE['identities'].items()}
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def save(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
def resources():
 allocated=0;locations=['programs/htfp/.cargo-local','programs/htfp/target']
 locations += [str(p.relative_to(ROOT)) for p in (ROOT/'target').glob('m4b-*')]
 for loc in locations:
  for directory,_,files in os.walk(ROOT/loc):
   for filename in files:
    p=Path(directory)/filename
    if p.is_file():allocated+=p.stat().st_blocks*512
 evidence=sum(p.stat().st_blocks*512 for p in (ROOT/'evidence/m4b').rglob('*') if p.is_file())
 stat=os.statvfs(ROOT);free=stat.f_bavail*stat.f_frsize
 row=dict(cache_targets_allocated_bytes=allocated,m4b_evidence_allocated_bytes=evidence,free_disk_bytes=free,counted_locations=locations)
 assert allocated<=1073741824,row
 assert evidence<=268435456,row
 assert free>=2147483648,row
 return row
class MixedFixture:
 selector=NATIVE['id'];selected_hash=NATIVE['captures'][1]['full_sha256']
 def __init__(self):
  self.codes={};self.inputs={}
  for cap in NATIVE['captures']:
   data=(ROOT/cap['path']).read_bytes();assert len(data)==cap['full_bytes'] and sha(data)==cap['full_sha256']
   self.codes[cap['role']]=data;self.inputs[cap['path']]=cap['full_sha256']
  for name in ['local_profile','native_fixture','processing_binding','native_abi','proof_abi','abi']:
   p='config/m4b/'+name+'.json';self.inputs[p]=file_sha(ROOT/p)
 def unchanged(self):return all(file_sha(ROOT/p)==d for p,d in self.inputs.items())
 def describe(self):return dict(selector=self.selector,mode=NATIVE['mode'],source_public_runtime_match='UNKNOWN',inputs=self.inputs)
 def install(self,svm):
  def view(role,expected=None):
   a=svm.get_account(K[role]);assert a is not None and a.executable,(role,a)
   d=bytes(a.data)
   if expected is not None:assert d==expected,(role,len(d),sha(d),sha(expected))
   return dict(program=str(K[role]),owner=str(a.owner),bytes=len(d),sha256=sha(d),executable=a.executable)
  before=view('associated_token');assert before['sha256']==NATIVE['bundled_ATA']['ELF_sha256'] and before['bytes']==105032
  container=Path(NATIVE['bundled_ATA']['container']).read_bytes();assert sha(container)==NATIVE['bundled_ATA']['container_sha256']
  b=NATIVE['bundled_ATA'];assert bytes(svm.get_account(K['associated_token']).data)==container[b['slice_offset']:b['slice_offset']+b['slice_bytes']]
  rows={}
  for role,key in [('legacyToken','legacy_token'),('Token2022','token2022'),('CPMM','amm')]:
   svm.add_program(K[key],self.codes[role]);rows[role]=view(key,self.codes[role])
  after=view('associated_token');assert before==after
  assert self.unchanged()
  return dict(ATA_before=before,loaded=rows,ATA_after=after,mode=NATIVE['mode'],code_transform='NONE',public_runtime_equivalence='NOT_CLAIMED')
def preflight(out):
 assert platform.node()=='weathertrades' and Path.cwd()==ROOT and sys.dont_write_bytecode
 assert sys.version_info[:3]==(3,12,3)
 import importlib.metadata
 for package,v in [('solders','0.26.0'),('jsonalias','0.1.1'),('typing_extensions','4.16.0')]:assert importlib.metadata.version(package)==v
 handoff=json.loads((ROOT/'evidence/m4b/design/HANDOFF.json').read_text())
 for p,d in handoff['files_sha256'].items():assert file_sha(ROOT/p)==d,p
 f=MixedFixture();svm=LiteSVM().with_sigverify(True).with_blockhash_check(True)
 row={'status':'EXACT_DEPENDENCY_LOAD_PASS_ONLY','native_load':f.install(svm),'resources':resources(),'source_sha256':{str(Path(__file__).relative_to(ROOT)):file_sha(__file__)},'runtime':NATIVE['runtime'],'limitations':['No transaction/executable ABI/CPMM initialization/close behavior proved by load alone','Three captures plus bundled ATA mixed provenance','Synthetic LiteSVM native loader, no public validator/features equivalence']}
 save(out/'RESULT.json',row);return row
if __name__=='__main__':
 out=OUT/(sys.argv[1] if len(sys.argv)>1 else 'dependency-001');out.mkdir(exist_ok=False);print(json.dumps(preflight(out)))
