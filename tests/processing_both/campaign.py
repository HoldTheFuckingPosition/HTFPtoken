"""Finite genuine new BothToken processing campaigns; no public network."""
from pathlib import Path
import argparse
import gzip
import json
import struct
import time
import traceback
from fractions import Fraction
from runtime import ROOT, FROZEN, Run, n, lge, fee, source_hashes, resources

SCOPE_SHA=n.sha((ROOT/'evidence/processing_both/SCOPE.md').read_bytes())
PROFILE=json.loads((ROOT/'config/processing-both/profile.json').read_bytes())
BINDING=json.loads((ROOT/'config/processing-both/processing_binding.json').read_bytes())
ABI=json.loads((ROOT/'config/processing-both/abi.json').read_bytes())
PROCESSING_COMMITMENT=BINDING['sha256']


class Scenario(fee.Lifecycle):
    def __init__(self,run,actors,t0):
        super().__init__(run);self.actors=actors;self.shared_t0=t0
        self.public={k:n.Pubkey.from_string(v['base58']) for k,v in PROFILE['identities'].items()}
        self.process_proofs=[];self.total_process_burn=0;self.total_redeem_burn=0

    def snapshot_file(self,filename,phase,**extra):
        rent=self.r.svm.get_rent()
        extra['actual_Rent_getter']={'lamports_per_byte_year':rent.lamports_per_byte_year,'exemption_threshold':rent.exemption_threshold,'burn_percent':rent.burn_percent,'minimum_balance_0':rent.minimum_balance(0),'minimum_balance_165':rent.minimum_balance(165),'minimum_balance_89':rent.minimum_balance(89)}
        extra['raw_Rent']=n.account_record(n.RENT,self.r.svm.get_account(n.RENT))
        extra['raw_Clock']=n.account_record(n.CLOCK,self.r.svm.get_account(n.CLOCK))
        return super().snapshot_file(filename,phase,**extra)

    def prepare(self, fixture, native_wsol, public):
        r = self.r
        self.operations, self.mint_signer, self.founder = [fee.published_test_signer(i) for i in (1, 2, 3)]
        assert self.operations.pubkey() == public["initializer"] and self.mint_signer.pubkey() == public["mint"] and self.founder.pubkey() == public["genesis_owner"]
        self.team, self.marketing = self.actors['team'], self.actors['marketing']
        self.participants = self.actors['participants']
        r.operations = self.operations
        for role, key in [("operations", self.operations.pubkey()), ("founder", self.founder.pubkey()), ("mint", self.mint_signer.pubkey()), ("team", self.team.pubkey()), ("marketing", self.marketing.pubkey())]:
            self.track(role, key)
        for i, kp in enumerate(self.participants, 1):
            self.track("participant-" + str(i), kp.pubkey())
        for role in ["config", "inventory", "custody", "genesis_holding", "tax_authority", "reserve"]:
            self.track(role, public[role])
        self.tax_authority = public["tax_authority"]
        self.track("clock", n.CLOCK)
        self.track("rent", n.RENT)
        self.track("wsol_mint", n.WSOL)
        assert r.svm.get_account(n.RESERVE) is None
        r.append("SYNTHETIC_SOL_AIRDROP_PROSPECTIVE", address=str(self.operations.pubkey()), lamports=str(lge.OPS_START))
        answer = r.svm.airdrop(self.operations.pubkey(), lge.OPS_START)
        r.synthetic_airdrop_calls += 1
        assert r.svm.get_balance(self.operations.pubkey()) == lge.OPS_START
        r.emit({"kind": "synthetic_SOL_initialization", "address": str(self.operations.pubkey()), "before": None,
                "after": n.account_record(self.operations.pubkey(), r.svm.get_account(self.operations.pubkey())),
                "airdrop_return_type": type(answer).__module__ + "." + type(answer).__name__, "public_funds": False})
        r.svm.set_account(n.WSOL, n.Account(r.svm.minimum_balance_for_rent_exemption(82), native_wsol, n.TOKEN))
        config_raw = (ROOT / fixture["raw_config0"]["path"]).read_bytes()
        config_key = n.Pubkey.find_program_address([b"amm_config", bytes([0, 0])], n.AMM)[0]
        self.track("amm_config", config_key)
        r.svm.set_account(config_key, n.Account(r.svm.minimum_balance_for_rent_exemption(236), config_raw, n.AMM))
        assert n.u64(config_raw, 12) == n.u64(config_raw, 108) == 2500 and n.u64(config_raw, 116) == 0
        self.track("creation_fee_receiver", n.FEE_RECEIVER)
        r.svm.set_account(n.FEE_RECEIVER, n.Account(r.svm.minimum_balance_for_rent_exemption(165), bytes(165), n.TOKEN))
        r.emit({"kind": "explicit_nonmonetary_dependency_prestate", "after": {k: r.snapshot()[k] for k in ["wsol_mint", "amm_config", "creation_fee_receiver"]},
                "disclosure": "Only exact zero-supply native SOL mint metadata, unchanged captured config0, and zero-filled fee receiver storage with local rent. No positive token, custody/R or pool state injected."})
        for i,kp in enumerate(self.actors['callers']): self.track('caller-'+str(i),kp.pubkey())
        self.track('volume', self.public['volume']);self.track('settle_authority',self.public['settle_authority'])
        self.initial_tracked_lamports = sum(int(a["lamports"]) for a in r.snapshot().values() if a is not None)
        r.send("native_initialize_zero_value_creation_fee_receiver", [n.instruction(n.TOKEN, bytes([18]) + bytes(self.founder.pubkey()), [n.am(n.FEE_RECEIVER, True), n.am(n.WSOL)])])
        assert self.amount("creation_fee_receiver") == 0
        self.t0 = self.shared_t0
        self.activation_timestamp = self.t0 + 120
        self.open_time = self.activation_timestamp + 14400
        r.clock(7, 100000, self.t0, "coherent_E7_before_genesis")
        self.plan = {"LOCAL_TEST_ONLY": True, "scope_sha256": SCOPE_SHA, "supply_base_units": str(n.SUPPLY), "decimals": "7",
                     "participants": [{"id": "participant-" + str(i + 1), "contribution_lamports": str(c), "token_base_units": str(a)} for i, (c, a) in enumerate(zip(lge.CONTRIBUTIONS, lge.ENTITLEMENTS))],
                     "total_contribution_lamports": str(lge.TOTAL), "token_allocations_base_units": {"participants": str(sum(lge.ENTITLEMENTS)), "pool": str(lge.POOL_HTFP), "team": str(lge.TEAM_HTFP), "marketing": str(lge.MARKETING_HTFP)},
                     "sol_allocations_lamports": {"reserve": str(lge.RESERVE_SOL), "pool": str(lge.POOL_SOL)},
                     "synthetic_clock": {"E": 7, "E_plus_2": 9, "initial_unix": self.t0, "activation_unix": self.activation_timestamp, "opening_unix": self.open_time, "test_only_margin_seconds": 14400, "real_prediction": False},
                     "operations_initial_lamports": str(lge.OPS_START), "creator_topup_lamports": str(lge.CREATOR_OPERATIONAL_TOPUP), "historical_fee_config_ppm": [2500, 2500], "final_creator500_validated": False}
        self.plan.update(processing_profile='LOCAL_BOTH_LGE_V1',processing_binding=PROCESSING_COMMITMENT,stage_acceptance=False)
        n.persist(r.output / 'PLAN.json', self.plan)

    def volume(self):
        d=self.raw('volume')
        return dict(credit=n.u64(d,43),last=struct.unpack_from('<q',d,51)[0],sequence=n.u64(d,59),active=d[67],origin=int.from_bytes(d[68:70],'little'),cleanup=int.from_bytes(d[70:72],'little'),nonce=n.u64(d,72))

    def full_credit_time(self):
        c=self.r.svm.get_clock();self.r.clock(c.epoch,c.slot+1,c.unix_timestamp+6000,'monotone_full_credit_refill')

    def temp(self,sequence=None):
        sequence=self.volume()['sequence'] if sequence is None else sequence
        key=n.Pubkey.find_program_address([b'htfp-tmp-wsol',bytes(self.keys['mint']),struct.pack('<Q',sequence)],n.H)[0]
        return self.track('temp_'+str(sequence),key)

    def process_ix(self,q=1600000000,caller=None,sequence=None):
        caller=caller or self.actors['callers'][0]
        values=[self.keys['config'],self.keys['inventory'],self.keys['volume'],self.keys['mint'],self.keys['custody'],self.tax_authority,n.RESERVE,self.temp(sequence),self.public['settle_authority'],caller.pubkey(),n.T22,n.TOKEN,n.WSOL,n.SYSTEM,self.public['instructions_sysvar'],n.AMM,self.keys['amm_config'],self.authority,self.keys['pool'],self.keys['vault1'],self.keys['vault0'],self.keys['observation']]
        assert len(values)==len(set(values))==22 and self.htfp_side==1
        return n.instruction(n.H,bytes.fromhex('485446500103')+struct.pack('<Q',q),[n.am(k,r['writable'],r['signer']) for k,r in zip(values,ABI['wire']['3']['accounts'])])

    def finalize_ix(self,nonce=None):
        if nonce is None:nonce=self.volume()['sequence']+1
        return n.instruction(n.H,bytes.fromhex('485446500105')+struct.pack('<Q',nonce),[n.am(self.keys['config']),n.am(self.keys['inventory'],True),n.am(self.keys['volume'],True),n.am(self.public['instructions_sysvar'])])

    def process(self,cid,q=1600000000,caller_index=0,prefund=None):
        self.r.cases(cid);caller=self.actors['callers'][caller_index]
        temp=self.temp()
        if prefund is not None and prefund>0:self.r.send(cid+'_genuine_Temp_prefund',[n.native_transfer(self.operations.pubkey(),temp,prefund)])
        before=self.r.snapshot();v0=self.volume();p0=self.r.svm.get_balance(temp) or 0;rent=self.r.svm.minimum_balance_for_rent_exemption(165)
        r0,c0,s0=self.booked(),self.amount('custody'),int(n.mint(self.raw('mint'))['supply']);reserve0=self.account('reserve').lamports
        pool0=n.pool(self.raw('pool'));a0=[self.amount('vault'+str(i)) for i in range(2)];w0=[self.withheld('vault'+str(i)) for i in range(2)]
        x=a0[1]-sum(int(pool0[k+'1']) for k in ['protocol','fund','creator']);y=a0[0]-sum(int(pool0[k+'0']) for k in ['protocol','fund','creator'])
        b=q//8*3;f=q//8*5;t=-(-f*800//10000);incoming=f-t;combined=-(-incoming*5000//1000000);creator=combined//2;trade=combined-creator;curve=incoming-combined;output=curve*y//(x+curve)
        clock=self.r.svm.get_clock();tm=max(clock.unix_timestamp,v0['last']);available=min(30000000000,v0['credit']+(tm-v0['last'])*5000000)
        self.r.emit(dict(kind='Process_expected_from_raw_prestate',case_ids=[cid],Q=str(q),B=str(b),F=str(f),T=str(t),X=str(x),Y=str(y),combined=str(combined),creator=str(creator),trade=str(trade),output=str(output),P=str(p0),L=str(rent),D=str(max(rent-p0,0)),W0=str(max(p0-rent,0)),available=str(available),stage_acceptance=False))
        row=self.r.send(cid,[self.process_ix(q,caller),self.finalize_ix()],payer=caller)
        assert len(row['signatures'])==1 and row['payer']==str(caller.pubkey())
        assert self.booked()==r0-q and self.amount('custody')==c0-q and int(n.mint(self.raw('mint'))['supply'])==s0-b
        assert self.withheld('custody')==0 and self.account('reserve').lamports==reserve0+output
        assert self.amount('vault1')==a0[1]+incoming and self.withheld('vault1')==w0[1]+t
        assert self.amount('vault0')==a0[0]-output and self.withheld('vault0')==w0[0]
        pool1=n.pool(self.raw('pool'))
        for k,delta in [('protocol1',trade*120000//1000000),('fund1',trade*40000//1000000),('creator1',creator),('protocol0',0),('fund0',0),('creator0',0)]:assert int(pool1[k])-int(pool0[k])==delta,(cid,k)
        a=self.r.svm.get_account(temp);assert (a is None and p0==0) or (a.owner==n.SYSTEM and not a.executable and len(a.data)==0 and a.lamports==p0)
        v1=self.volume();assert v1==dict(credit=available-3*f,last=tm,sequence=v0['sequence']+1,active=0,origin=0,cleanup=0,nonce=0)
        assert self.raw('inventory')[11]==0 and self.amount('custody')-self.booked()==920
        assert self.amount('founder_lp')==self.lp_receipt and n.u64(self.raw('lp_mint'),36)==self.lp_receipt
        assert O_floor(output,curve,y,x)
        self.total_process_burn+=b
        proof=dict(case_id=cid,Q=str(q),B=str(b),F=str(f),T=str(t),I=str(incoming),X=str(x),Y=str(y),combined=str(combined),creator=str(creator),trade=str(trade),O=str(output),P=str(p0),L=str(rent),D=str(max(rent-p0,0)),W0=str(max(p0-rent,0)),R_before=str(r0),R_after=str(self.booked()),S_before=str(s0),S_after=str(s0-b),network_fee=row['network_fee_expected_lamports'],transaction_sha256=row['transaction_sha256'])
        self.process_proofs.append(proof);self.r.emit(dict(kind='Process_measured_raw_certificate',**proof));return row

    def reject_process(self,cid,expected,q=1600000000,ix=None,tail=None,caller=None,signer_objects=()):
        caller=caller or self.actors['callers'][0];self.r.cases(cid)
        return self.r.send(cid,[ix or self.process_ix(q,caller),tail or self.finalize_ix()],signer_objects,payer=caller,expected_error=expected)

    def redeem_ix(self,minimum,amount=10**17,source=None):
        owner=self.participants[0];payee=owner.pubkey()
        return n.instruction(n.H,bytes.fromhex('485446500102')+struct.pack('<QQ',amount,minimum)+bytes(payee)+bytes([0,0]),[n.am(self.keys['config']),n.am(self.keys['inventory'],True),n.am(self.keys['mint'],True),n.am(source or self.keys['participant-1_htfp'],True),n.am(n.RESERVE,True),n.am(payee,True),n.am(owner.pubkey(),False,True),n.am(n.T22),n.am(n.SYSTEM)])

    def prefix(self,fixture,wsol):
        r=self.r;r.cases('N001');self.prepare(fixture,wsol,self.public)
        r.send('fund_unrelated_callers_outside_LGE',[n.native_transfer(self.operations.pubkey(),k.pubkey(),10000000) for k in self.actors['callers']])
        self.genesis();self.ata('callerA_htfp',self.actors['callers'][0].pubkey(),self.keys['mint'],n.T22)
        init=n.instruction(n.H,bytes.fromhex('485446500104'),[n.am(self.keys['config']),n.am(self.keys['inventory'],True),n.am(self.keys['volume'],True),n.am(self.actors['callers'][2].pubkey(),True,True),n.am(n.SYSTEM)])
        r.send('N001_InitProcessing_unrelated_C_only',[init],payer=self.actors['callers'][2]);assert self.volume()==dict(credit=30000000000,last=1700000000,sequence=0,active=0,origin=0,cleanup=0,nonce=0)
        r.cases('N002');self.collect_and_distribute();self.initialize();self.snapshot_file('PHASE_POOL_INITIALIZED.json','native_fixed_pool_BothToken')
        r.cases('N003');self.ata('trader_wsol',self.participants[4].pubkey(),n.WSOL,n.TOKEN)
        r.send('separate_operational_trader_wrap',[n.native_transfer(self.operations.pubkey(),self.keys['trader_wsol'],lge.TRADER_OPERATIONAL_SOL),n.instruction(n.TOKEN,bytes([17]),[n.am(self.keys['trader_wsol'],True)])])
        r.clock(8,110000,self.t0+60,'coherent_E8');self.transfer_token('E8_transfer1001','participant-1_htfp','participant-2_htfp',1001,self.participants[0],0)
        r.clock(9,120000,self.open_time-1,'coherent_E9_preopen');r.send('N003_preopen_swap',[self.swap_instruction(False,1000000)],[self.participants[4]],expected_error=6000)
        r.clock(9,120001,self.open_time,'coherent_E9_exact_open');r.cases('N004')
        for a in [1,1001,1000000007]:self.transfer_token('N004_literal_'+str(a),'participant-1_htfp','participant-2_htfp',a,self.participants[0],800)
        self.checked_swap('N004_pool_buy',False,1000000,800);self.checked_swap('N004_pool_sell',True,100000000000000,800)
        r.cases('N005');self.transfer_token('N005_genuine_alpha_inventory','participant-1_htfp','participant-2_htfp',10**17,self.participants[0],800)
        r.cases('N006');self.transfer_token('N006_donation','participant-1_htfp','custody',1001,self.participants[0],800)
        r.default_payer=self.actors['callers'][1];self.recover('N006_Recover_n0',[])
        r.cases('N007');r.default_payer=self.actors['callers'][0];self.recover('N007_batch',['participant-2_htfp','participant-5_htfp','vault1'])
        r.cases('N008');self.recover('N008_retry',['participant-2_htfp','participant-5_htfp','vault1']);self.recover('N008_empty',[]);r.default_payer=None
        self.reject_process('N069',7020,q=16000000008)
        self.snapshot_file('PHASE_PRE_PROCESS_CALIBRATION.json','genuine_exact_calibration_bank')
        return r.snapshot()

    def main_cases(self):
        r=self.r
        cal=self.process('N009',16000000000);self.snapshot_file('PHASE_POST_PROCESS_CALIBRATION.json','global_exact_capacity_processed')
        self.reject_process('N010',7020,q=8)
        r.cases('N070');r.default_payer=self.actors['callers'][1];rec=self.recover('N070_independent_same_slot_pool_tax',['vault1']);r.default_payer=None
        assert rec['expected_from_raw_before']=='800000000';self.snapshot_file('PHASE_SAME_SLOT_RECOVERED.json','subsequent_transaction_same_slot')
        c=r.svm.get_clock();r.clock(9,c.slot+1,c.unix_timestamp+301,'301_seconds_exact_refill')
        self.process('N011',802666664,1);assert self.volume()['credit']==5
        self.reject_process('N012',7020,q=8);self.full_credit_time()
        p=n.pool(self.raw('pool'));x=self.amount('vault1')-sum(int(p[k+'1']) for k in ['protocol','fund','creator']);alpha_q=8*((x//1000)//5+1);assert alpha_q<=self.booked()
        self.reject_process('N013',7020,q=alpha_q)
        for cid,q in [('N014',0),('N015',7),('N016',(self.booked()//8+1)*8),('N017',8)]:self.reject_process(cid,2505 if cid=='N017' else 7006,q=q)
        for row in json.loads((ROOT/'evidence/processing_both/design/MATRIX.json').read_bytes())['cases']:
            if row['phase']!='identity':continue
            cid=row['id'];ix=self.process_ix();metas=list(ix.accounts);decoy=n.Pubkey.new_unique();self.track('decoy_'+cid,decoy);m=metas[row['account_index']];metas[row['account_index']]=n.am(decoy,m.is_writable,m.is_signer)
            self.reject_process(cid,7001,ix=n.instruction(n.H,ix.data,metas))
        for cid,flag in [('N039','signature'),('N040','writable')]:
            ix=self.process_ix(caller=self.actors['callers'][1]);metas=list(ix.accounts);metas[9]=n.am(self.actors['callers'][1].pubkey(),flag!='writable',flag=='writable')
            self.reject_process(cid,7005 if flag=='signature' else 7002,ix=n.instruction(n.H,ix.data,metas),signer_objects=[self.actors['callers'][1]] if flag=='writable' else ())
        for cid,index in [('N041',7),('N042',9)]:
            ix=self.process_ix();metas=list(ix.accounts);metas[index]=n.am(n.RESERVE,True,False);self.reject_process(cid,7003,ix=n.instruction(n.H,ix.data,metas))
        a=self.actors['callers'][0];r.cases('N043');r.send('N043',[self.process_ix()],payer=a,expected_error=7021)
        dummy=n.native_transfer(a.pubkey(),self.keys['caller-1'],1)
        self.reject_process('N044',7022,tail=dummy);self.reject_process('N045',7021,tail=self.finalize_ix(self.volume()['sequence']+2))
        r.cases('N046');r.send('N046',[self.process_ix(),self.finalize_ix(),dummy],payer=a,expected_error=7022)
        for cid,src in [('N047',[]),('N048',['participant-2_htfp'])]:
            r.cases(cid);r.send(cid,[self.process_ix(),self.recover_ix(src),self.finalize_ix()],payer=a,expected_error=7021)
        r.cases('N049');r.send('N049',[self.process_ix(),n.native_transfer(a.pubkey(),self.keys['caller-1'],n.U64_MAX),self.finalize_ix()],payer=a,expected_error=1)
        r.cases('N050');r.send('N050',[n.instruction(n.T22,bytes([26,3,1]),[n.am(self.keys['mint'],True),n.am(self.keys['callerA_htfp'],True),n.am(a.pubkey(),False,True),n.am(self.keys['vault1'],True)])],payer=a,expected_error=4)
        r.cases('N051');r.send('N051',[n.instruction(n.T22,bytes([15])+struct.pack('<QB',8,7),[n.am(self.keys['custody'],True),n.am(self.keys['mint'],True),n.am(a.pubkey(),False,True)])],payer=a,expected_error=4)
        r.cases('N052');r.send('N052',[self.redeem_ix(0,8,self.keys['custody'])],[self.participants[0]],payer=a,expected_error=7003)
        r.cases('N053');r.send('N053',[self.recover_ix(['participant-2_htfp']*2)],payer=a,expected_error=7003)
        r.cases('N054');r.send('N054',[self.recover_ix([],self.keys['callerA_htfp'])],payer=a,expected_error=7001)
        rent=r.svm.minimum_balance_for_rent_exemption(165)
        for j,pfund in enumerate([0,1,rent-1,rent,rent+1]):self.full_credit_time();self.process('N%03d'%(55+j),caller_index=j%3,prefund=pfund)
        self.full_credit_time();r.cases('N060');seq=self.volume()['sequence'];s0=int(n.mint(self.raw('mint'))['supply']);rr=self.booked();reserve0=self.account('reserve').lamports
        row=r.send('N060',[self.process_ix(sequence=seq),self.process_ix(caller=self.actors['callers'][1],sequence=seq+1),self.finalize_ix(seq+1)],[self.actors['callers'][1]],payer=a)
        assert int(n.mint(self.raw('mint'))['supply'])==s0-1200000000 and self.booked()==rr-3200000000 and self.account('reserve').lamports>reserve0 and self.volume()['sequence']==seq+2 and self.raw('inventory')[11]==0
        self.total_process_burn+=1200000000
        r.cases('N062');A=10**17;s=int(n.mint(self.raw('mint'))['supply']);v=max(self.account('reserve').lamports-r.svm.minimum_balance_for_rent_exemption(0),0);payout=v*A//s
        assert A<=self.amount('participant-1_htfp');r.send('N062',[self.redeem_ix(payout+1)],[self.participants[0]],payer=a,expected_error=7009)
        self.full_credit_time();r.cases('N061');seq=self.volume()['sequence'];s=int(n.mint(self.raw('mint'))['supply']);res=self.account('reserve').lamports;mint0=s
        # Derive the Process output from the live raw reserve/liabilities, then exact Redeem minimum.
        pp=n.pool(self.raw('pool'));x=self.amount('vault1')-sum(int(pp[k+'1']) for k in ['protocol','fund','creator']);y=self.amount('vault0')-sum(int(pp[k+'0']) for k in ['protocol','fund','creator']);z=915400000;out=z*y//(x+z)
        v=max(res+out-r.svm.minimum_balance_for_rent_exemption(0),0);pay=v*A//(s-600000000);owner_before=r.svm.get_balance(self.participants[0].pubkey()) or 0;token_before=self.amount('participant-1_htfp')
        r.send('N061',[self.process_ix(),self.redeem_ix(pay),self.finalize_ix()],[self.participants[0]],payer=a)
        assert self.amount('participant-1_htfp')==token_before-A and int(n.mint(self.raw('mint'))['supply'])==s-600000000-A and self.account('reserve').lamports==res+out-pay and (r.svm.get_balance(self.participants[0].pubkey()) or 0)==owner_before+pay
        assert self.volume()['active']==0 and self.raw('inventory')[11]==0;self.total_process_burn+=600000000;self.total_redeem_burn+=A
        r.cases('N063');r.send('N063',[self.finalize_ix()],payer=a)
        r.cases('N064');r.send('N064',[self.finalize_ix(self.volume()['sequence']+2)],payer=a,expected_error=7022)
        self.full_credit_time();ix=self.process_ix();metas=list(ix.accounts);metas[3]=n.am(self.keys['mint']);self.reject_process('N065',7002,ix=n.instruction(n.H,ix.data,metas))
        for cid,why in [('N066','sanitizer writable demotion; source-only readonly guard'),('N067','new immutable binding/default isolation; source-only, no fake state')]:r.coverage[cid]=dict(status='SOURCE_ONLY_NOT_NATIVE',reason=why)
        self.final_report();return cal

    def final_report(self):
        total=0;seen=set();roles=[]
        for role,key in self.keys.items():
            if key in seen or role=='mint':continue
            a=self.r.svm.get_account(key)
            if a is None or a.owner!=n.T22 or len(a.data)<178 or bytes(a.data)[:32]!=bytes(self.keys['mint']):continue
            seen.add(key);total+=int(n.token(bytes(a.data))['amount'])+int(n.token(bytes(a.data))['withheld']);roles.append(role)
        total+=int(n.mint(self.raw('mint'))['withheld']);s=int(n.mint(self.raw('mint'))['supply'])
        assert total==s==n.SUPPLY-self.total_process_burn-self.total_redeem_burn
        assert self.amount('custody')-self.booked()==920 and self.amount('founder_lp')==self.lp_receipt and n.u64(self.raw('lp_mint'),36)==self.lp_receipt
        actual=sum(int(a['lamports']) for a in {v['address']:v for v in self.r.snapshot().values() if v is not None}.values())
        assert actual+self.r.fees==self.initial_tracked_lamports,(actual,self.r.fees,self.initial_tracked_lamports)
        self.r.coverage['N068']=dict(status='RAW_PHASE_AND_CONSERVATION',phase='PHASE_FINAL.json')
        self.snapshot_file('PHASE_FINAL.json','coherent_BothToken_processing_final',total_process_burn=str(self.total_process_burn),total_redeem_burn=str(self.total_redeem_burn),selected_token_roles=roles)
        n.persist(self.r.output/'REPORT.json',dict(schema='HTFP_BOTH_NATIVE_REPORT_V1',status='LOCAL_NATIVE_BOTH_PROCESSING_PASS',stage_acceptance=False,process_proofs=self.process_proofs,total_process_burn=str(self.total_process_burn),total_redeem_burn=str(self.total_redeem_burn),final_R=str(self.booked()),final_C=str(self.amount('custody')),donation_surplus='920',supply=str(s),LP_receipt=str(self.lp_receipt),initial_tracked_lamports=str(self.initial_tracked_lamports),final_tracked_lamports=str(actual),network_fee_lamports=str(self.r.fees),limitations=PROFILE['limitations']+['Remaining unselected newly generated pool withholding is pending, not all final tax cleared','Same-slot positive Process/callbacks/alpha-equalitysuccess remain NOT_RUN per frozenalignment']))


def O_floor(o,z,y,x):return o*(x+z)<=z*y<(o+1)*(x+z)


def main():
    p=argparse.ArgumentParser();p.add_argument('--role',choices=['author','supervisor'],required=True);p.add_argument('--label',required=True);p.add_argument('--build',required=True);args=p.parse_args()
    assert args.label.replace('-','').isalnum()
    fixture,codes,hashes,ata,wsol=n.public_inputs();build=json.loads((ROOT/args.build).read_bytes())
    actors=dict(team=n.Keypair(),marketing=n.Keypair(),participants=[n.Keypair() for _ in range(5)],callers=[n.Keypair() for _ in range(3)])
    keys=[k.pubkey() for k in [actors['team'],actors['marketing'],*actors['participants'],*actors['callers']]];assert len(keys)==len(set(keys))==10 and not(set(keys)&{n.Pubkey.from_string(k['base58']) for k in PROFILE['identities'].values()})
    t0=int(time.time());calibration=None;prestate=None
    for index,mode in enumerate(['main','cu-near-total','cu-32000']):
        label=args.label+'-'+mode;r=Run(ROOT/'evidence/processing_both'/args.role/label,args.role,build)
        try:
            n.persist(r.output/'INPUTS.json',dict(schema='HTFP_BOTH_NATIVE_INPUTS_V1',source_hashes=r.initial_sources,public_inputs=hashes,build_path=args.build,build_sha256=n.sha((ROOT/args.build).read_bytes()),build=build,profile_sha256=n.sha((ROOT/'config/processing-both/profile.json').read_bytes()),processing_binding_sha256=PROCESSING_COMMITMENT,t0=t0,mode=mode,stage_acceptance=False))
            r.create_vm(fixture,codes,ata);s=Scenario(r,actors,t0);state=s.prefix(fixture,wsol)
            n.persist(r.output/'IDENTITIES.json',dict(roles={k:str(v) for k,v in sorted(s.keys.items())},unrelated_callers=[str(k.pubkey()) for k in actors['callers']],ephemeral_secret_exported=False,htfp_side=s.htfp_side))
            if mode=='main':prestate=state;calibration=s.main_cases();status='LOCAL_NATIVE_BOTH_PROCESSING_PASS'
            else:
                assert state==prestate,'fresh genuine full raw prestate differs from calibration'
                cid='CU001' if mode=='cu-near-total' else 'CU002';cu=max(1,calibration['compute_units']-1) if cid=='CU001' else 32000
                r.cases(cid);n.persist(r.output/'PRESTATE_COMPARISON.json',dict(equal=True,compared='all tracked raw accounts inclClock/Rent and identities',calibration_packet_sha256=calibration['transaction_sha256'],calibration_compute_units=calibration['compute_units'],cut_compute_units=cu,positive_state_copy=False))
                row=r.send(cid,[s.process_ix(16000000000),s.finalize_ix()],payer=actors['callers'][0],cu=cu,expected_error='ComputationalBudgetExceeded')
                s.snapshot_file('PHASE_FINAL.json','failed_cut_raw_rollback_not_main_success')
                n.persist(r.output/'REPORT.json',dict(status='LOCAL_NATIVE_CU_ROLLBACK_PASS',case_id=cid,stage_acceptance=False,actual_logs=row['logs'],compute_units=row['compute_units'],limit=cu,calibration_compute_units=calibration['compute_units'],rollback='everytrackedrawaccount exceptactualfee'))
                status='LOCAL_NATIVE_CU_ROLLBACK_PASS'
            assert source_hashes()==r.initial_sources
            r.finish(status);print(json.dumps(dict(status=status,path=str(r.output),VM=r.vms,sends=r.sends)))
        except BaseException as error:
            failure=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());n.persist(r.output/'FAILURE.json',failure);r.finish('RETAINED_NATIVE_FAILURE',failure);print(json.dumps(failure));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())

