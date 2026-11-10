"""Serialize exact pinned offline builds; capture each immutable trial/source/ELF."""
from pathlib import Path
import os,subprocess,json,time,shutil,sys,tomllib
from common import ROOT,OUT,resources,file_sha,save

def main(label):
 out=OUT/label;out.mkdir(exist_ok=False)
 workspace=ROOT/'programs/m4b-proof';platform=Path('/home/jerem/.cache/solana/v1.54/platform-tools')
 sources=sorted(workspace.rglob('*.rs'))+sorted(workspace.rglob('Cargo.toml'))+[workspace/'Cargo.lock',Path(__file__).resolve()]
 before={str(p.relative_to(ROOT)):file_sha(p) for p in sources}
 snap=out/'source';snap.mkdir()
 for p in sources:
  dest=snap/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 old=tomllib.loads((ROOT/'programs/htfp/Cargo.lock').read_text());new=tomllib.loads((workspace/'Cargo.lock').read_text())
 assert [x for x in old['package'] if 'source'in x]==[x for x in new['package'] if 'source'in x]
 env=os.environ.copy()
 for k in list(env):
  if k.startswith(('CARGO_REGISTRIES_','CARGO_REGISTRY_')) or k in ['RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTUP_TOOLCHAIN','CARGO_BUILD_RUSTC_WRAPPER','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS']:env.pop(k,None)
 env.update(NO_DNA='1',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',CARGO_HOME=str(ROOT/'programs/htfp/.cargo-local'),CARGO_TARGET_DIR=str(ROOT/'target/m4b-author'),RUSTC=str(platform/'rust/bin/rustc'),RUSTDOC=str(platform/'rust/bin/rustdoc'),PATH=str(platform/'rust/bin')+':'+str(platform/'llvm/bin')+':'+env.get('PATH',''))
 command=[str(platform/'rust/bin/cargo'),'build','--offline','--locked','--release','--target','sbpf-solana-solana','--jobs','1','--manifest-path',str(workspace/'Cargo.toml')]
 observations=[resources()];start=time.monotonic()
 with (out/'build.txt').open('w') as log:
  proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
  while proc.poll() is None:
   try:observations.append(resources())
   except BaseException:proc.terminate();proc.wait();raise
   time.sleep(1)
 status=proc.returncode;artifacts={}
 if status==0:
  for package in ['m4b_proof_kernel','m4b_restricted_wallet']:
   src=ROOT/'target/m4b-author/sbpf-solana-solana/release'/f'{package}.so';unstripped=out/(package+'.unstripped.so');shutil.copyfile(src,unstripped)
   final=out/(package+'.so');strip=[str(platform/'llvm/bin/llvm-objcopy'),'--strip-all',str(src),str(final)]
   result=subprocess.run(strip,capture_output=True,text=True);assert result.returncode==0,result.stderr
   artifacts[package]={'path':str(final.relative_to(ROOT)),'sha256':file_sha(final),'bytes':final.stat().st_size,'unstripped_sha256':file_sha(unstripped),'strip_command':strip,'strip_status':result.returncode}
 after={str(p.relative_to(ROOT)):file_sha(p) for p in sources};assert before==after
 record=dict(status='BUILD_PASS' if status==0 else 'BUILD_FAIL',exit_status=status,command=command,environment={k:env[k] for k in ['NO_DNA','CARGO_NET_OFFLINE','CARGO_INCREMENTAL','CARGO_HOME','CARGO_TARGET_DIR','RUSTC','RUSTDOC','PATH']},inputs_before_sha256=before,inputs_after_sha256=after,source_unchanged=before==after,compiler_sha256=file_sha(platform/'rust/bin/rustc'),artifacts=artifacts,resource_observations=observations,elapsed_seconds=time.monotonic()-start)
 save(out/'BUILD.json',record);print(json.dumps({'status':record['status'],'exit_status':status,'artifacts':artifacts,'resources':resources()}));return status
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
