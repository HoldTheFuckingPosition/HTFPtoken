"""Genuine native/custom instruction cases; fault fixtures explicitly labelled."""
import os,random,struct,unittest
from pathlib import Path
from solders.keypair import Keypair
from solders.account import Account
from solders.compute_budget import set_compute_unit_limit
from solders.pubkey import Pubkey
from harness import VM,K,H,T,R,SYSTEM,LEGACY,SUPPLY,MAX,EVENTS,COUNTS,am,ix,tlv,fee,count,exact

class InitializeTests(unittest.TestCase):
    def test_native_genesis_fields_epoch_schedule_and_revocation(self):
        f=VM(self.id())
        d=bytes(f.svm.get_account(K['mint']).data);ext=tlv(d)[1]
        self.assertEqual(f.view('mint')['supply'],SUPPLY)
        self.assertEqual(d[44],7);self.assertEqual(ext[:32],bytes(32))
        self.assertEqual(ext[32:64],bytes(K['tax_authority']))
        self.assertEqual(struct.unpack_from('<QQH',ext,72),(7,MAX,0))
        self.assertEqual(struct.unpack_from('<QQH',ext,90),(9,MAX,800))
        self.assertIsNone(f.view('mint')['mint_authority'])
        self.assertIsNone(f.view('mint')['freeze_authority'])
        dest=f.create_token('epoch_recipient')
        for epoch,bps in [(7,0),(8,0),(9,800)]:
            f.clock(epoch)
            for amount in [0,1,12,13,24,25,26,500,10**18]:
                before=f.view('epoch_recipient');s0=f.view('mint')['supply']
                f.token_transfer(dest,amount)
                after=f.view('epoch_recipient')
                tax=after['withheld']-before['withheld']
                self.assertEqual(after['spendable']-before['spendable']+tax,amount)
                self.assertLessEqual(amount*bps,tax*10000)
                self.assertLess(tax*10000-amount*bps,10000)
                self.assertEqual(f.view('mint')['supply'],s0)
                count('native_epoch_fee_cases')
        f.send('native_forbidden_fee_edit',[ix(bytes([26,5])+struct.pack('<HQ',0,MAX),[am(K['mint'],w=True),am(f.initializer.pubkey(),s=True)])],error=29,index=0)
        f.send('native_forbidden_issuance',[ix(bytes([14])+struct.pack('<QB',1,7),[am(K['mint'],w=True),am(K['genesis_holding'],w=True),am(f.initializer.pubkey(),s=True)])],error=5,index=0)

    def test_prefunded_fresh_PDAs_no_refund_or_reserve_debit(self):
        for mode in ['below','exact','above']:
            f=VM(self.id()+mode,initialize=False)
            expected={}
            for role,length in [('config',175),('inventory',20),('custody',178)]:
                required=f.svm.minimum_balance_for_rent_exemption(length)
                before=f.svm.minimum_balance_for_rent_exemption(0) if mode=='below' else required+(123456 if mode=='above' else 0)
                f.fund(K[role],before)
                expected[role]=max(before,required)
            f.fund(R,2_000_000);f.fund(K['tax_authority'],1_000_000)
            res=f.svm.get_balance(R);tax=f.svm.get_balance(K['tax_authority'])
            f.send('initialize_positive_prefunds',[f.initialize_ix()])
            for role,want in expected.items():self.assertEqual(f.svm.get_balance(K[role]),want)
            self.assertEqual(f.svm.get_balance(R),res);self.assertEqual(f.svm.get_balance(K['tax_authority']),tax)
            self.assertEqual(f.view('inventory'),{'R':0,'guard':0})
            self.assertEqual(f.view('custody')['spendable'],0)
            count('prefund_profiles')

    def test_initializer_wrong_signature_wire_and_occupied_state(self):
        f=VM(self.id(),initialize=False)
        other=Keypair();f.track('other',other.pubkey(),'state');f.fund(other.pubkey(),10_000_000)
        f.send('wrong_initializer',[f.initialize_ix(other.pubkey())],[other],error=7001,index=0)
        f.send('missing_initializer_signature',[f.initialize_ix(signer=False)],payer=other,error=7005,index=0)
        good=f.initialize_ix()
        f.send('unexpected_init_payload',[ix(bytes(good.data)+b'\0',list(good.accounts),H)],error=7000,index=0)
        for role,owner in [('config',H),('custody',T)]:
            v=VM(self.id()+role,initialize=False)
            v.inject_account(role,bytes(175 if role=='config' else 178),owner,3_000_000,'unreachable foreign/pre-owned canonical PDA; rejection-only fault, no token amounts fabricated')
            v.send('reject_occupied_'+role,[v.initialize_ix()],error=7017,index=0)

    def test_wrong_native_genesis_not_just_digest(self):
        for options,error in [
            ({'amount':SUPPLY-1},7016),({'bps':900},7016),({'maximum':MAX-1},7016),
            ({'revoke_mint':False},7016),({'revoke_fee':False},7016),({'extra_mint':True},7004)]:
            f=VM(self.id()+str(options),initialize=False,genesis_options=options)
            f.send('reject_incomplete_native_genesis',[f.initialize_ix()],error=error,index=0)
            count('native_genesis_negative_profiles')

    def test_replay_zero_reserve_and_post_terminal(self):
        f=VM(self.id())
        f.send('initialization_replay',[f.initialize_ix()],error=7017,index=0)
        f.send('empty_reserve_no_burn',[f.redeem_ix(1)],[f.holder],error=7008,index=0)
        f.fund(R,5_000_000)
        f.send('full_supply_redemption',[f.redeem_ix(SUPPLY)],[f.holder])
        self.assertEqual(f.view('mint')['supply'],0)
        self.assertEqual(f.svm.get_balance(R),f.svm.minimum_balance_for_rent_exemption(0))
        f.send('postterminal_reinitialize',[f.initialize_ix()],error=7017,index=0)
        f.fund(R,1_000_000)
        f.send('postterminal_donation_stays_immobilized',[f.redeem_ix(1)],[f.holder],error=7007,index=0)

    def test_late_initialization_failure_and_later_instruction_rollback(self):
        control=VM(self.id()+'control')
        units=int(next(e['compute_units'] for e in reversed(EVENTS) if e.get('fixture')==control.label and e.get('case')=='initialize'))
        f=VM(self.id()+'compute_fault',initialize=False)
        f.send('late_init_compute_exhaustion',[set_compute_unit_limit(units-500),f.initialize_ix()],error='ComputationalBudgetExceeded',index=1)
        logs=EVENTS[-1]['logs']
        self.assertIn('Program log: HTFP init guard installed',logs)
        self.assertTrue(any('initialize custody' in line for line in logs))
        g=VM(self.id()+'later_tx_failure',initialize=False)
        dest=g.create_token('destination')
        bad=ix(bytes([26,1])+struct.pack('<QBQ',1,7,1),[am(K['genesis_holding'],w=True),am(K['mint']),am(dest,w=True),am(g.holder.pubkey(),s=True)])
        g.send('successful_init_then_later_native_failure',[g.initialize_ix(),bad],[g.holder],error=32,index=1)
        self.assertTrue(any(line.startswith('Program data: ') for line in EVENTS[-1]['logs']))

class RedemptionTests(unittest.TestCase):
    def funded(self,label):
        f=VM(label);f.fund(R,10**12);f.fund(K['genesis_owner'],1_000_000);return f
    def test_generated_native_floor_and_ratio_conservation(self):
        f=self.funded(self.id());rng=random.Random(0x4d3352454445454d)
        for i in range(48):
            s=f.view('mint')['supply'];v=f.svm.get_balance(R)-f.svm.minimum_balance_for_rent_exemption(0)
            a=rng.randint(max(1,s//10000),max(1,s//8))
            before=f.svm.get_balance(K['genesis_owner']);src=f.view('genesis_holding')['spendable']
            f.send('generated_redemption',[f.redeem_ix(a)],[f.holder])
            payout=f.svm.get_balance(K['genesis_owner'])-before
            self.assertGreater(payout,0)
            self.assertLessEqual(payout*s,v*a);self.assertLess(v*a,(payout+1)*s)
            self.assertEqual(f.view('mint')['supply']+a,s)
            self.assertEqual(f.view('genesis_holding')['spendable']+a,src)
            self.assertGreaterEqual((v-payout)*s,v*(s-a))
            self.assertEqual(f.view('inventory'),{'R':0,'guard':0})
            count('custom_runtime_generated_redemptions')

    def test_amount_destination_authorization_minimum_and_protocol_aliases(self):
        f=self.funded(self.id());a=SUPPLY//10
        f.send('zero_amount',[f.redeem_ix(0)],[f.holder],error=7006,index=0)
        f.send('too_large_amount',[f.redeem_ix(SUPPLY+1)],[f.holder],error=7006,index=0)
        f.send('zero_floor_no_burn',[f.redeem_ix(1)],[f.holder],error=7008,index=0)
        f.send('minimum_not_met',[f.redeem_ix(a,minimum=10**12)],[f.holder],error=7009,index=0)
        wrong=Keypair();f.track('wrong',wrong.pubkey(),'state');f.fund(wrong.pubkey(),1_000_000)
        f.send('wrong_holder',[f.redeem_ix(a,authority=wrong.pubkey())],[wrong],error=7005,index=0)
        f.send('recipient_bytes_do_not_match',[f.redeem_ix(a,recipient=wrong.pubkey())],[f.holder],error=7005,index=0)
        f.send('protocol_payee_reserve',[f.redeem_ix(a,payee=R)],[f.holder],error=7003,index=0)
        f.send('protocol_payee_custody',[f.redeem_ix(a,payee=K['custody'])],[f.holder],error=7003,index=0)
        f.send('unimplemented_process',[ix(b'HTFP\1\3',[],H)],error=7015,index=0)

    def test_source_payee_owner_payee_and_fee_payer_payee_aliases(self):
        for alias in ['source','owner','payer','self_owned_source']:
            f=self.funded(self.id()+alias);a=SUPPLY//20
            source=K['genesis_holding'];authority=f.holder
            if alias=='self_owned_source':
                kp=Keypair();source=kp.pubkey();f.track('self_source',source)
                from solders.system_program import create_account
                f.send('native_self_owned_source',[create_account({'from_pubkey':f.initializer.pubkey(),'to_pubkey':source,'lamports':f.svm.minimum_balance_for_rent_exemption(178),'space':178,'owner':T}),
                   ix(bytes([18])+bytes(source),[am(source,w=True),am(K['mint'])])],[kp])
                f.token_transfer(source,a);authority=kp
            payee=source if alias in ['source','self_owned_source'] else K['genesis_owner'] if alias=='owner' else K['initializer']
            before=f.svm.get_balance(payee)
            v=f.svm.get_balance(R)-f.svm.minimum_balance_for_rent_exemption(0)
            s=f.view('mint')['supply']
            f.send('permitted_alias_'+alias,[f.redeem_ix(a,source=source,authority=authority.pubkey(),payee=payee)],[authority])
            observed=f.svm.get_balance(payee)-before
            if alias=='payer':observed+=10000 # two real transaction signatures; fees outside payout
            self.assertLessEqual(observed*s,v*a);self.assertLess(v*a,(observed+1)*s)
            count('permitted_alias_cases')

    def test_external_final_native_burn_and_underfunded_reserve(self):
        f=VM(self.id());f.native_burn(K['genesis_holding'],SUPPLY)
        f.fund(R,2_000_000)
        f.send('external_extinction_no_payout',[f.redeem_ix(1)],[f.holder],error=7007,index=0)
        f.send('external_extinction_no_reset',[f.initialize_ix()],error=7017,index=0)
        g=VM(self.id()+'underfunded')
        # Explicit lamport-boundary fault; no token amount/supply is forged.
        g.inject_account('reserve',b'',SYSTEM,788537,'below-current-rent existing System receiver boundary, matching historical form; explicit local state injection')
        g.send('undermaintenance_no_burn',[g.redeem_ix(SUPPLY)],[g.holder],error=7008,index=0)

    def test_late_system_overflow_rolls_back_real_burn_and_later_tx_failure(self):
        f=self.funded(self.id());payee=Keypair().pubkey();f.track('overflow_payee',payee,'state');f.fund(payee,1_000_000)
        f.set_lamports_fault('overflow_payee',MAX,'unreachable destination-lamport-overflow fault solely for native payout failure after genuine Burn CPI')
        f.send('native_System_overflow_after_successful_burn',[f.redeem_ix(SUPPLY//10,payee=payee)],[f.holder],error='ArithmeticOverflow',index=0)
        logs=EVENTS[-1]['logs'];self.assertIn(f'Program {T} success',logs)
        self.assertTrue(any('native redemption payout' in x for x in logs))
        g=self.funded(self.id()+'later');dest=g.create_token('late_bad_destination')
        bad=ix(bytes([26,1])+struct.pack('<QBQ',1,7,1),[am(K['genesis_holding'],w=True),am(K['mint']),am(dest,w=True),am(g.holder.pubkey(),s=True)])
        g.send('successful_redeem_then_later_native_error',[g.redeem_ix(SUPPLY//10),bad],[g.holder],error=32,index=1)
        self.assertTrue(EVENTS[-1]['htfp_event_hex'])
