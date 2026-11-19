"""Focused LOCAL tests for the proposed Devnet processor; no network or existing keys."""
import base64,hashlib,importlib.metadata,json,math,struct
from pathlib import Path
from solders.account import Account
from solders.clock import Clock
from solders.compute_budget import set_compute_unit_limit
from solders.instruction import AccountMeta,Instruction
from solders.keypair import Keypair
from solders.litesvm import LiteSVM
from solders.message import Message
from solders.pubkey import Pubkey
from solders.rent import Rent
from solders.signature import Signature
from solders.system_program import transfer
from solders.transaction import Transaction
from solders.transaction_metadata import FailedTransactionMetadata
from oracle import amount,token,volume,check_batch,check_rollback,check_recover
ROOT=Path(__file__).resolve().parents[3]
FIXTURE_ROOT=ROOT
PROFILE='config/devnet-processor/PROFILE.json'
ABI='config/devnet-processor/ABI.json'
STATE='evidence/devnet_processor_upgrade/read-001/STATE.json'
PARTICIPANTS='evidence/devnet_processor_upgrade/read-003/RESULT.json'
SYSVARS='evidence/devnet_processor_upgrade/read-004/RESULT.json'
PINS={'config/devnet-processor/PROFILE.json': '8671afc989c121053f9bdf40983a8885939b1ba74aa54df58efbae8082075eeb', 'config/devnet-processor/ABI.json': '2d404a6be5e526b10b16a46fc59ce617f48fb4959d4b36bd2964bb67e7a647d2', 'evidence/devnet_processor_upgrade/read-001/STATE.json': '345fb91868316ef6a1bd9451c0a7ea97373adeb80344d06f528e51fdb5d7e9fa', 'evidence/devnet_processor_upgrade/read-001/RESULT.json': 'c11ff27bc67e9fe74b6a0a3563d23b58e10c656bde77a5ad18592b4485665353', 'evidence/devnet_processor_upgrade/read-003/RESULT.json': 'b0ee1224c3e98328ddd17c1c918cbf250f797a50328745a76e3d6b2b87d0cfa2', 'evidence/devnet_processor_upgrade/read-004/RESULT.json': '05b5ab889220ccccc207c5b23476c5e6676ebe7c935f748fe59bedddff6b4b7e', 'evidence/devnet_processor_upgrade/read-001/token2022.so': 'b781b71d230a9910de4d3c103e72608f597fc73c83ee207242ac82b708382a6a', 'evidence/devnet_processor_upgrade/read-001/amm.so': '30a9273dda17d7b3513889af1dab1185d9facc4756a6edf36c42f30ba228d8d1', 'evidence/devnet_processor_upgrade/read-001/legacy_token.so': '8190d3f7ceb6cb7a7a8d8924bff89f9f611e15ce1f806f2b6237f3311a98f697'}
NATIVE_RUNTIME_SHA='648e13d02ec2e8555d751e38980e01faa5cbb47c2e7d7262f3a2103caa3afa02'
SYSTEM=Pubkey.from_string('11111111111111111111111111111111')
NATIVE_FILES={name:'evidence/devnet_processor_upgrade/read-001/'+name+'.so'for name in ('token2022','amm','legacy_token')}
Q=1_600_000_000_000_000
def sha(raw):return hashlib.sha256(raw).hexdigest()


def strict(raw):
    def pairs(items):
        result={}
        for key,value in items:assert key not in result;result[key]=value
        return result
    def finite(text):
        value=float(text);assert math.isfinite(value);return value
    return json.loads(raw,object_pairs_hook=pairs,parse_float=finite,parse_constant=lambda text:(_ for _ in ()).throw(ValueError(text)))

def public(path):
    p=Path(path);assert not p.is_absolute() and '..'not in p.parts
    full=(FIXTURE_ROOT if p.parts[0]=='evidence' else ROOT)/p
    for parent in (full,*full.parents):assert not parent.is_symlink()
    return full

def pinned(path,digest):
    raw=public(path).read_bytes();assert sha(raw)==digest,(path,'HASH')
    return raw

def account_record(key,account):
    if account is None:return None
    return {'address':str(key),'owner':str(account.owner),'executable':account.executable,'lamports':str(account.lamports),'data_hex':bytes(account.data).hex()}

def am(key,w=False,s=False):return AccountMeta(key,s,w)

def ix(key,data,accounts):return Instruction(key,bytes(data),accounts)

class VM:
    def __init__(self,run):
        self.run=run;run.resources();assert run.vms<2;run.vms+=1;run.journal('VM_ATTEMPT_STARTED',ordinal=run.vms)
        self.profile=strict(pinned(PROFILE,PINS[PROFILE]));self.abi=strict(pinned(ABI,PINS[ABI]));self.k={n:Pubkey.from_string(v['base58'])for n,v in self.profile['identities'].items()}
        self.svm=LiteSVM().with_sigverify(False).with_blockhash_check(True).with_log_bytes_limit(None);self.phase='SETUP_SIGVERIFY_DISABLED';self.tracked={};self.programs={}
        for package,version in (('solders','0.26.0'),('jsonalias','0.1.1'),('typing_extensions','4.16.0')):assert importlib.metadata.version(package)==version
        snapshot=strict(pinned(STATE,PINS[STATE]));people=strict(pinned(PARTICIPANTS,PINS[PARTICIPANTS]));sysvars=strict(pinned(SYSVARS,PINS[SYSVARS]))
        skip={'program','programdata','token2022','amm','legacy_token'}
        self.k.update({n:Pubkey.from_string(k)for n,k in people['keys'].items()if n in ('participant1','participant2','participant1_htfp','participant2_htfp')})
        self.k.update({n:Pubkey.from_string(k)for n,k in sysvars['keys'].items()})
        for group in (snapshot['accounts'],{n:people['accounts'][n]for n in ('participant1','participant2','participant1_htfp','participant2_htfp')},sysvars['accounts']):
            for role,a in group.items():
                if role in skip:continue
                assert role in self.k,('UNKNOWN_CAPTURE_ROLE',role)
                key=self.k[role];self.track(role,key)
                if a is not None:
                    raw=base64.b64decode(a['data'][0],validate=True);assert a['executable']is False
                    self.host('CURRENT_CAPTURE_IMPORT',key,Account(a['lamports'],raw,Pubkey.from_string(a['owner']),False,a['rentEpoch']))
        rent_raw=base64.b64decode(sysvars['accounts']['rent']['data'][0],validate=True)
        clock_raw=base64.b64decode(sysvars['accounts']['clock']['data'][0],validate=True)
        self.svm.set_rent(Rent.from_bytes(rent_raw));self.svm.set_clock(Clock.from_bytes(clock_raw))
        assert bytes(self.svm.get_rent())==rent_raw and bytes(self.svm.get_clock())==clock_raw
        quotes=strict(pinned('evidence/devnet_processor_upgrade/read-001/RESULT.json',PINS['evidence/devnet_processor_upgrade/read-001/RESULT.json']))['rents']
        assert all(self.svm.minimum_balance_for_rent_exemption(int(size))==n for size,n in quotes.items())
        run.emit({'kind':'captured_sysvars_installed','rent_hex':rent_raw.hex(),'clock_hex':clock_raw.hex(),'actual_rent':json.loads(self.svm.get_rent().to_json()),'synthetic_clock_warp_follows':True})
        for name,path in NATIVE_FILES.items():self.load(name,self.k[name],pinned(path,PINS[path]))
        self.load('program',self.k['program'],run.elf)
        self.actors=[Keypair.from_seed(hashlib.sha256(('HTFP_DEVNET_PROCESSOR_LOCAL_TEST_'+str(i)).encode()).digest())for i in range(2)]
        assert len({v.pubkey()for v in self.actors})==2 and not({v.pubkey()for v in self.actors}&set(self.k.values()))
        for i,a in enumerate(self.actors):self.track('caller'+str(i),a.pubkey());self.host('SYNTHETIC_LOCAL_CALLER_FUNDING',a.pubkey(),Account(2_000_000_000,b'',SYSTEM))
        self.track('instructions_sysvar',self.k['instructions_sysvar']);self.track('volume',self.k['volume']);self.track('settle_authority',self.k['settle_authority'])
        assert self.raw('config')[:8]==b'HTFPCFG1'and len(self.raw('config'))==175 and len(self.raw('inventory'))==20 and self.raw('inventory')[11]==0
        assert amount(self.raw('inventory'),12)==0 and token(self.raw('custody'))==(0,0)and len(self.raw('mint'))==459
        assert token(self.raw('vault_htfp'))[0]==3_500_000_000_000_000_000 and token(self.raw('vault_wsol'))[0]==8_800_000_000
        assert self.svm.get_account(self.k['volume'])is None
        self.warp(1210,1794801601)
        run.emit({'kind':'vm_ready','programs':self.programs,'actors':[str(v.pubkey())for v in self.actors],'current_core_snapshot_slot':snapshot['context']['slot'],'participant_snapshot_slot':people['context']['slot'],'sysvar_snapshot_slot':sysvars['context']['slot'],'public_upgrade_equivalence':False})
    def load(self,role,key,raw):
        self.svm.add_program(key,raw);a=self.svm.get_account(key);assert a is not None and a.executable and bytes(a.data)==raw
        self.programs[role]={'address':str(key),'bytes':len(raw),'sha256':sha(raw),'current_capture':role!='program'}
    def track(self,role,key):self.tracked[role]=key
    def host(self,reason,key,account):
        before=account_record(key,self.svm.get_account(key));self.svm.set_account(key,account);self.run.emit({'kind':'host_fixture_mutation','reason':reason,'address':str(key),'before':before,'after':account_record(key,self.svm.get_account(key))})
    def raw(self,role):return bytes(self.svm.get_account(self.k[role]).data)
    def state(self):return volume(self.raw('volume'))
    def warp(self,epoch,unix):
        old=json.loads(self.svm.get_clock().to_json());slot=max(self.svm.get_clock().slot+1,epoch*432000+1);self.svm.warp_to_slot(slot);self.svm.set_clock(Clock(slot,unix,epoch,epoch,unix))
        self.run.emit({'kind':'ARTIFICIAL_LOCAL_CLOCK','before':old,'after':json.loads(self.svm.get_clock().to_json()),'not_network_time_evidence':True})
    def verified(self):self.svm.with_sigverify(True);self.phase='VERIFIED_LOCAL';self.run.emit({'kind':'verified_phase_started','public_keys':[str(v.pubkey())for v in self.actors]})
    def snapshot(self):return {role:account_record(key,self.svm.get_account(key))for role,key in self.tracked.items()}
    def temp(self,seq=None):
        seq=self.state()['sequence']if seq is None else seq;key,_=Pubkey.find_program_address([b'htfp-tmp-wsol',bytes(self.k['mint']),struct.pack('<Q',seq)],self.k['program']);self.track('temp_'+str(seq),key);return key
    def operation(self,tag,payload=b'',caller=0,seq=None):
        roles={**self.k,'storage_payer':self.actors[caller].pubkey()}
        if tag==3:roles['temp_sequence']=self.temp(seq)
        return ix(self.k['program'],b'HTFP\x01'+bytes([tag])+payload,[am(roles[m['role']],m['writable'],m['signer'])for m in self.abi['wire'][str(tag)]['accounts']])
    def process(self,q,caller=0,seq=None):return self.operation(3,struct.pack('<Q',q),caller,seq)
    def fence(self,nonce=None):return self.operation(5,struct.pack('<Q',self.state()['sequence']+1 if nonce is None else nonce))
    def recover(self,sources):
        return ix(self.k['program'],b'HTFP\x01\x01'+struct.pack('<H',len(sources)),[am(self.k['config']),am(self.k['inventory'],True),am(self.k['mint'],True),am(self.k['custody'],True),am(self.k['tax_authority']),am(self.k['token2022'])]+[am(x,True)for x in sources])
    def transfer_token(self,destination,amount):
        return ix(self.k['token2022'],b'\x0c'+struct.pack('<Q',amount)+b'\x07',[am(self.k['participant1_htfp'],True),am(self.k['mint']),am(destination,True),am(self.k['participant1'],False,True)])
    def send(self,name,instructions,expect=None,payer=0):
        self.run.resources();assert self.run.txs<64
        self.track('fee_payer',self.actors[payer].pubkey())
        for instruction in instructions:
            for m in instruction.accounts:
                if m.is_signer:assert m.pubkey.is_on_curve(),'NO_PDA_TOP_LEVEL_SIGNATURE'
        self.svm.expire_blockhash();operations=[set_compute_unit_limit(1_400_000),*instructions]
        if self.phase=='VERIFIED_LOCAL':
            needed={m.pubkey for ins in instructions for m in ins.accounts if m.is_signer}|{self.actors[payer].pubkey()};signers=[a for a in self.actors if a.pubkey()in needed];assert {a.pubkey()for a in signers}==needed
            tx=Transaction.new_signed_with_payer(operations,self.actors[payer].pubkey(),signers,self.svm.latest_blockhash());assert all(tx.verify_with_results())
        else:
            assert all(i.program_id==self.k['token2022']for i in instructions),'SETUP_HAS_NO_H'
            message=Message.new_with_blockhash(operations,self.actors[payer].pubkey(),self.svm.latest_blockhash());fake=[Signature.from_bytes(hashlib.sha512(bytes(message)+struct.pack('<I',i)).digest())for i in range(message.header.num_required_signatures)];tx=Transaction.populate(message,fake)
        packet=bytes(tx);assert len(packet)<=1232;before=self.snapshot();self.run.txs+=1;self.run.journal('TX_ATTEMPT_STARTED',ordinal=self.run.txs,name=name,phase=self.phase,wire_sha256=sha(packet))
        result=self.svm.send_transaction(tx);failed=isinstance(result,FailedTransactionMetadata);meta=result.meta()if failed else result;after=self.snapshot();fee=5000*len(tx.signatures)
        row={'kind':'transaction','name':name,'ordinal':self.run.txs,'phase':self.phase,'before':before,'after':after,'payer':str(self.actors[payer].pubkey()),'fee_lamports':str(fee),'status':'FAILURE'if failed else'SUCCESS','error':str(result.err())if failed else None,'expected_error':expect,'packet_hex':packet.hex(),'packet_sha256':sha(packet),'message_hex':bytes(tx.message).hex(),'message_sha256':sha(bytes(tx.message)),'signatures':[str(v)for v in tx.signatures],'signature_verification':self.phase=='VERIFIED_LOCAL','blockhash_verification':True,'instructions':[{'program_id':str(i.program_id),'data_hex':bytes(i.data).hex(),'accounts':[{'pubkey':str(m.pubkey),'is_signer':m.is_signer,'is_writable':m.is_writable}for m in i.accounts]}for i in operations],'logs':meta.logs(),'inner_instructions':[[json.loads(i.to_json())for i in group]for group in meta.inner_instructions()],'compute_units':meta.compute_units_consumed(),'actual_clock':json.loads(self.svm.get_clock().to_json()),'actual_rent':json.loads(self.svm.get_rent().to_json()),'programs':self.programs}
        self.run.emit(row);self.run.coverage.append({'name':name,'ordinal':self.run.txs,'status':row['status'],'packet_sha256':row['packet_sha256']});self.run.journal('TX_ATTEMPT_COMPLETED',ordinal=self.run.txs,name=name,status=row['status'])
        if failed:
            check_rollback(row);assert expect is not None
            if type(expect)is int:assert getattr(getattr(result.err(),'err',None),'code',None)==expect
            elif expect!='FAIL':assert expect in row['error']
        else:assert expect is None
        return row
