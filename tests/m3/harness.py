"""Local-only SBF/native harness. No RPC, key files or forged positive money state."""
import base64,hashlib,json,os,struct
from pathlib import Path
from solders.account import Account
from solders.clock import Clock
from solders.instruction import AccountMeta,Instruction
from solders.keypair import Keypair
from solders.litesvm import LiteSVM
from solders.pubkey import Pubkey
from solders.system_program import create_account,create_account_with_seed,transfer as system_transfer
from solders.token.state import Mint,TokenAccount,Multisig
from solders.transaction import Transaction,VersionedTransaction
from solders.message import MessageV0
from solders.transaction_metadata import FailedTransactionMetadata
from solders.address_lookup_table_account import AddressLookupTableAccount

ROOT=Path(__file__).resolve().parents[2]
PROFILE=json.loads((ROOT/'config/m3/local_profile.json').read_text())
K={k:Pubkey.from_string(v['base58']) for k,v in PROFILE['public_keys'].items()}
H,T,SYSTEM,M,R=K['program'],K['token2022'],K['system'],K['mint'],K['reserve']
LEGACY=Pubkey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
SUPPLY=10**19
MAX=(1<<64)-1
NATIVE_HASH='47181a65d6ee7d7a100480db2efaa21fcfff2be1af49155c30975e9fe5c0c9d6'
EVENTS=[]
ARTIFACTS={}
NATIVE_FIXTURE=None
COUNTS={}
def count(name,n=1):COUNTS[name]=COUNTS.get(name,0)+n
def exact(v):
    if type(v) is int:return str(v)
    if isinstance(v,dict):return {str(k):exact(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [exact(x) for x in v]
    return v
def sha(v):return hashlib.sha256(v).hexdigest()
def am(k,s=False,w=False):return AccountMeta(k,s,w)
def ix(data,accounts,program=T):return Instruction(program,bytes(data),accounts)
def opt(k):return b'\0' if k is None else b'\1'+bytes(k)
def fee(amount,bps=800):return (amount*bps+9999)//10000
def tlv(data):
    result={};pos=166
    while pos+4<=len(data):
        if not any(data[pos:]):break
        tag,n=struct.unpack_from('<HH',data,pos);pos+=4
        result[tag]=data[pos:pos+n];pos+=n
    return result
def mint_view(data):
    base=Mint.from_bytes(data[:82]);ext=tlv(data)
    f=ext.get(1,b'')
    return {'supply':base.supply,'decimals':base.decimals,
      'mint_authority':str(base.mint_authority) if base.mint_authority else None,
      'freeze_authority':str(base.freeze_authority) if base.freeze_authority else None,
      'extensions':{str(k):v.hex() for k,v in ext.items()},
      'mint_withheld':int.from_bytes(f[64:72],'little') if len(f)>=108 else None}
def token_view(data):
    base=TokenAccount.from_bytes(data[:165]);ext=tlv(data)
    return {'mint':str(base.mint),'owner':str(base.owner),'spendable':base.amount,
      'withheld':int.from_bytes(ext.get(2,b'\0'*8),'little'),
      'delegate':str(base.delegate) if base.delegate else None,'allowance':base.delegated_amount,
      'close_authority':str(base.close_authority) if base.close_authority else None,
      'extensions':{str(k):v.hex() for k,v in ext.items()}}
def pubtest_signer(which):
    # RFC8032 §7.1 published, deliberately public test inputs, NOT deployment secrets.
    # Only the resulting artificial signer objects exist in memory; never keypair files.
    inputs={
      1:'9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60',
      2:'4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb',
      3:'c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7'}
    return Keypair.from_seed(bytes.fromhex(inputs[which]))

class VM:
    def __init__(self,label,default=False,initialize=True,genesis=True,genesis_options=None,prefund=None):
        self.label=label;self.svm=LiteSVM().with_sigverify(True).with_blockhash_check(True);self.seq=0
        self.initializer=pubtest_signer(1);self.mint_signer=pubtest_signer(2);self.holder=pubtest_signer(3)
        assert self.initializer.pubkey()==K['initializer'] and self.mint_signer.pubkey()==M and self.holder.pubkey()==K['genesis_owner']
        self.tracked={k:v for k,v in K.items() if k not in ['program','token2022','system']}
        self.kinds={k:('mint' if k=='mint' else 'token' if k in ['custody','genesis_holding'] else 'state') for k in self.tracked}
        self.fault_mode=False
        assert NATIVE_FIXTURE is not None and NATIVE_HASH=='47181a65d6ee7d7a100480db2efaa21fcfff2be1af49155c30975e9fe5c0c9d6'
        native_load=NATIVE_FIXTURE.install(self.svm)
        EVENTS.append(exact({'kind':'native_fixture_load','fixture':self.label,**native_load}))
        elf=Path(os.environ['M3_DEFAULT_ELF'] if default else os.environ['M3_ELF'])
        loaded=ARTIFACTS['M3_DEFAULT_ELF' if default else 'M3_ELF']
        self.elf_hash=sha(loaded);self.svm.add_program(H,loaded)
        self.svm.airdrop(self.initializer.pubkey(),20_000_000_000_000)
        assert self.svm.get_balance(self.initializer.pubkey())==20_000_000_000_000
        self.clock(7)
        if genesis:self.genesis(**(genesis_options or {}))
        if prefund:
            for role,lamports in prefund.items():self.fund(K[role],lamports,'prefund_'+role)
        if initialize:self.send('initialize',[self.initialize_ix()],[self.initializer])
    def clock(self,e):
        slot=self.svm.get_epoch_schedule().get_first_slot_in_epoch(e)
        self.svm.warp_to_slot(slot);self.svm.set_clock(Clock(slot,0,e,e,0))
        EVENTS.append(exact({'kind':'synthetic_clock','fixture':self.label,'epoch':e,'slot':slot}))
    def track(self,name,key,kind='token'):
        self.tracked[name]=key;self.kinds[name]=kind
        return key
    def snapshot(self):
        out={}
        for role,k in self.tracked.items():
            a=self.svm.get_account(k)
            if a is None:
                out[role]=None;continue
            data=bytes(a.data)
            row={'address':str(k),'owner':str(a.owner),'lamports':a.lamports,
                 'length':len(data),'data_hex':data.hex(),'data_sha256':sha(data),'executable':a.executable}
            try:
                if role=='inventory' and len(data)==20:
                    row['decoded']={'R':int.from_bytes(data[12:20],'little'),'guard':data[11]}
                elif self.kinds[role]=='mint' and len(data)>=82:row['decoded']=mint_view(data)
                elif self.kinds[role]=='token' and len(data)>=165:row['decoded']=token_view(data)
                elif self.kinds[role]=='multisig' and len(data)==355:
                    row['decoded']={'threshold':data[0],'configured_positions':data[1],'initialized':data[2],
                        'header_valid':data[2]==1 and 1<=data[0]<=data[1]<=11,
                        'members':[str(Pubkey.from_bytes(data[3+i*32:35+i*32])) for i in range(min(data[1],11))]}
            except (ValueError,TypeError) as err:row['decode_error']=str(err)
            out[role]=row
        return out
    def view(self,role):
        return self.snapshot()[role]['decoded']
    def send(self,name,instructions,signers=(),error=None,index=None,versioned=None,allow_failure=False,payer=None):
        payer=payer or self.initializer
        before=self.snapshot();payer_before=self.svm.get_balance(payer.pubkey())
        self.svm.expire_blockhash()
        signing={str(payer.pubkey()):payer}
        signing.update({str(s.pubkey()):s for s in signers})
        if versioned is None:
            tx=Transaction.new_signed_with_payer(instructions,payer.pubkey(),
                    list(signing.values()),self.svm.latest_blockhash())
        else:
            msg=MessageV0.try_compile(payer.pubkey(),instructions,versioned,self.svm.latest_blockhash())
            tx=VersionedTransaction(msg,list(signing.values()))
        size=len(bytes(tx))
        assert size<=1232, f'real packet too large: {size}'
        result=self.svm.send_transaction(tx)
        failed=isinstance(result,FailedTransactionMetadata);meta=result.meta() if failed else result
        after=self.snapshot()
        logs=meta.logs()
        events=[]
        for line in logs:
            if line.startswith('Program data: '):
                raw=base64.b64decode(line.split(': ',1)[1])
                if raw.startswith(b'HTFPEVT1'):events.append(raw.hex())
        e={'kind':'transaction','fixture':self.label,'case':name,'custom_elf_sha256':self.elf_hash,
           'native_fixture':NATIVE_FIXTURE.selector,'native_elf_sha256':NATIVE_FIXTURE.selected_hash,
           'state_provenance':'explicit_adversarial_fault_present' if self.fault_mode else 'native_instruction_created_monetary_state',
           'expected':'SUCCESS' if error is None else {'error':error,'index':index},
           'actual':'FAILURE' if failed else 'SUCCESS','error':str(result.err()) if failed else None,
           'error_instruction':getattr(result.err(),'index',None) if failed else None,
           'packet_bytes':size,'signature':str(meta.signature()),'compute_units':meta.compute_units_consumed(),
           'logs':logs,'htfp_event_hex':events,'before':before,'after':after,
           'payer_address':str(payer.pubkey()),'payer_before':payer_before,'payer_after':self.svm.get_balance(payer.pubkey()),
           'signature_count':len(tx.signatures),'native_transaction_fee_expected':len(tx.signatures)*5000,
           'instructions':[{'program':str(i.program_id),'data_hex':bytes(i.data).hex(),
                           'accounts':[{'key':str(a.pubkey),'signer':a.is_signer,'writable':a.is_writable} for a in i.accounts]} for i in instructions]}
        EVENTS.append(exact(e));self.seq+=1
        if failed:
            # Prove rollback for unexpected failures too, with only actual native fees excluded.
            for role,old in before.items():
                new=after[role]
                if old is not None and old['address']==str(payer.pubkey()):
                    expected=dict(old);expected['lamports']-=len(tx.signatures)*5000
                    assert new==expected,(role,old,new)
                else:assert new==old,(role,old,new)
            EVENTS[-1]['rollback_verified']=True
        if allow_failure:return result,e
        if error is None:
            assert not failed,str(result)
        else:
            assert failed,'expected failure'
            actual=result.err()
            if type(error) is int:assert getattr(getattr(actual,'err',None),'code',None)==error,str(actual)
            else:assert error in str(actual),str(actual)
            if index is not None:assert getattr(actual,'index',None)==index,str(actual)
        return result,e
    def fund(self,k,lamports,name='native_SOL_funding'):
        return self.send(name,[system_transfer({'from_pubkey':self.initializer.pubkey(),'to_pubkey':k,'lamports':lamports})])
    def genesis(self,amount=SUPPLY,bps=800,maximum=MAX,revoke_mint=True,revoke_fee=True,extra_mint=False):
        length=314 if extra_mint else 278
        create=create_account({'from_pubkey':self.initializer.pubkey(),'to_pubkey':M,
           'lamports':self.svm.minimum_balance_for_rent_exemption(length),'space':length,'owner':T})
        initfee=ix(bytes([26,0])+opt(self.initializer.pubkey())+opt(K['tax_authority'])+struct.pack('<HQ',0,maximum),[am(M,w=True)])
        initial=[create,initfee]
        if extra_mint:initial.append(ix(bytes([25])+opt(self.initializer.pubkey()),[am(M,w=True)]))
        initial.append(ix(bytes([20,7])+bytes(self.initializer.pubkey())+opt(None),[am(M,w=True)]))
        self.send('native_create_fee_mint',initial,[self.mint_signer])
        g=K['genesis_holding']
        create=create_account_with_seed({'from_pubkey':self.initializer.pubkey(),'to_pubkey':g,'base':self.initializer.pubkey(),'seed':'m3-local-holder-v1','lamports':self.svm.minimum_balance_for_rent_exemption(178),'space':178,'owner':T})
        self.send('native_genesis_holding',[create,ix(bytes([18])+bytes(self.holder.pubkey()),[am(g,w=True),am(M)])])
        self.send('native_issue_exact_supply',[ix(bytes([14])+struct.pack('<QB',amount,7),[am(M,w=True),am(g,w=True),am(self.initializer.pubkey(),s=True)])])
        schedule=ix(bytes([26,5])+struct.pack('<HQ',bps,maximum),[am(M,w=True),am(self.initializer.pubkey(),s=True)])
        native=[schedule]
        if revoke_fee:native.append(ix(bytes([6,4])+opt(None),[am(M,w=True),am(self.initializer.pubkey(),s=True)]))
        if revoke_mint:native.append(ix(bytes([6,0])+opt(None),[am(M,w=True),am(self.initializer.pubkey(),s=True)]))
        self.send('native_schedule_and_revoke',native)
    def initialize_ix(self,initializer=None,signer=True):
        i=initializer or self.initializer.pubkey()
        return ix(b'HTFP\1\0',[am(K['config'],w=True),am(K['inventory'],w=True),am(M),
              am(K['custody'],w=True),am(K['tax_authority']),am(R),am(K['genesis_holding']),
              am(i,s=signer,w=True),am(T),am(SYSTEM)],H)
    def recover_ix(self,sources=(),count_override=None):
        n=len(sources) if count_override is None else count_override
        return ix(b'HTFP\1\1'+struct.pack('<H',n),[
            am(K['config']),am(K['inventory'],w=True),am(M,w=True),am(K['custody'],w=True),
            am(K['tax_authority']),am(T),*[am(k,w=True) for k in sources]],H)
    def redeem_ix(self,amount,minimum=0,payee=None,source=None,authority=None,signers=(),recipient=None,kind=None,authority_signer=None):
        source=source or K['genesis_holding'];payee=payee or K['genesis_owner'];authority=authority or K['genesis_owner']
        kind=(1 if signers else 0) if kind is None else kind
        s=(kind==0) if authority_signer is None else authority_signer
        return ix(b'HTFP\1\2'+struct.pack('<QQ',amount,minimum)+bytes(recipient or payee)+bytes([kind,len(signers)]),
            [am(K['config']),am(K['inventory'],w=True),am(M,w=True),am(source,w=True),am(R,w=True),
             am(payee,w=True),am(authority,s=s),am(T),am(SYSTEM),*[am(k,s=True) for k in signers]],H)
    def create_token(self,name,owner=None,extensions=(),keypair=None):
        owner=owner or self.holder.pubkey();kp=keypair or Keypair();key=kp.pubkey()
        self.track(name,key)
        length=178+sum(4+({7:0,8:1,11:1,15:1}[x]) for x in extensions)
        create=create_account({'from_pubkey':self.initializer.pubkey(),'to_pubkey':key,'lamports':self.svm.minimum_balance_for_rent_exemption(length),'space':length,'owner':T})
        instructions=[create]
        if 7 in extensions:instructions.append(ix(bytes([22]),[am(key,w=True)]))
        instructions.append(ix(bytes([18])+bytes(owner),[am(key,w=True),am(M)]))
        self.send('native_create_'+name,instructions,[kp])
        return key
    def token_transfer(self,destination,amount,source=None,authority=None,signers=None):
        source=source or K['genesis_holding'];authority=authority or self.holder
        rate=800 if self.svm.get_clock().epoch>=9 else 0
        native=ix(bytes([26,1])+struct.pack('<QBQ',amount,7,fee(amount,rate)),
              [am(source,w=True),am(M),am(destination,w=True),am(authority.pubkey(),s=True)])
        return self.send('native_transfer',[native],[authority] if signers is None else signers)
    def approve(self,source,delegate,amount,owner=None):
        owner=owner or self.holder
        return self.send('native_approve',[ix(bytes([4])+struct.pack('<Q',amount),[am(source,w=True),am(delegate),am(owner.pubkey(),s=True)])],[owner])
    def flag(self,source,extension,enabled,owner=None):
        owner=owner or self.holder
        return self.send('native_account_extension_toggle',[ix(bytes([extension,0 if enabled else 1]),[am(source,w=True),am(owner.pubkey(),s=True)])],[owner])
    def native_burn(self,source,amount,owner=None):
        owner=owner or self.holder
        return self.send('native_external_burn',[ix(bytes([15])+struct.pack('<QB',amount,7),[am(source,w=True),am(M,w=True),am(owner.pubkey(),s=True)])],[owner])
    def mutate(self,role,mutator,explanation):
        key=self.tracked[role];a=self.svm.get_account(key);data=bytearray(a.data)
        mutator(data)
        self.svm.set_account(key,Account(a.lamports,bytes(data),a.owner,a.executable,a.rent_epoch))
        self.fault_mode=True
        EVENTS.append(exact({'kind':'explicit_non_native_fault_injection','fixture':self.label,'role':role,'explanation':explanation,'bytes_before_sha256':sha(bytes(a.data)),'bytes_after_sha256':sha(data)}))
    def set_lamports_fault(self,role,lamports,explanation):
        a=self.svm.get_account(self.tracked[role])
        self.svm.set_account(self.tracked[role],Account(lamports,bytes(a.data),a.owner,a.executable,a.rent_epoch))
        self.fault_mode=True
        EVENTS.append(exact({'kind':'explicit_adversarial_lamport_fault','fixture':self.label,'role':role,'lamports':lamports,'explanation':explanation}))

    def inject_account(self,role,data,owner,lamports,explanation):
        self.svm.set_account(self.tracked[role],Account(lamports,bytes(data),owner))
        self.fault_mode=True
        EVENTS.append(exact({'kind':'explicit_adversarial_account_fault','fixture':self.label,
           'role':role,'owner':str(owner),'lamports':lamports,'explanation':explanation,'data_sha256':sha(bytes(data))}))

    def multisig(self,name,m,members,legacy=False,keypair=None):
        kp=keypair or Keypair();key=kp.pubkey();self.track(name,key,'multisig')
        program=LEGACY if legacy else T
        create=create_account({'from_pubkey':self.initializer.pubkey(),'to_pubkey':key,
          'lamports':self.svm.minimum_balance_for_rent_exemption(355),'space':355,'owner':program})
        initialize=ix(bytes([19,m]),[am(key,w=True),*[am(k) for k in members]],program)
        self.send('native_initialize_multisig_'+name,[create,initialize],[kp])
        return key
    def lookup_table(self,addresses):
        from solders.system_program import create_lookup_table,extend_lookup_table
        from solders.address_lookup_table_account import AddressLookupTable
        from solders.sysvar import SLOT_HASHES
        slot_hashes=SLOT_HASHES
        raw=bytes(self.svm.get_account(slot_hashes).data)
        recent=struct.unpack_from('<Q',raw,8)[0]
        create,key=create_lookup_table({'authority_address':self.initializer.pubkey(),
          'payer_address':self.initializer.pubkey(),'recent_slot':recent})
        self.send('native_create_lookup_table',[create])
        for offset in range(0,len(addresses),16):
            self.send('native_extend_lookup_table',[extend_lookup_table({
              'payer_address':self.initializer.pubkey(),'lookup_table_address':key,
              'authority_address':self.initializer.pubkey(),'new_addresses':addresses[offset:offset+16]})])
        clock=self.svm.get_clock()
        self.svm.warp_to_slot(clock.slot+1)
        clock.slot+=1;self.svm.set_clock(clock)
        actual=AddressLookupTable.deserialize(bytes(self.svm.get_account(key).data))
        assert list(actual.addresses)==list(addresses)
        return AddressLookupTableAccount(key,list(actual.addresses))
