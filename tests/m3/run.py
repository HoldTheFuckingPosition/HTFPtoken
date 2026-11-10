"""Run only in-process captured local/native SBF; new evidence directory per run."""
import argparse,hashlib,importlib.metadata,io,json,os,platform,sys,time,traceback,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',required=True);p.add_argument('--elf',required=True)
    p.add_argument('--default-elf');p.add_argument('--helper-elf');p.add_argument('--pattern',default='test_*.py')
    from native_fixture import SELECTORS
    p.add_argument('--native-fixture',choices=SELECTORS,default='bundled')
    args=p.parse_args();out=(ROOT/args.out).resolve()
    assert any(out.is_relative_to(ROOT/path) and out!=(ROOT/path) for path in ['evidence/m3/author','evidence/m3/supervisor'])
    out.mkdir(exist_ok=False)
    os.environ['M3_RUN_OUT']=str(out)
    os.environ['M3_ELF']=str((ROOT/args.elf).resolve())
    if args.default_elf:os.environ['M3_DEFAULT_ELF']=str((ROOT/args.default_elf).resolve())
    if args.helper_elf:os.environ['M3_HELPER_ELF']=str((ROOT/args.helper_elf).resolve())
    stream=io.StringIO();record={'result':'HARNESS_FAILED','exit_status':1};h=None;native=None;source={};artifact_inputs={}
    try:
        assert sys.dont_write_bytecode and Path.cwd()==ROOT
        import harness as h
        from evidence_policy import success_policy,validate_artifact
        assert platform.node()=='weathertrades' and sys.version_info[:3]==(3,12,3)
        assert importlib.metadata.version('solders')=='0.26.0'
        from solders import __file__ as soldersfile
        package=Path(soldersfile).parent
        assert sha(package/'solders.abi3.so')=='648e13d02ec2e8555d751e38980e01faa5cbb47c2e7d7262f3a2103caa3afa02'
        if __import__('shutil').disk_usage(ROOT).free<2*1024**3:raise RuntimeError('2GiB disk floor')
        from native_fixture import prepare
        native=prepare(args.native_fixture);h.NATIVE_FIXTURE=native
        paths=list((ROOT/'programs/htfp/src').glob('*.rs'))+list((ROOT/'tests/m3').glob('*.py'))
        paths+=[ROOT/'programs/htfp/Cargo.toml',ROOT/'programs/htfp/Cargo.lock',ROOT/'config/m3/local_profile.json',ROOT/'config/m3/helper_public.json']
        helper=ROOT/'tests/m3/pda_wallet/src/lib.rs'
        if helper.exists():paths+=[helper,helper.parent.parent/'Cargo.toml',helper.parent.parent/'Cargo.lock']
        source={str(v.relative_to(ROOT)):sha(v) for v in sorted(paths)}
        source.update(native.inputs)
        artifact_inputs={}
        h.ARTIFACTS={}
        for env_key,kind,feature in [('M3_ELF','htfp','local-m3'),('M3_DEFAULT_ELF','htfp','DEFAULT_DISABLED'),('M3_HELPER_ELF','helper','local-m3')]:
            if env_key not in os.environ:
                raise ValueError('required captured build missing: '+env_key)
            path=Path(os.environ[env_key])
            data,build=validate_artifact(path,kind,feature)
            h.ARTIFACTS[env_key]=data
            artifact_inputs[env_key]={'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),
                'build_record':str(path.with_name('build.json')),'build_record_sha256':sha(path.with_name('build.json'))}
        environment={'host':platform.node(),'python':sys.version,'python_executable':sys.executable,
            'PYTHONDONTWRITEBYTECODE':os.environ.get('PYTHONDONTWRITEBYTECODE'),'PYTHONPATH':os.environ.get('PYTHONPATH'),
            'packages':{n:importlib.metadata.version(n) for n in ['solders','jsonalias','typing_extensions']},
            'native_extension_sha256':sha(package/'solders.abi3.so'),'source_sha256':source,
            'artifacts':{k:{'path':v,'sha256':sha(v),'bytes':Path(v).stat().st_size}
                          for k,v in os.environ.items() if k in ['M3_ELF','M3_DEFAULT_ELF','M3_HELPER_ELF']},
            'native_Token2022_ELF_sha256':native.selected_hash,'bundled_baseline_sha256':h.NATIVE_HASH,
            'selected_native_fixture':native.describe(),'command':sys.argv,
            'public_network':'NONE','synthetic_profile':'config/m3/local_profile.json',
            'baseline':'fae0a3f2c77e2e13694a240706b8353e762e4c3f'}
        (out/'environment.json').write_text(json.dumps(h.exact(environment),indent=2)+'\n')
        # Fail a native load/panic before test discovery; no fallback and no test PASS.
        record['result']='NATIVE_LOAD_FAILED_EXECUTION_NOT_RUN'
        preflight=native.install(h.LiteSVM().with_sigverify(True).with_blockhash_check(True))
        h.EVENTS.append(h.exact({'kind':'native_fixture_preflight',**preflight}))
        record['native_preflight']=preflight
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/m3'),pattern=args.pattern)
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        record.update(result='PASS' if success_policy(result) else 'FAIL',exit_status=0 if success_policy(result) else 1,
            tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
            failure_details=[{'test':str(t),'traceback':e} for t,e in result.failures],
            error_details=[{'test':str(t),'traceback':e} for t,e in result.errors],
            selected_native_fixture=native.describe(),native_inputs_unchanged=native.unchanged(),
            artifact_build_associations=artifact_inputs,
            artifacts_unchanged=all(sha(v['path'])==v['sha256'] and sha(Path(v['build_record']))==v['build_record_sha256'] for v in artifact_inputs.values()),
            source_sha256=source,source_unchanged=all(sha(ROOT/k)==v for k,v in source.items()),
            transaction_count=sum(e['kind']=='transaction' for e in h.EVENTS),coverage_counts=h.COUNTS,
            observed_native_and_custom_failures=sum(e['kind']=='transaction' and e['actual']=='FAILURE' for e in h.EVENTS),
            expected_failures=sum(e['kind']=='transaction' and e['actual']=='FAILURE' and e['expected']!='SUCCESS' for e in h.EVENTS),
            unexpected_failures=sum(e['kind']=='transaction' and e['actual']=='FAILURE' and e['expected']=='SUCCESS' for e in h.EVENTS),
            evidence_level='CAPTURED_CUSTOM_SBF_AND_SELECTED_NATIVE_TOKEN2022_SYSTEM_SYNTHETIC_LOCAL_RUNTIME',
            limits=['No public deployment/source match, real wallets or production genesis',
              'Finite deterministic generated cases; no automatic shrinking',
              'Any explicit state/overflow fault is labelled separately from native monetary-state construction',
              'Independent frozen-candidate review pending; local execution is not founder acceptance'])
        if not record['source_unchanged'] or not record['artifacts_unchanged']:record.update(result='FAIL',exit_status=1)
    except BaseException:
        stream.write(traceback.format_exc());record['exception']=traceback.format_exc()
    finally:
        record['source_sha256']=source
        record['source_unchanged']=all(sha(ROOT/k)==v for k,v in source.items())
        if native:
            record['selected_native_fixture']=native.describe()
            record['native_inputs_unchanged']=native.unchanged()
        if not record['source_unchanged'] or (native and not native.unchanged()):record.update(result='FAIL_INPUT_CHANGED',exit_status=1)
        exact=h.exact if h else lambda x:x
        (out/'unittest.txt').write_text(stream.getvalue())
        if h:(out/'events.json').write_text(json.dumps(exact(h.EVENTS),indent=2)+'\n')
        (out/'report.json').write_text(json.dumps(exact(record),indent=2)+'\n')
        budget_root=ROOT/'evidence/m3/author/native-target'
        usage=sum(v.stat().st_size for v in budget_root.rglob('*') if v.is_file()) if budget_root.exists() else 0
        if usage>128*1024**2:
            record.update(result='FAIL_OUTPUT_BUDGET',exit_status=1)
            (out/'report.json').write_text(json.dumps(exact(record),indent=2)+'\n')
        print(stream.getvalue());print(record['result'],'Evidence:',out)
    return record['exit_status']
if __name__=='__main__':raise SystemExit(main())
