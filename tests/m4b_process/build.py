"""Fresh exact current-source feature artifacts, pinned direct offline compiler."""
from common import *
import subprocess,time

def main(label,feature,helper=False):
 out=OUT/label;out.mkdir(exist_ok=False);before=freeze(out);platform=Path('/home/jerem/.cache/solana/v1.54/platform-tools');manifest=ROOT/('tests/m4b_process/wallet/Cargo.toml' if helper=='wallet' else 'tests/m3/pda_wallet/Cargo.toml' if helper else 'programs/htfp/Cargo.toml')
 env=os.environ.copy()
 for k in list(env):
  if k.startswith(('CARGO_REGISTRIES_','CARGO_REGISTRY_')) or k in ['RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTUP_TOOLCHAIN','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS']:env.pop(k,None)
 env.update(NO_DNA='1',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',CARGO_HOME=str(ROOT/'programs/htfp/.cargo-local'),CARGO_TARGET_DIR=str(ROOT/'target/m4b-author'),RUSTC=str(platform/'rust/bin/rustc'),RUSTDOC=str(platform/'rust/bin/rustdoc'),PATH=str(platform/'rust/bin')+':'+str(platform/'llvm/bin')+':'+env.get('PATH',''))
 command=[str(platform/'rust/bin/cargo'),'build','--offline','--locked','--release','--target','sbpf-solana-solana','--jobs','1','--no-default-features','--manifest-path',str(manifest)]
 if feature!='DEFAULT_DISABLED':command+=['--features',feature]
 obs=[resources()]
 with (out/'build.txt').open('w') as log:
  proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
  while proc.poll() is None:obs.append(resources());time.sleep(.5)
 status=proc.returncode;artifacts={}
 if status==0:
  package='htfp_process_wallet' if helper=='wallet' else 'pda_wallet' if helper else 'htfp';elf=ROOT/'target/m4b-author/sbpf-solana-solana/release'/(package+'.so');raw=elf.read_bytes();(out/'unstripped.so').write_bytes(raw);final=out/(package+'.so');strip=[str(platform/'llvm/bin/llvm-objcopy'),'--strip-all',str(elf),str(final)];r=subprocess.run(strip,capture_output=True,text=True);assert r.returncode==0
  artifacts=dict(artifact_name=final.name,elf_sha256=file_sha(final),elf_bytes=str(final.stat().st_size),unstripped_sha256=sha(raw),strip_command=strip,strip_exit_status='0')
 after=inputs();assert before==after
 record=dict(schema='htfp-m3-owned-build-v2',kind='helper' if helper else 'htfp',feature=feature,command=command,environment={k:env[k] for k in ['NO_DNA','CARGO_NET_OFFLINE','CARGO_INCREMENTAL','CARGO_HOME','CARGO_TARGET_DIR','RUSTC','RUSTDOC','PATH']},inputs_before_sha256=before,inputs_after_sha256=after,source_unchanged=True,compiler_sha256=file_sha(platform/'rust/bin/rustc'),cargo_exit_status=str(status),exit_status=str(status),resource_observations=obs,**artifacts)
 save(out/'build.json',record);print(json.dumps(dict(status=status,path=str(out),artifact=artifacts,resources=resources())));return status
if __name__=='__main__':raise SystemExit(main(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else False))
