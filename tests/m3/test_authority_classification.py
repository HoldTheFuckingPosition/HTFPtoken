"""Defensive classification regressions against the corrected local artifact only."""
import unittest
from solders.keypair import Keypair
from harness import VM,K,T,R,SYSTEM,EVENTS,count

class NativeAuthorityClassificationTests(unittest.TestCase):
    def fixture(self,label,legacy=False,duplicate_members=False):
        f=VM(label);f.fund(R,10**10)
        account_key=Keypair();a,b,c=Keypair(),Keypair(),Keypair()
        members=[a.pubkey(),a.pubkey(),b.pubkey()] if duplicate_members else [a.pubkey(),b.pubkey(),c.pubkey()]
        multi=f.multisig('classification_multisig',2,members,legacy=legacy,keypair=account_key)
        source=f.create_token('classification_source',owner=multi)
        f.token_transfer(source,10**18)
        payee=Keypair().pubkey();f.track('classification_payee',payee,'state');f.fund(payee,1_000_000)
        return f,account_key,a,b,source,payee

    def reject_before_cpi(self,f,call,signing):
        f.send('reject_authority_classification_before_Burn',[call],signing,error=7005,index=0)
        event=EVENTS[-1]
        self.assertTrue(event['rollback_verified'])
        self.assertFalse(event['htfp_event_hex'])
        self.assertNotIn('Program log: HTFP CPI burn authorized redemption',event['logs'])
        self.assertNotIn('Program log: HTFP CPI native redemption payout',event['logs'])
        self.assertFalse(any(line.startswith(f'Program {T} invoke') for line in event['logs']))
        # send() compares every tracked account byte/balance, excluding actual payer fees.
        self.assertEqual(event['before']['classification_multisig'],event['after']['classification_multisig'])
        self.assertEqual(event['before']['classification_source'],event['after']['classification_source'])
        self.assertEqual(event['before']['classification_payee'],event['after']['classification_payee'])
        count('classification_rejections_before_any_monetary_CPI')

    def test_signed_native_multisig_account_cannot_select_ordinary_owner_mode(self):
        for legacy in [False,True]:
            for duplicate_members in [False,True]:
                with self.subTest(legacy=legacy,duplicate_members=duplicate_members):
                    f,account_key,a,b,source,payee=self.fixture(self.id()+str((legacy,duplicate_members)),legacy,duplicate_members)
                    state=f.snapshot()['classification_multisig']
                    self.assertEqual(state['length'],355)
                    self.assertEqual(state['decoded']['threshold'],2)
                    self.assertEqual(state['decoded']['configured_positions'],3)
                    self.assertEqual(state['decoded']['initialized'],1)
                    # The real artificial account-address signature is present; members are absent.
                    call=f.redeem_ix(10**17,source=source,authority=account_key.pubkey(),payee=payee,
                        kind=0,signers=(),authority_signer=True)
                    self.reject_before_cpi(f,call,[account_key])
                    self.assertEqual(EVENTS[-1]['signature_count'],'2')
                    count('native_initialized_multisig_kind0_signed_negative_profiles')

    def test_malformed_native_multisig_headers_rejected_in_both_modes(self):
        for legacy in [False,True]:
            f,account_key,a,b,source,payee=self.fixture(self.id()+str(legacy),legacy)
            for header in [bytes([0,3,1]),bytes([4,3,1]),bytes([2,12,1]),bytes([2,3,0]),bytes([2,3,2]),bytes([1,0,1])]:
                f.mutate('classification_multisig',lambda d,h=header:d.__setitem__(slice(0,3),h),
                    'Negative malformed native multisig header on genuinely initialized account; no monetary values fabricated')
                for kind in [0,1]:
                    with self.subTest(legacy=legacy,header=header.hex(),kind=kind):
                        members=[] if kind==0 else [a.pubkey(),b.pubkey()]
                        call=f.redeem_ix(10**17,source=source,authority=account_key.pubkey(),payee=payee,
                            kind=kind,signers=members,authority_signer=kind==0)
                        self.reject_before_cpi(f,call,[account_key] if kind==0 else [a,b])
                        count('malformed_native_multisig_header_negative_profiles')

    def test_threshold_mode_refuses_unsupported_owner_or_size(self):
        for malformed in ['runtime_owner','native_size']:
            f,account_key,a,b,source,payee=self.fixture(self.id()+malformed)
            account=f.svm.get_account(account_key.pubkey())
            f.inject_account('classification_multisig',bytes(account.data) if malformed=='runtime_owner' else bytes(account.data)[:-1],
                SYSTEM if malformed=='runtime_owner' else T,account.lamports,
                'Negative unsupported native-multisig runtime-owner/size fixture, derived from genuine native initialized data')
            call=f.redeem_ix(10**17,source=source,authority=account_key.pubkey(),payee=payee,
                kind=1,signers=[a.pubkey(),b.pubkey()])
            self.reject_before_cpi(f,call,[a,b])
            count('unsupported_native_multisig_threshold_negative_profiles')
