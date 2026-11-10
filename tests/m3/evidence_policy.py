"""Build/run evidence integrity independent from the protocol implementation."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[2]
def sha(data):return hashlib.sha256(data).hexdigest()
def success_policy(result):
    return result.testsRun>0 and len(result.skipped)==0 and result.wasSuccessful()
def validate_artifact(path,kind,feature):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'evidence/m3'):raise ValueError('artifact outside repository evidence')
    record=json.loads(path.with_name('build.json').read_text())
    if record.get('schema')!='htfp-m3-owned-build-v2':raise ValueError('missing validated build association')
    if record.get('kind')!=kind or record.get('feature')!=feature:raise ValueError('wrong artifact profile/kind')
    if record.get('exit_status')!='0' or record.get('cargo_exit_status')!='0' or record.get('strip_exit_status')!='0':
        raise ValueError('unsuccessful build/strip')
    if not record.get('source_unchanged') or record.get('inputs_before_sha256')!=record.get('inputs_after_sha256'):
        raise ValueError('build race/input mismatch')
    for relative,expected in record['inputs_before_sha256'].items():
        p=(ROOT/relative).resolve()
        if not p.is_relative_to(ROOT):raise ValueError('invalid build input path')
        if sha(p.read_bytes())!=expected:raise ValueError('stale source/build input: '+relative)
    data=path.read_bytes()
    if record.get('artifact_name')!=path.name or sha(data)!=record['elf_sha256']:
        raise ValueError('artifact does not match successful build')
    return data,record
