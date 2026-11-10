"""Independent conservation, rollback, alias and native verification controls."""
import random,struct,unittest
from solders.compute_budget import set_compute_unit_limit
from solders.keypair import Keypair
from solders.signature import Signature
from solders.transaction import Transaction
from solders.system_program import transfer
from harness import VM,K,H,T,R,SUPPLY,EVENTS,am,ix,count,exact

class RuntimeBoundaryTests(unittest.TestCase):
    def test_native_signature_verification_is_actually_enabled(self):
        f=VM(self.id());payee=Keypair().pubkey();f.track('unsigned_payee',payee,'state')
        before=f.snapshot()
        tx=Transaction.new_signed_with_payer([transfer({'from_pubkey':f.initializer.pubkey(),
            'to_pubkey':payee,'lamports':1_000_000})],f.initializer.pubkey(),[f.initializer],f.svm.latest_blockhash())
        invalid=Transaction.populate(tx.message,[Signature.default()])
        result=f.svm.send_transaction(invalid)
        self.assertIn('SignatureFailure',str(result.err()))
        self.assertEqual(f.snapshot(),before)
        EVENTS.append(exact({'kind':'native_preflight_control','fixture':self.id(),
            'error':str(result.err()),'logs':result.meta().logs(),
            'signature_verification':'ENABLED_OBSERVED','state_and_fee_unchanged':True}))

    def test_generated_native_recovery_conserves_supply_and_separates_donations(self):
        f=VM(self.id());sources=[f.create_token('generated_source_'+str(i)) for i in range(4)]
        f.clock(9);rng=random.Random(0x4d335245434f564552)
        booked=0;donations=0
        for step in range(24):
            amount=rng.choice([1,12,13,24,25,26,rng.randint(1,10**12)])
            destination=K['custody'] if step%3==0 else sources[step%4]
            tax=(amount*8+99)//100
            f.token_transfer(destination,amount)
            if destination==K['custody']:donations+=amount-tax
            if step%4!=3:continue
            expected=sum(f.view('generated_source_'+str(i))['withheld'] for i in range(4))
            expected+=f.view('custody')['withheld']+f.view('mint')['mint_withheld']
            # A third party can harvest first, without claiming R or receiving tokens.
            f.send('generated_external_harvest',[ix(bytes([26,4]),[am(K['mint'],w=True),am(sources[0],w=True)])])
            f.send('generated_permissionless_recovery',[f.recover_ix(sources)])
            booked+=expected
            self.assertEqual(f.view('inventory'),{'R':booked,'guard':0})
            self.assertEqual(f.view('custody')['spendable'],booked+donations)
            total=f.view('genesis_holding')['spendable']+f.view('custody')['spendable']
            total+=sum(f.view('generated_source_'+str(i))['spendable'] for i in range(4))
            self.assertEqual(total,SUPPLY);self.assertEqual(f.view('mint')['supply'],SUPPLY)
            f.send('generated_retry_no_credit',[f.recover_ix(sources)])
            self.assertEqual(f.view('inventory')['R'],booked)
            count('generated_recovery_conservation_checkpoints')

    def test_recovery_late_compute_and_later_instruction_failure_rollback(self):
        def fixture(label):
            f=VM(label);source=f.create_token('late_source');f.clock(9);f.token_transfer(source,25)
            return f,source
        control,source=fixture(self.id()+'control')
        control.send('successful_recovery_compute_control',[control.recover_ix([source])])
        units=int(EVENTS[-1]['compute_units'])
        f,source=fixture(self.id()+'compute_fault')
        f.send('late_recovery_compute_exhaustion',[set_compute_unit_limit(units-500),f.recover_ix([source])],
            error='ComputationalBudgetExceeded',index=1)
        self.assertIn(f'Program {T} success',EVENTS[-1]['logs'])
        self.assertIn('Program log: HTFP CPI withdraw mint withholding',EVENTS[-1]['logs'])
        g,source=fixture(self.id()+'later_instruction')
        bad=ix(bytes([26,1])+struct.pack('<QBQ',1,7,0),[am(K['genesis_holding'],w=True),
            am(K['mint']),am(source,w=True),am(g.holder.pubkey(),s=True)])
        g.send('successful_recovery_then_later_native_failure',[g.recover_ix([source]),bad],[g.holder],error=32,index=1)
        self.assertTrue(EVENTS[-1]['htfp_event_hex'])
        self.assertEqual(g.view('inventory')['R'],0);self.assertEqual(g.view('late_source')['withheld'],2)

    def test_native_multisig_signer_source_and_payee_aliases(self):
        for alias in ['source_is_signer','payee_is_multisig','payee_is_signer']:
            f=VM(self.id()+alias);f.fund(R,10**10)
            a,b=Keypair(),Keypair();multi=f.multisig('alias_multisig',2,[a.pubkey(),b.pubkey()])
            source=f.create_token('alias_source',owner=multi,keypair=a if alias=='source_is_signer' else None)
            f.token_transfer(source,10**18)
            payee=multi if alias=='payee_is_multisig' else a.pubkey() if alias=='payee_is_signer' else source
            f.track('alias_payee',payee,'state')
            # A new zero-lamport payee must receive enough for actual runtime rent rules.
            before=f.svm.get_balance(payee) or 0
            f.send('native_multisig_alias_'+alias,[f.redeem_ix(10**17,source=source,authority=multi,
                signers=[a.pubkey(),b.pubkey()],payee=payee)],[a,b])
            self.assertEqual(f.view('alias_source')['spendable'],9*10**17)
            self.assertGreater(f.svm.get_balance(payee),before)
            count('native_multisig_alias_profiles')

    def test_exact_success_event_codecs(self):
        f=VM(self.id());initialized=bytes.fromhex(EVENTS[-1]['htfp_event_hex'][0])
        self.assertEqual((initialized[:10],len(initialized)),(b'HTFPEVT1\x01\x00',107))
        f.send('zero_recovery_codec',[f.recover_ix()])
        recovered=bytes.fromhex(EVENTS[-1]['htfp_event_hex'][0])
        self.assertEqual((recovered[:10],len(recovered)),(b'HTFPEVT1\x01\x01',104))
        self.assertEqual(struct.unpack_from('<QQQHHH',recovered,74),(0,0,0,0,0,0))
        f.fund(R,10**10);f.fund(K['genesis_owner'],1_000_000)
        before=f.svm.get_balance(R);maintenance=f.svm.minimum_balance_for_rent_exemption(0)
        amount=10**17;minimum=1
        f.send('redemption_codec',[f.redeem_ix(amount,minimum=minimum)],[f.holder])
        redeemed=bytes.fromhex(EVENTS[-1]['htfp_event_hex'][0])
        self.assertEqual((redeemed[:10],len(redeemed)),(b'HTFPEVT1\x01\x02',194))
        fields=struct.unpack_from('<QQQQQQQ',redeemed,138)
        payout=before-f.svm.get_balance(R)
        self.assertEqual(fields,(amount,minimum,SUPPLY,before-maintenance,maintenance,payout,SUPPLY-amount))
