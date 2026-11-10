"""Fixed reviewed native fixture selection; no RPC, arbitrary path or fallback."""
import hashlib,json
from pathlib import Path
from solders.pubkey import Pubkey
ROOT=Path(__file__).resolve().parents[2]
BUNDLED_HASH='47181a65d6ee7d7a100480db2efaa21fcfff2be1af49155c30975e9fe5c0c9d6'
CAPTURE_HASH='414f5c53b1cbd15efb6e933c4a1db11d5c65813a08e48baa66ded0ac9be19b91'
CAPTURE_SELECTOR='testnet-capture-462242918'
SELECTORS=('bundled',CAPTURE_SELECTOR)
MANIFEST_HASH='e64e44f7a3f6107cc518aa9676d3dd949457024338cf1d73d63b4f7bcf555ab4'
HANDOFF_HASH='499e25dda8db22feb5bcaeb7f19eda1a903bbd848188dadfeb4f808031cacdf7'
PROPOSAL_HASH='104f97e2ee921525efee4ee4e61c83cf59cc1fe028b174c5ff300d0fe932c0c4'
CODE_PATH='evidence/m3/native_target/token2022_testnet_code_unmodified.so'
HANDOFF_PATH='evidence/m3/native_target/CAPTURE_HANDOFF.json'
SYNTHETIC_OWNER='BPFLoader2111111111111111111111111111111111'
T=Pubkey.from_string('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')
def sha(data):return hashlib.sha256(data).hexdigest()

class FrozenNativeFixture:
    def __init__(self,selector,code,inputs):
        self.selector=selector;self.code=code;self.inputs=dict(inputs)
        self.selected_hash=CAPTURE_HASH if selector==CAPTURE_SELECTOR else BUNDLED_HASH
        self.selected_bytes=691008 if selector==CAPTURE_SELECTOR else 535256
    def unchanged(self):
        return all(sha((ROOT/p).read_bytes())==expected for p,expected in self.inputs.items())
    def describe(self):
        return {'selector':self.selector,'program':str(T),'selected_sha256':self.selected_hash,
            'selected_bytes':self.selected_bytes,'bundled_constructor_sha256':BUNDLED_HASH,
            'synthetic_runtime_owner':SYNTHETIC_OWNER,'source_public_version':'UNKNOWN',
            'public_upgradeable_loader_runtime_equivalence':'NOT_CLAIMED',
            'code_transform':'NONE; full captured region including79952padding bytes',
            'input_sha256':dict(self.inputs)}
    def install(self,svm):
        baseline=svm.get_account(T)
        if not baseline or not baseline.executable or len(baseline.data)!=535256 or sha(bytes(baseline.data))!=BUNDLED_HASH:
            raise ValueError('Constructor bundled Token2022 identity mismatch')
        if str(baseline.owner)!=SYNTHETIC_OWNER:raise ValueError('Unexpected constructor native owner')
        if self.selector==CAPTURE_SELECTOR:
            # Only frozen reviewed raw ELF bytes; never ProgramData metadata or a new fetch.
            svm.add_program(T,self.code)
        loaded=svm.get_account(T)
        if not loaded or not loaded.executable or str(loaded.owner)!=SYNTHETIC_OWNER:
            raise ValueError('Selected local executable/owner mismatch')
        data=bytes(loaded.data)
        if len(data)!=self.selected_bytes or sha(data)!=self.selected_hash:
            raise ValueError('Selected local native bytes/hash mismatch')
        if self.selector==CAPTURE_SELECTOR and data!=self.code:raise ValueError('Captured bytes changed on load')
        return {'selector':self.selector,'bundled_before_sha256':BUNDLED_HASH,
            'loaded_sha256':sha(data),'loaded_bytes':len(data),'actual_synthetic_owner':str(loaded.owner),
            'executable':loaded.executable,'padding_retained':self.selector==CAPTURE_SELECTOR,
            'public_runtime_equivalence':'NOT_CLAIMED'}

def prepare(selector):
    if selector not in SELECTORS:raise ValueError('Unsupported native fixture selector')
    manifest_path='config/m3/native_fixture.json';raw=(ROOT/manifest_path).read_bytes()
    if sha(raw)!=MANIFEST_HASH:raise ValueError('Reviewed native manifest hash mismatch')
    manifest=json.loads(raw);capture=manifest['capture']
    if manifest['schema']!='htfp-m3-fixed-native-fixtures-v1' or manifest['default']!='bundled' or manifest['program']!=str(T):
        raise ValueError('Native manifest schema/default/program mismatch')
    handoff_raw=(ROOT/HANDOFF_PATH).read_bytes()
    if sha(handoff_raw)!=HANDOFF_HASH or capture['capture_handoff_sha256']!=HANDOFF_HASH:
        raise ValueError('Reviewed capture handoff mismatch')
    handoff=json.loads(handoff_raw)
    expected={p:d['sha256'] for p,d in handoff['artifacts_sha256'].items()}
    expected[HANDOFF_PATH]=HANDOFF_HASH
    if capture['inputs_sha256']!=expected or capture['proposal_sha256']!=PROPOSAL_HASH:
        raise ValueError('Capture provenance manifest mismatch')
    # Freeze and hash every provenance input, including the native code, before discovery.
    blobs={}
    for relative,digest in expected.items():
        path=(ROOT/relative).resolve()
        if not path.is_relative_to(ROOT/'evidence/m3/native_target'):raise ValueError('Invalid provenance path')
        data=path.read_bytes()
        if sha(data)!=digest:raise ValueError('Capture provenance changed: '+relative)
        blobs[relative]=data
    code=blobs[CODE_PATH]
    if capture['code_path']!=CODE_PATH or capture['sha256']!=CAPTURE_HASH or capture['bytes']!=691008:
        raise ValueError('Reviewed code identity mismatch')
    if len(code)!=691008 or sha(code)!=CAPTURE_HASH or any(code[-79952:]):raise ValueError('Unmodified captured code/padding mismatch')
    if code!=blobs['evidence/m3/native_target/token2022_programdata.account_data.bin'][45:]:
        raise ValueError('Captured ProgramData/code association mismatch')
    expected[manifest_path]=MANIFEST_HASH
    fixture=FrozenNativeFixture(selector,code,expected)
    if not fixture.unchanged():raise ValueError('Native input race during selection')
    return fixture
