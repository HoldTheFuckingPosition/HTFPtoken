import io,json,os,unittest
from pathlib import Path
from types import SimpleNamespace
from evidence_policy import success_policy,validate_artifact
class EvidencePolicyTests(unittest.TestCase):
    def test_zero_tests_and_skips_cannot_pass(self):
        empty=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestSuite())
        self.assertTrue(empty.wasSuccessful())
        self.assertFalse(success_policy(empty))
        skipped=SimpleNamespace(testsRun=1,skipped=[('dummy','explicit policy control')],wasSuccessful=lambda:True)
        self.assertFalse(success_policy(skipped))
        healthy=SimpleNamespace(testsRun=1,skipped=[],wasSuccessful=lambda:True)
        self.assertTrue(success_policy(healthy))
    def test_wrong_profile_and_stale_or_racing_build_records_rejected(self):
        from harness import ROOT
        local=Path(os.environ['M3_ELF'])
        with self.assertRaisesRegex(ValueError,'wrong artifact profile'):
            validate_artifact(local,'htfp','DEFAULT_DISABLED')
        current=json.loads(local.with_name('build.json').read_text())
        directory=Path(os.environ['M3_RUN_OUT'])/'evidence_policy_controls'
        directory.mkdir(exist_ok=False)
        data=local.read_bytes()
        (directory/local.name).write_bytes(data)
        stale=json.loads(json.dumps(current))
        first=next(iter(stale['inputs_before_sha256']))
        stale['inputs_before_sha256'][first]='0'*64
        stale['inputs_after_sha256'][first]='0'*64
        (directory/'build.json').write_text(json.dumps(stale))
        with self.assertRaisesRegex(ValueError,'stale source'):
            validate_artifact(directory/local.name,'htfp','local-m3')
        race=json.loads(json.dumps(current));race['source_unchanged']=False
        (directory/'build.json').write_text(json.dumps(race))
        with self.assertRaisesRegex(ValueError,'build race'):
            validate_artifact(directory/local.name,'htfp','local-m3')
