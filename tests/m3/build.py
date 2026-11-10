"""Owned offline build/capture. No wrapper/rustup/keypair or global cache writes."""
from pathlib import Path
import os,subprocess,json,hashlib,sys,shutil,time
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(name,features,helper=False):
    out=ROOT/'evidence/m3/author'/name;out.mkdir(exist_ok=False)
    platform=Path('/home/jerem/.cache/solana/v1.54/platform-tools')
    manifest=ROOT/('tests/m3/pda_wallet/Cargo.toml' if helper else 'programs/htfp/Cargo.toml')
    sources=sorted((manifest.parent/'src').glob('*.rs'))
    inputs=sources+[manifest,manifest.with_name('Cargo.lock'),Path(__file__).resolve(),
                   ROOT/'config/m3/local_profile.json']
    if helper:inputs.append(ROOT/'config/m3/helper_public.json')
    before={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    env=os.environ.copy()
    for key in list(env):
        if key.startswith(('CARGO_REGISTRIES_','CARGO_REGISTRY_')) or key in [
            'RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTUP_TOOLCHAIN','CARGO_BUILD_RUSTC_WRAPPER',
            'RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS']:
            env.pop(key,None)
    env.update(NO_DNA='1',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',
      CARGO_HOME=str(ROOT/'programs/htfp/.cargo-local'),
      CARGO_TARGET_DIR=str(ROOT/'programs/htfp/target/m3'),
      RUSTC=str(platform/'rust/bin/rustc'),RUSTDOC=str(platform/'rust/bin/rustdoc'),
      PATH=str(platform/'rust/bin')+':'+str(platform/'llvm/bin')+':'+env.get('PATH',''))
    command=[str(platform/'rust/bin/cargo'),'build','--offline','--locked','--release',
      '--target','sbpf-solana-solana','--jobs','1','--no-default-features',
      '--manifest-path',str(manifest)]
    if features:command+=['--features',features]
    if shutil.disk_usage(ROOT).free<2*1024**3:raise RuntimeError('disk free below2GiB')
    start=time.monotonic()
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/'build.txt').write_text(result.stdout)
    record={'schema':'htfp-m3-owned-build-v2','command':command,
      'environment':{k:env[k] for k in ['CARGO_HOME','CARGO_TARGET_DIR','CARGO_NET_OFFLINE','CARGO_INCREMENTAL','RUSTC','RUSTDOC','PATH']},
      'cargo_exit_status':str(result.returncode),'exit_status':str(result.returncode),
      'duration_seconds':str(time.monotonic()-start),'feature':features or 'DEFAULT_DISABLED',
      'kind':'helper' if helper else 'htfp','inputs_before_sha256':before,
      'compiler_sha256':sha(platform/'rust/bin/rustc'),
      'objcopy_sha256':sha(platform/'llvm/bin/llvm-objcopy')}
    if result.returncode==0:
        name_elf='pda_wallet.so' if helper else 'htfp.so'
        elf=ROOT/'programs/htfp/target/m3/sbpf-solana-solana/release'/name_elf
        data=elf.read_bytes();(out/'unstripped.so').write_bytes(data)
        final=out/name_elf
        strip_command=[str(platform/'llvm/bin/llvm-objcopy'),'--strip-all',str(elf),str(final)]
        stripped=subprocess.run(strip_command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (out/'strip.txt').write_text(stripped.stdout)
        record.update(strip_command=strip_command,strip_exit_status=str(stripped.returncode),unstripped_sha256=hashlib.sha256(data).hexdigest())
        if stripped.returncode:record['exit_status']=str(stripped.returncode)
        else:record.update(elf_sha256=sha(final),elf_bytes=str(final.stat().st_size),artifact_name=name_elf)
    after={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    record.update(inputs_after_sha256=after,source_unchanged=before==after)
    if before!=after:record.update(exit_status='1',failure='build inputs changed during compilation/capture')
    usage=sum(p.stat().st_size for folder in ['programs/htfp/.cargo-local','programs/htfp/target/m3']
              for p in (ROOT/folder).rglob('*') if p.is_file())
    record['mirror_target_bytes']=str(usage)
    if usage>1024**3:record.update(exit_status='1',failure='initial1GiB resource budget exceeded; no cleanup attempted')
    (out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
    print(result.stdout[-18000:]);print('Build evidence:',out,'exit',record['exit_status'])
    return int(record['exit_status'])
if __name__=='__main__':raise SystemExit(build(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'local-m3',len(sys.argv)>3 and sys.argv[3]=='helper'))
