import json,os,random,struct,unittest
from pathlib import Path
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from harness import VM,K,H,T,R,SYSTEM,LEGACY,SUPPLY,MAX,ROOT,EVENTS,am,ix,count,tlv,fee

class RecoveryTests(unittest.TestCase):
    def test_actual_account_mint_custody_self_harvest_donations_and_retry(self):
        f=VM(self.id());account=f.create_token('tax_source');f.clock(9)
        f.token_transfer(account,500)
        self.assertEqual(f.view('tax_source')['spendable'],460)
        self.assertEqual(f.view('tax_source')['withheld'],40)
        f.token_transfer(K['custody'],500) # Spendable donation460 is not booked R.
        self.assertEqual(f.view('inventory')['R'],0)
        f.send('recover_account_plus_implicit_custody',[f.recover_ix([account])])
        self.assertEqual(f.view('custody')['spendable'],540) # donation460 + real recovered80
        self.assertEqual(f.view('custody')['withheld'],0)
        self.assertEqual(f.view('inventory')['R'],80)
        f.send('empty_retry_no_double_count',[f.recover_ix([account])])
        self.assertEqual(f.view('inventory')['R'],80)
        f.token_transfer(account,25) # two withheld native base units.
        f.send('external_permissionless_harvest_race',[ix(bytes([26,4]),[am(K['mint'],w=True),am(account,w=True)])])
        self.assertEqual(f.view('mint')['mint_withheld'],2)
        f.send('recover_mint_harvested_inventory_no_explicit_sources',[f.recover_ix()])
        self.assertEqual(f.view('inventory')['R'],82)
        self.assertEqual(f.view('custody')['spendable'],542)
        self.assertEqual(f.view('mint')['supply'],SUPPLY)
        self.assertEqual(f.view('mint')['mint_withheld'],0)
        count('genuine_recovery_paths',3)

    def test_empty_closed_invalid_duplicate_and_count_boundaries(self):
        f=VM(self.id());empty=f.create_token('empty')
        closed=Keypair().pubkey();f.track('closed_or_absent',closed,'state')
        f.send('empty_and_absent_noop',[f.recover_ix([empty,closed])])
        raw=bytes.fromhex(EVENTS[-1]['htfp_event_hex'][0])
        self.assertEqual(struct.unpack_from('<HHH',raw,len(raw)-6),(2,1,1))
        # A genuinely created then closed token account has the same absent representation.
        closing=f.create_token('closing')
        f.send('native_close_empty_source',[ix(bytes([9]),[am(closing,w=True),am(f.initializer.pubkey(),w=True),am(f.holder.pubkey(),s=True)])],[f.holder])
        f.send('actual_closed_source_noop',[f.recover_ix([closing])])
        f.send('duplicate_sources',[f.recover_ix([empty,empty])],error=7003,index=0)
        f.send('explicit_implicit_custody',[f.recover_ix([K['custody']])],error=7003,index=0)
        f.send('mint_as_source',[f.recover_ix([K['mint']])],error=7003,index=0)
        invalid=Keypair().pubkey();f.track('positive_System_source',invalid,'state');f.fund(invalid,1_000_000)
        f.send('positive_System_not_closed',[f.recover_ix([invalid])],error=7014,index=0)
        f.send('count_mismatch',[f.recover_ix([],count_override=1)],error=7000,index=0)
        f.send('above_cap_count_rejected',[f.recover_ix([],count_override=33)],error=7000,index=0)
        f.mutate('inventory',lambda d:d.__setitem__(11,1),'unreachable persistent in-flight flag; rejection-only reentry guard fixture')
        f.send('shared_guard_refuses_entry',[f.recover_ix()],error=7012,index=0)

    def test_cap32_real_version0_lookup_table_packet_and_resources(self):
        f=VM(self.id());sources=[f.create_token('batch_'+str(i)) for i in range(32)]
        f.clock(9)
        for source in sources:f.token_transfer(source,1)
        addresses=[K['config'],K['inventory'],K['mint'],K['custody'],K['tax_authority'],*sources]
        table=f.lookup_table(addresses)
        from solders.compute_budget import set_compute_unit_limit
        f.send('recover_actual_cap32_with_real_lookup_table',[set_compute_unit_limit(400_000),f.recover_ix(sources)],versioned=[table])
        self.assertLessEqual(int(EVENTS[-1]['packet_bytes']),1232)
        self.assertEqual(f.view('inventory')['R'],32)
        self.assertEqual(f.view('custody')['spendable'],32)
        for i in range(32):self.assertEqual(f.view('batch_'+str(i))['withheld'],0)
        count('cap32_sources_actually_recovered',32)

    def test_recovery_passive_flags_and_malformed_source_refusal(self):
        f=VM(self.id());s=f.create_token('guard_memo_source',extensions=[7,8,11])
        f.flag(s,30,True);f.flag(s,34,True);f.clock(9)
        # Memo requirement on destination needs a genuine preceding Memo instruction.
        memo=Pubkey.from_string('MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr')
        native=ix(bytes([26,1])+struct.pack('<QBQ',25,7,2),[am(K['genesis_holding'],w=True),am(K['mint']),am(s,w=True),am(f.holder.pubkey(),s=True)])
        f.send('native_memo_transfer_into_guarded_source',[ix(b'local-M3 transfer',[],memo),native],[f.holder])
        f.send('harvest_ignores_passive_guard_memo_immutable_flags',[f.recover_ix([s])])
        self.assertEqual(f.view('inventory')['R'],2)
        f.mutate('guard_memo_source',lambda d:d.__setitem__(108,0),'uninitialized base-state source fault; balances originated only in genuine native transfers')
        f.send('invalid_native_source_atomically_refused',[f.recover_ix([s])],error=7014,index=0)

class AuthorizationTests(unittest.TestCase):
    def fund(self,f):
        f.fund(R,10**10);f.fund(K['genesis_owner'],1_000_000)
    def test_native_multisigs_both_program_owners_and_configured_slots(self):
        for legacy in [False,True]:
            for duplicate_members in [False,True]:
                with self.subTest(legacy=legacy,duplicate_members=duplicate_members):
                    f=VM(self.id()+str((legacy,duplicate_members)));self.fund(f)
                    a,b,c=Keypair(),Keypair(),Keypair()
                    members=[a.pubkey(),a.pubkey(),b.pubkey()] if duplicate_members else [a.pubkey(),b.pubkey(),c.pubkey()]
                    multi=f.multisig('multisig',2,members,legacy=legacy)
                    source=f.create_token('multisig_source',owner=multi);f.token_transfer(source,10**18)
                    if not duplicate_members:
                        f.send('threshold_minus_one',[f.redeem_ix(10**17,source=source,authority=multi,signers=[a.pubkey()])],[a],error=7005,index=0)
                    outsider=Keypair()
                    f.send('nonmember_signer',[f.redeem_ix(10**17,source=source,authority=multi,signers=[outsider.pubkey()])],[outsider],error=7005,index=0)
                    f.send('duplicate_supplied_signer',[f.redeem_ix(10**17,source=source,authority=multi,signers=[a.pubkey(),a.pubkey()])],[a],error=7003,index=0)
                    signing=[a] if duplicate_members else [a,b]
                    f.send('actual_native_multisig_redemption',[f.redeem_ix(10**17,source=source,authority=multi,signers=[x.pubkey() for x in signing])],signing)
                    self.assertEqual(f.view('multisig_source')['spendable'],9*10**17)
                    self.assertEqual(f.view('mint')['supply'],SUPPLY-10**17)
                    count('actual_native_multisig_profiles')

    def test_delegate_excluded_and_self_delegate_native_allowance_effects(self):
        f=VM(self.id());self.fund(f);g=K['genesis_holding'];a=10**17
        delegate=Keypair();f.approve(g,delegate.pubkey(),a)
        f.send('delegate_alone_excluded',[f.redeem_ix(a,authority=delegate.pubkey())],[delegate],error=7005,index=0)
        f.approve(g,f.holder.pubkey(),a)
        f.send('self_delegated_insufficient_allowance',[f.redeem_ix(a+1)],[f.holder],error=1,index=0)
        f.send('self_delegated_partial_allowance',[f.redeem_ix(a//2)],[f.holder])
        self.assertEqual(f.view('genesis_holding')['allowance'],a//2)
        self.assertEqual(f.view('genesis_holding')['delegate'],str(f.holder.pubkey()))
        f.send('self_delegated_exhaust_allowance',[f.redeem_ix(a//2)],[f.holder])
        self.assertEqual(f.view('genesis_holding')['allowance'],0)
        self.assertIsNone(f.view('genesis_holding')['delegate'])
        count('native_self_delegate_branches',3)

    def test_enabled_disabled_guard_memo_and_immutable_owner(self):
        f=VM(self.id());self.fund(f)
        source=f.create_token('extended_holder',extensions=[7,8,11])
        f.token_transfer(source,10**18)
        f.flag(source,30,True);f.flag(source,34,True)
        f.send('enabled_owner_guard_rejected_before_burn',[f.redeem_ix(10**17,source=source)],[f.holder],error=7004,index=0)
        f.flag(source,34,False)
        f.send('disabled_guard_memo_immutable_owner_native_burn',[f.redeem_ix(10**17,source=source)],[f.holder])
        self.assertEqual(f.view('extended_holder')['spendable'],9*10**17)
        self.assertIn('7',f.view('extended_holder')['extensions'])
        self.assertEqual(f.view('extended_holder')['extensions']['8'],'01')
        count('native_passive_extension_modes',2)

    def test_stale_None_payloads_accepted_invalid_tags_and_unknown_extensions_rejected(self):
        f=VM(self.id(),initialize=False)
        f.mutate('mint',lambda d:d.__setitem__(slice(4,36),bytes(K['genesis_owner'])),'valid native COptionNone with inactive stale pubkey; nonmonetary compatibility fixture')
        f.send('initialize_with_native_compatible_stale_None',[f.initialize_ix()])
        self.fund(f)
        f.mutate('genesis_holding',lambda d:d.__setitem__(slice(76,108),bytes(K['initializer'])),'valid inactive delegateNone payload; no amount/supply fabrication')
        f.send('redeem_stale_delegate_None_payload',[f.redeem_ix(10**17)],[f.holder])
        self.assertIsNone(f.view('genesis_holding')['delegate'])
        f.mutate('genesis_holding',lambda d:d.__setitem__(slice(72,76),(2).to_bytes(4,'little')),'invalid native optional-key tag, negative only')
        f.send('invalid_COption_tag',[f.redeem_ix(10**17)],[f.holder],error=7002,index=0)
        g=VM(self.id()+'unknown_extension');self.fund(g)
        source=g.create_token('unknown_extra',extensions=[11])
        g.token_transfer(source,10**18)
        # Change zero-value account extension11 to unsupported15 as explicit schema fault.
        def unknown(data):
            pos=166
            while pos<len(data):
                tag,n=struct.unpack_from('<HH',data,pos)
                if tag==11:data[pos:pos+2]=(15).to_bytes(2,'little');return
                pos+=4+n
            raise AssertionError('expected native allocated guard extension')
        # InitializeAccount3 may leave optional reserved space uninitialized until toggle.
        g.flag(source,34,False)
        g.mutate('unknown_extra',unknown,'unsupported holder TLV negative-only fault; underlying tokens genuinely native-transferred')
        g.send('unsupported_holder_extension',[g.redeem_ix(10**17,source=source)],[g.holder],error=7004,index=0)

    def test_authenticated_real_PDA_wallet_CPI_and_missing_controller(self):
        helper_data=json.loads((ROOT/'config/m3/helper_public.json').read_text())
        helper=Pubkey.from_bytes(bytes.fromhex(helper_data['program_hex']))
        f=VM(self.id());self.fund(f)
        from harness import ARTIFACTS
        f.svm.add_program(helper,ARTIFACTS['M3_HELPER_ELF'])
        wallet,_=Pubkey.find_program_address([b'wallet-holder'],helper)
        f.track('wallet_PDA',wallet,'state')
        source=f.create_token('PDA_holder',owner=wallet);f.token_transfer(source,10**18)
        call=f.redeem_ix(10**17,source=source,authority=wallet,authority_signer=False)
        def forward(controller,signer):
            return ix(bytes(call.data),[am(controller,s=signer),am(H),*list(call.accounts)],helper)
        f.send('wallet_missing_controller_signature',[forward(f.holder.pubkey(),False)],error=9001,index=0)
        wrong=Keypair()
        f.send('wallet_wrong_controller',[forward(wrong.pubkey(),True)],[wrong],error=9001,index=0)
        f.send('authenticated_wallet_PDA_native_Burn_and_payout',[forward(f.holder.pubkey(),True)],[f.holder])
        self.assertEqual(f.view('PDA_holder')['spendable'],9*10**17)
        self.assertTrue(any(f'Program {H} invoke [2]'==s for s in EVENTS[-1]['logs']))
        count('genuine_authenticated_PDA_CPI_cases')

class DefaultProfileTests(unittest.TestCase):
    def test_actual_default_ELF_has_no_accepted_monetary_profile(self):
        f=VM(self.id(),default=True,initialize=False)
        f.send('default_initialize_disabled',[f.initialize_ix()],error=7015,index=0)
        f.send('default_recover_disabled',[f.recover_ix()],error=7015,index=0)
        f.send('default_redeem_disabled',[f.redeem_ix(1)],[f.holder],error=7015,index=0)
        count('default_disabled_endpoints',3)
