"""New isolated native adapter. Frozen helpers imported, never monkeypatched."""
from pathlib import Path
import gzip
import hashlib
import json
import os
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
FROZEN = {
    'tests/lge_pool/native_adapter.py': '8af4335544daf41cdb7997208ea85ef10055d41319c63e95d3177056fcc86c85',
    'tests/lge_pool/native_rehearsal.py': '05774d26766e96b4b57278cd7d1bbb559691359d5219f819e4ce0d100402f167',
    'tests/fee_lifecycle/native_flow.py': '13290c399915bff605a9861f591ca2c87239f3b9072699fe7fefa940183142ce',
}
for p, h in FROZEN.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
sys.path.insert(0,str(ROOT/'tests/fee_lifecycle'))
import native_flow as fee
n, lge = fee.n, fee.lge
from build import resources


def source_hashes():
    paths=list(FROZEN)
    for base in ['programs/htfp-both','config/processing-both','tests/processing_both']:
        paths += [p.relative_to(ROOT).as_posix() for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    return {p:n.sha((ROOT/p).read_bytes()) for p in sorted(paths)}


class Run(n.NativeRun):
    def __init__(self, output, role, build):
        self.role,self.output,self.build=role,Path(output),build
        base=ROOT/'evidence/processing_both'/role
        assert role in ('author','supervisor') and self.output.parent==base and not self.output.exists()
        base.mkdir(exist_ok=True)
        vm=sends=0;prior_summaries=[]
        for prior in sorted(base.glob('*/CASE_LEDGER.jsonl')):
            rows=[json.loads(line) for line in prior.read_text().splitlines()]
            assert rows and rows[0]['event']=='RUN_STARTED' and rows[-1]['event']=='RUN_FINISHED',str(prior)
            assert sum(x['event']=='RUN_STARTED' for x in rows)==sum(x['event']=='RUN_FINISHED' for x in rows)==1
            active_send=None;active_vm=False;ordinal=rows[0]['prior_sends'];vm_count=send_count=0
            for row in rows:
                if row['event']=='VM_ATTEMPT_STARTED':assert not active_vm;active_vm=True;vm_count+=1
                elif row['event']=='VM_CONSTRUCTED':assert active_vm;active_vm=False
                elif row['event']=='SEND_ATTEMPT_STARTED':
                    assert not active_vm and active_send is None and row['ordinal']==ordinal+1
                    ordinal=row['ordinal'];active_send=(ordinal,row['packet_sha256']);send_count+=1
                elif row['event']=='SEND_ATTEMPT_COMPLETED':assert active_send==(row['ordinal'],row['packet_sha256']);active_send=None
            assert not active_vm and active_send is None,'unmatched prior VM/send attempt'
            assert rows[-1]['actual_vm_attempts']==vm_count and rows[-1]['explicit_signed_send_attempts']==send_count
            prior_summaries.append((rows[0]['prior_vm'],rows[0]['prior_sends'],vm_count,send_count))
            vm+=sum(row['event']=='VM_ATTEMPT_STARTED' for row in rows);sends+=sum(row['event']=='SEND_ATTEMPT_STARTED' for row in rows)
        expected_vm=expected_sends=0
        for pv,ps,vc,sc in sorted(prior_summaries):
            assert (pv,ps)==(expected_vm,expected_sends),'prior role counter gap/reset'
            expected_vm+=vc;expected_sends+=sc
        assert (expected_vm,expected_sends)==(vm,sends)
        assert vm<6 and sends<400
        self.prior_vm,self.prior_send=vm,sends
        self.vms=self.sends=self.synthetic_airdrop_calls=self.fees=0
        self.sequence=self.event_count=0;self.tracked={};self.finished=False;self.case_ids=[];self.default_payer=None
        self.output.mkdir();self.journal=(self.output/'CASE_LEDGER.jsonl').open('xb')
        self.event_file=(self.output/'events.jsonl.gz').open('xb');self.compressor=gzip.GzipFile(filename='',mode='wb',fileobj=self.event_file,mtime=0)
        self.initial_sources=source_hashes();self.coverage={}
        self.append('RUN_STARTED',source_hashes=self.initial_sources,resources=resources(),prior_vm=vm,prior_sends=sends)
        for p,h in self.initial_sources.items():
            dest=self.output/'source'/p;dest.parent.mkdir(parents=True,exist_ok=True)
            assert n.sha((ROOT/p).read_bytes())==h
            with dest.open('xb') as f:f.write((ROOT/p).read_bytes())

    def source_hashes(self):return source_hashes()

    def cases(self,*ids):self.case_ids=list(ids)

    def create_vm(self,fixture,codes,ata_bytes):
        assert self.prior_vm+self.vms<6
        self.append('VM_ATTEMPT_STARTED',ordinal=self.prior_vm+self.vms+1,resources=resources());self.vms+=1
        self.svm=n.LiteSVM().with_sigverify(True).with_blockhash_check(True)
        self.programs={}
        for label,key in [('CPMM',n.AMM),('Token2022',n.T22),('legacyToken',n.TOKEN)]:
            self.svm.add_program(key,codes[label]);a=self.svm.get_account(key)
            assert a is not None and a.executable and bytes(a.data)==codes[label]
            self.programs[label]=dict(program=str(key),owner=str(a.owner),bytes=len(a.data),sha256=n.sha(bytes(a.data)))
        a=self.svm.get_account(n.ATA);assert a is not None and a.executable and bytes(a.data)==ata_bytes
        self.programs['ATA']=dict(program=str(n.ATA),owner=str(a.owner),bytes=len(a.data),sha256=n.sha(bytes(a.data)))
        assert self.svm.get_account(n.H) is None
        spec=self.build['artifact'];raw=(ROOT/spec['path']).read_bytes();assert len(raw)==spec['bytes'] and n.sha(raw)==spec['sha256']
        assert self.build['feature']=='local-both' and self.build['exit_status']==0 and self.build['source_unchanged']
        for p,h in self.build['inputs_before_sha256'].items():assert n.sha((ROOT/p).read_bytes())==h
        self.append('H_LOAD_PROSPECTIVE',artifact=spec,source_inputs=self.build['inputs_before_sha256'])
        self.svm.add_program(n.H,raw);a=self.svm.get_account(n.H);assert a is not None and a.executable and bytes(a.data)==raw
        self.programs['H']=dict(program=str(n.H),owner=str(a.owner),bytes=len(a.data),sha256=n.sha(bytes(a.data)),feature='local-both',build_source_inputs=self.build['inputs_before_sha256'])
        self.emit(dict(kind='post_load_getters',programs=self.programs,H_present=True,loader=fixture['loader'],public_runtime_equivalence='NOT_CLAIMED'))
        self.append('VM_CONSTRUCTED',programs=self.programs,H_present=True)

    def send(self,name,instructions,signer_objects=(),expected_error=None,payer=None,cu=1400000):
        resources();assert self.prior_send+self.sends<400 and 0<cu<=1400000
        payer=payer or self.default_payer or self.operations
        before=self.snapshot();self.svm.expire_blockhash();blockhash=self.svm.latest_blockhash()
        signers={str(payer.pubkey()):payer};signers.update({str(k.pubkey()):k for k in signer_objects})
        tx=n.Transaction.new_signed_with_payer([n.set_compute_unit_limit(cu),*instructions],payer.pubkey(),list(signers.values()),blockhash)
        packet=bytes(tx);assert len(packet)<=1232 and all(tx.verify_with_results())
        ixrows=[dict(program_id=str(ix.program_id),data_hex=bytes(ix.data).hex(),accounts=[dict(pubkey=str(m.pubkey),is_signer=m.is_signer,is_writable=m.is_writable) for m in ix.accounts]) for ix in instructions]
        self.append('SEND_ATTEMPT_STARTED',ordinal=self.prior_send+self.sends+1,name=name,case_ids=self.case_ids,packet_sha256=n.sha(packet),packet_bytes=len(packet),expected_error=expected_error,resources=resources(),source_hashes=source_hashes());self.sends+=1
        answer=self.svm.send_transaction(tx);failed=isinstance(answer,n.FailedTransactionMetadata);meta=answer.meta() if failed else answer
        after=self.snapshot();fee_lamports=len(tx.signatures)*5000;self.fees+=fee_lamports
        row=dict(kind='transaction',name=name,case_ids=list(self.case_ids),ordinal=self.prior_send+self.sends,status='FAILURE' if failed else 'SUCCESS',expected_error=expected_error,error=str(answer.err()) if failed else None,
                 transaction_hex=packet.hex(),transaction_sha256=n.sha(packet),packet_bytes=len(packet),message_hex=bytes(tx.message).hex(),message_sha256=n.sha(bytes(tx.message)),recent_blockhash=str(blockhash),signatures=[str(s) for s in tx.signatures],signature_verification=tx.verify_with_results(),compute_unit_limit=cu,compute_units=meta.compute_units_consumed(),network_fee_expected_lamports=str(fee_lamports),payer=str(payer.pubkey()),instructions=ixrows,logs=meta.logs(),inner_instructions=[[json.loads(inner.to_json()) for inner in group] for group in meta.inner_instructions()],before=before,after=after,program_hashes=self.programs)
        self.emit(row)
        for cid in self.case_ids:self.coverage.setdefault(cid,[]).append(dict(ordinal=row['ordinal'],packet_sha256=row['transaction_sha256'],status=row['status']))
        self.append('SEND_ATTEMPT_COMPLETED',ordinal=row['ordinal'],name=name,case_ids=self.case_ids,status=row['status'],error=row['error'],packet_sha256=row['transaction_sha256'],compute_units=row['compute_units'])
        assert row['compute_units']<=cu
        if failed:
            for role,old in before.items():
                want=old
                if old is not None and old['address']==str(payer.pubkey()):want=dict(old,lamports=str(int(old['lamports'])-fee_lamports))
                assert after[role]==want,('rollback',name,role)
            assert expected_error is not None,row['error']
            if type(expected_error) is int:assert getattr(getattr(answer.err(),'err',None),'code',None)==expected_error,row['error']
            else:assert expected_error in row['error'],row['error']
        else:assert expected_error is None,(name,'unexpected success')
        return row

    def finish(self,status,error=None):
        if self.finished:return
        self.finished=True;self.compressor.close();self.event_file.flush();os.fsync(self.event_file.fileno());self.event_file.close()
        stored=(self.output/'events.jsonl.gz').read_bytes();raw=gzip.decompress(stored)
        rec=dict(schema='HTFP_BOTH_NATIVE_RESULT_V1',status=status,error=error,role=self.role,actual_vm_attempts=self.vms,explicit_signed_send_attempts=self.sends,synthetic_airdrop_API_calls=self.synthetic_airdrop_calls,prior_role_vm_attempts=self.prior_vm,prior_role_send_attempts=self.prior_send,role_cumulative_vm_attempts=self.prior_vm+self.vms,role_cumulative_send_attempts=self.prior_send+self.sends,network_fees_expected_lamports=str(self.fees),events=dict(path=(self.output/'events.jsonl.gz').relative_to(ROOT).as_posix(),stored_bytes=len(stored),stored_sha256=n.sha(stored),raw_bytes=len(raw),raw_sha256=n.sha(raw),rows=self.event_count),source_hashes_after=source_hashes(),resources=resources(),stage_acceptance=False)
        assert source_hashes()==self.initial_sources
        n.persist(self.output/'events.jsonl.gz.FORMAT.json',dict(schema='HTFP_BOTH_LOSSLESS_EVENTS_V1',compression='gzip',raw_encoding='UTF8 JSONL compact sorted keys LF',**rec['events']))
        n.persist(self.output/'COVERAGE.json',self.coverage);n.persist(self.output/'RESULT.json',rec);self.append('RUN_FINISHED',**rec);self.journal.close()
