"""Exact independently reviewed static zero-supply native mint supplement only."""
import base64,json,struct
from solders.account import Account
from common import ROOT,K,sha,file_sha
SUPPLEMENT='evidence/M4B_WSOL_MINT_FIXTURE_SUPPLEMENT.json'
SUPPLEMENT_SHA='b22c83c421f1a3884cd34e1de4b0e0ff550ccec70f56960f3bfae9e9b537becf'
def install(svm):
 assert file_sha(ROOT/SUPPLEMENT)==SUPPLEMENT_SHA
 d=json.loads((ROOT/SUPPLEMENT).read_text());mint=d['native_mint'];raw=(ROOT/mint['data_path']).read_bytes();record=json.loads((ROOT/mint['account_record_path']).read_text())
 assert len(raw)==82 and sha(raw)==mint['data_sha256'] and raw.hex()==mint['data_hex'];assert raw==base64.b64decode(record['data'][0])
 assert record['owner']==str(K['legacy_token']) and not record['executable'];assert raw[:4]==bytes(4) and raw[46:50]==bytes(4) and struct.unpack_from('<Q',raw,36)[0]==0 and raw[44:46]==bytes([9,1])
 assert svm.get_account(K['wsol_mint']) is None,'Refuse conflicting canonical native mint prestate'
 before={str(K[n]):sha(bytes(svm.get_account(K[n]).data)) for n in ['legacy_token','token2022','amm','associated_token']}
 rent=svm.minimum_balance_for_rent_exemption(82);svm.set_account(K['wsol_mint'],Account(rent,raw,K['legacy_token'],False))
 a=svm.get_account(K['wsol_mint']);assert bytes(a.data)==raw and a.lamports==rent and a.owner==K['legacy_token'] and not a.executable
 after={str(K[n]):sha(bytes(svm.get_account(K[n]).data)) for n in ['legacy_token','token2022','amm','associated_token']};assert before==after
 return dict(kind='static_native_mint_dependency',authority='evidence/M4B_WSOL_MINT_SUPPLEMENT_HANDOFF.md',supplement_sha256=SUPPLEMENT_SHA,constructor_prestate='ABSENT',address=str(K['wsol_mint']),owner=str(a.owner),data_hex=raw.hex(),data_sha256=sha(raw),bytes=82,local_rent_lamports=rent,supply=0,decimals=9,initialized=True,mint_authority=None,freeze_authority=None,public_lamport_balance_copied=False,positive_monetary_state_injected=False,program_hashes_before=before,program_hashes_after=after,provenance={p:file_sha(ROOT/p) for p in [mint['data_path'],mint['account_record_path'],'evidence/m4a/author/DEVNET_CAPTURE.json']})
