"""New owned offline direct-platform builds; no wrapper/download/dependency edits."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import pwd
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PLATFORM = Path('/home/jerem/.cache/solana/v1.54/platform-tools')


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sources():
    return {p.relative_to(ROOT).as_posix(): digest(p) for base in ['programs/htfp-both', 'config/processing-both'] for p in sorted((ROOT/base).rglob('*')) if p.is_file()}


def resources():
    v = os.statvfs(ROOT)
    free = v.f_bavail * v.f_frsize
    evidence = sum(p.stat().st_blocks*512 for p in (ROOT/'evidence/processing_both').rglob('*') if p.is_file())
    target = sum(p.stat().st_blocks*512 for role in ['author', 'supervisor'] for p in (ROOT/('target/processing-both-'+role)).rglob('*') if p.is_file())
    assert free >= 2*1024**3 and evidence <= 48*1024**2 and target <= 1024**3, (free,evidence,target)
    return dict(free_bytes=free, new_evidence_allocated_bytes=evidence, new_targets_allocated_bytes=target)


def persist(path, obj):
    with Path(path).open('xb') as f:
        f.write((json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode());f.flush();os.fsync(f.fileno())


def main():
    a=argparse.ArgumentParser();a.add_argument('--role',choices=['author','supervisor'],required=True);a.add_argument('--label',required=True);a.add_argument('--feature',choices=['local-both','local-m3','DEFAULT_DISABLED','local-m3,local-both'],required=True);args=a.parse_args()
    assert platform.node()=='weathertrades' and Path.cwd()==ROOT and pwd.getpwuid(os.getuid()).pw_name=='jerem' and os.getuid()==ROOT.stat().st_uid
    assert args.label.replace('-','').isalnum()
    base=ROOT/'evidence/processing_both'/args.role;base.mkdir(exist_ok=True)
    out=base/args.label;out.mkdir(exist_ok=False)
    before=sources();pins=json.loads((ROOT/'evidence/processing_both/design/BUILD_AND_PRESERVATION.json').read_bytes())
    for p in pins['tools']['observed'].values():assert digest(p['resolved'])==p['sha256']
    command=[str(PLATFORM/'rust/bin/cargo'),'build','--offline','--locked','--release','--target','sbpf-solana-solana','--jobs','1','--no-default-features','--manifest-path',str(ROOT/'programs/htfp-both/Cargo.toml')]
    if args.feature!='DEFAULT_DISABLED':command+=['--features',args.feature]
    env=os.environ.copy()
    for k in list(env):
        if k.startswith(('CARGO_REGISTRIES_','CARGO_REGISTRY_')) or k in ['RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','RUSTUP_TOOLCHAIN','RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS']:env.pop(k,None)
    env.update(NO_DNA='1',CARGO_NET_OFFLINE='true',CARGO_INCREMENTAL='0',CARGO_HOME=str(ROOT/'programs/htfp/.cargo-local'),CARGO_TARGET_DIR=str(ROOT/('target/processing-both-'+args.role)),RUSTC=str(PLATFORM/'rust/bin/rustc'),RUSTDOC=str(PLATFORM/'rust/bin/rustdoc'),PATH=str(PLATFORM/'rust/bin')+':'+str(PLATFORM/'llvm/bin')+':'+env.get('PATH',''))
    ledger=base/'BUILD_LEDGER.jsonl'
    if ledger.exists():
        pending=None
        for line in ledger.read_text().splitlines():
            row=json.loads(line)
            if row['event']=='BUILD_ATTEMPT_STARTED':assert pending is None;pending=row['label']
            elif row['event']=='BUILD_ATTEMPT_COMPLETED':assert pending==row['label'];pending=None
            else:raise AssertionError('unknown build ledger event')
        assert pending is None,'unclosed prior build attempt'
    def event(kind,**extra):
        with ledger.open('ab') as f:f.write((json.dumps(dict(event=kind,label=args.label,feature=args.feature,UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**extra),sort_keys=True,separators=(',',':'))+'\n').encode());f.flush();os.fsync(f.fileno())
    event('BUILD_ATTEMPT_STARTED',command=command,sources=before,resources=resources())
    obs=[resources()]
    proc=None;aborted=None;artifact={}
    try:
        with (out/'build.txt').open('xb') as log:
            proc=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while proc.poll() is None:obs.append(resources());time.sleep(.5)
        status=proc.returncode
        if status==0:
            elf=ROOT/('target/processing-both-'+args.role)/'sbpf-solana-solana/release/htfp_both.so';final=out/'htfp_both.so'
            strip=[str(PLATFORM/'llvm/bin/llvm-objcopy'),'--strip-all',str(elf),str(final)]
            answer=subprocess.run(strip,capture_output=True,text=True,timeout=20)
            assert answer.returncode==0,(answer.returncode,answer.stderr)
            artifact=dict(path=final.relative_to(ROOT).as_posix(),bytes=final.stat().st_size,sha256=digest(final),unstripped_sha256=digest(elf),strip_command=strip,strip_exit_status=answer.returncode)
        after=sources();assert before==after
    except BaseException as error:
        aborted=dict(type=type(error).__name__,message=str(error))
        if proc is not None and proc.poll() is None:
            import signal
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
        status=proc.returncode if proc is not None else None;after=sources()
        persist(out/'ABORTED.json',aborted)
    result=dict(schema='HTFP_BOTH_OWNED_BUILD_V1',role=args.role,feature=args.feature,command=command,environment={k:env[k] for k in ['NO_DNA','CARGO_NET_OFFLINE','CARGO_INCREMENTAL','CARGO_HOME','CARGO_TARGET_DIR','RUSTC','RUSTDOC','PATH']},inputs_before_sha256=before,inputs_after_sha256=after,source_unchanged=before==after,exit_status=status,aborted=aborted,expected_failure=args.feature=='local-m3,local-both',artifact=artifact,resource_observations=obs)
    persist(out/'build.json',result);event('BUILD_ATTEMPT_COMPLETED',exit_status=status,artifact=artifact,aborted=aborted)
    assert aborted is None,aborted
    if args.feature=='local-m3,local-both':assert status!=0 and 'mutually exclusive' in (out/'build.txt').read_text();return 0
    assert status==0,(status,str(out/'build.txt'));print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
