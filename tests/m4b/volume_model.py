"""MODEL ONLY: independent integer storage candidate versus supervisor Fraction oracle."""
import importlib.util,sys,json,random,collections
from common import ROOT,OUT,PROFILE,file_sha,save
U=(1<<64)-1;LO=-(1<<63);HI=(1<<63)-1
ORACLE=ROOT/'evidence/m4b/supervisor/volume_oracle.py'
def integer_decide(credit,last,sequence,now,q,R,vault,protocol,fund,creator,complete):
 before=(credit,last,sequence,R);t=max(now,last);available=min(30000000000,credit+(t-last)*5000000)
 if not 0<q<=U or q%8 or q>R:return False,before
 x=vault-protocol-fund-creator
 if x<=0 or protocol+fund+creator>U or sequence==U:return False,before
 f=(q//8)*5
 if f>x//1000 or f*3>available or not complete:return False,before
 return True,(available-f*3,t,sequence+1,R-q)
def main(label):
 out=OUT/label;out.mkdir(exist_ok=False);before=file_sha(ORACLE);spec=importlib.util.spec_from_file_location('independent_m4b_fraction_oracle',ORACLE);oracle=importlib.util.module_from_spec(spec);sys.modules[spec.name]=oracle;spec.loader.exec_module(oracle);params=oracle.Parameters.from_profile(PROFILE)
 rng=random.Random(0x4d3442564f4c);counts=collections.Counter();samples=[];cases=[]
 # Explicit exact-limit, one-over, full-at-anchor, negative/backward time and u64/i64 boundaries.
 for credit in [0,1,2,3,30000000000]:
  for now in [LO,1699999999,1700000000,1700000001,1700000060,HI]:
   for q in [0,1,7,8,16000000000,16000000008,U]:cases.append((credit,1700000000,0,now,q,U,10**13,0,0,0,True))
 for vault,protocol,fund,creator in [(0,0,0,0),(5,5,0,0),(5,6,0,0),(U,U,1,0),(4999,0,0,0),(5000,0,0,0),(5001,0,0,0)]:
  cases.append((30000000000,1700000000,0,1700000000,8,U,vault,protocol,fund,creator,True))
 for i in range(4096):
  k=rng.randint(1,2000000000);q=8*k;f=5*k;credit=rng.choice([0,1,2,30000000000,rng.randint(0,30000000000)]);last=rng.choice([LO,0,1700000000,HI]);now=max(LO,min(HI,last+rng.choice([-60,-1,0,1,60,10**9])))
  protocol=rng.randint(0,1000);fund=rng.randint(0,1000);creator=rng.randint(0,1000);x=f*1000+rng.choice([-1,0,1,999,1000]);vault=x+protocol+fund+creator
  if i%17==0:q=rng.choice([0,1,7,U])
  R=rng.choice([q if q<=U else U,U,max(0,q-1)]);sequence=U if i%19==0 else rng.randint(0,1000)
  cases.append((credit,last,sequence,now,q,R,vault,protocol,fund,creator,bool(i%5)))
 for i,c in enumerate(cases):
  credit,last,sequence,now,q,R,vault,protocol,fund,creator,complete=c;state=oracle.VolumeState.from_scaled(credit,last,sequence,params);request=oracle.Request(now,q,R,vault,protocol,fund,creator);ref=oracle.decide(params,state,request,complete=complete)
  committed,after=integer_decide(*c);expected=(ref.after.scaled(params),ref.after.last_refill,ref.after.sequence,ref.recovered_after)
  assert committed==ref.committed and after==expected,(i,c,ref,after)
  assert 0<=after[0]<=30000000000
  if not committed:assert after==(credit,last,sequence,R)
  else:assert after[2]==sequence+1 and after[3]==R-q and after[0]%1==0
  counts[ref.reason]+=1
  if len(samples)<20 or ref.committed and len(samples)<40:samples.append(dict(input=c,committed=committed,after=after,oracle_reason=ref.reason))
 assert file_sha(ORACLE)==before
 row=dict(status='MODEL_ORACLE_AGREEMENT_ONLY',cases=len(cases),seed='0x4d3442564f4c',outcomes=dict(counts),independent_fraction_oracle_path=str(ORACLE.relative_to(ROOT)),independent_fraction_oracle_sha256=before,author_integer_model_sha256=file_sha(__file__),samples=samples,limitations=['No H/native volume code exists; no runtime/account/price/fee/F17 proof from these models','Finite deterministic generated cases, no PBT dependency, no automatic shrinking/exhaustiveness claim'])
 save(out/'RESULT.json',row);print(json.dumps({k:row[k] for k in ['status','cases','outcomes']}))
if __name__=='__main__':main(sys.argv[1])
