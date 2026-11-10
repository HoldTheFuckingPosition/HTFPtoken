"""Stage C owned output/resources and contemporaneous complete source capture."""
from pathlib import Path
import os,json,hashlib,sys,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'evidence/m4b/process_author'
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def save(p,d):
 data=json.dumps(d,separators=(',',':'))+'\n';r=resources();old=Path(p).stat().st_blocks*512 if Path(p).exists() else 0;growth=max(0,((len(data.encode())+4095)//4096)*4096-old)
 assert r['StageC_author_bytes']+growth<=58720256 and r['all_M4B_evidence_bytes']+growth<=268435456,(str(p),r,growth)
 Path(p).write_text(data)
def resources():
 targets=[ROOT/'programs/htfp/target',ROOT/'programs/htfp/.cargo-local']+list((ROOT/'target').glob('m4b-*'))
 used=sum(f.stat().st_blocks*512 for d in targets for f in d.rglob('*') if f.is_file());all_evidence=sum(f.stat().st_blocks*512 for f in (ROOT/'evidence/m4b').rglob('*') if f.is_file());root_records=sum(f.stat().st_blocks*512 for f in (ROOT/'evidence').glob('M4B_*') if f.is_file());all_evidence+=root_records;own=sum(f.stat().st_blocks*512 for f in OUT.rglob('*') if f.is_file());s=os.statvfs(ROOT);free=s.f_bavail*s.f_frsize
 r=dict(cache_targets_bytes=used,all_M4B_evidence_bytes=all_evidence,StageC_author_bytes=own,free_disk_bytes=free,root_M4B_records_bytes=root_records)
 assert used<=1073741824 and all_evidence<=268435456 and own<=58720256 and free>=2147483648,r
 return r
def inputs():
 p=list((ROOT/'programs/htfp/src').glob('*.rs'))+[ROOT/'programs/htfp/Cargo.toml',ROOT/'programs/htfp/Cargo.lock']+list((ROOT/'tests/m4b_process').rglob('*.py'))+list((ROOT/'tests/m4b_process').rglob('*.rs'))+list((ROOT/'tests/m4b_process').rglob('Cargo.*'))+list((ROOT/'tests/m4b_process').glob('*.json'))
 for d in ['config/m3','config/m4b']:p+=list((ROOT/d).glob('*.json'))
 p+=list((ROOT/'tests/m3/pda_wallet').glob('Cargo.*'))+list((ROOT/'tests/m3/pda_wallet/src').rglob('*.rs'))
 p+=list((ROOT/'tests/m3').glob('*.py'))+[ROOT/'tests/m4b'/n for n in ['common.py','runtime.py','amm.py','native_mint_fixture.py','quote_oracle.py']]+[ROOT/'evidence/m4b/supervisor/volume_oracle.py']
 return {str(f.relative_to(ROOT)):file_sha(f) for f in sorted(set(p)) if f.is_file()}
def freeze(out):
 before=inputs();save(out/'INPUTS.json',before)
 for p in before:
  if p.startswith(('programs/htfp/','tests/m4b_process/')):
   dest=out/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
 return before

def save_events(path,events):
 """Lossless NEW-trace encoding: deduplicate only account data bytes by SHA256.
 Owners, lamports, addresses and all transaction metadata remain inline. No prior
 evidence is rewritten. Resolve data_ref through the named DATA_BLOBS.json and
 verify sha256(bytes.fromhex(hex)) == data_ref before interpreting raw fields.
 """
 path=Path(path);blobs={};encoded=[]
 for original in events:
  row=dict(original)
  if row.get('kind')=='transaction':
   row['account_data_blob_file']=str((path.parent/'DATA_BLOBS.json').relative_to(ROOT))
   for side in ['before','after']:
    result={}
    for role,account in row[side].items():
     if account is None:result[role]=None;continue
     account=dict(account);hx=account.pop('data_hex');ref=sha(bytes.fromhex(hx));assert account.get('data_sha256',ref)==ref
     blobs[ref]=hx;account['data_ref']=ref;result[role]=account
    row[side]=result
  encoded.append(row)
 save(path.parent/'DATA_BLOBS.json',blobs);save(path,encoded)

def resolve_events(path):
 path=Path(path);rows=json.loads(path.read_text());blobs=json.loads((path.parent/'DATA_BLOBS.json').read_text())
 for row in rows:
  if row.get('kind')!='transaction':continue
  for side in ['before','after']:
   for account in row[side].values():
    if account is not None:
     ref=account.pop('data_ref');hx=blobs[ref];assert sha(bytes.fromhex(hx))==ref;account['data_hex']=hx
 return rows

def save_gzip_events(path,events):
 """NEW evidence only, lossless inline raw JSON with deterministic gzip framing."""
 import gzip
 path=Path(path);content=json.dumps(events,separators=(',',':')).encode();encoded=gzip.compress(content,mtime=0);r=resources();need=((len(encoded)+4095)//4096)*4096
 assert r['StageC_author_bytes']+need+4096<=58720256 and r['all_M4B_evidence_bytes']+need+4096<=268435456,(path,r,need)
 path.write_bytes(encoded)
 save(path.with_name(path.name+'.FORMAT.json'),dict(schema='htfp-new-evidence-lossless-gzip-json-v1',file=str(path.relative_to(ROOT)),encoding='UTF8 JSON compact, gzip mtime0, full inline raw account data and metadata',compressed_bytes=len(encoded),compressed_sha256=sha(encoded),decoded_UTF8_bytes=len(content),decoded_UTF8_sha256=sha(content),prior_evidence_recompressed=False))
