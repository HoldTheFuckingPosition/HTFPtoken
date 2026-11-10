"""Fixed genuine captured CPMM/ATA/native lifecycle, source-derived exact ABI."""
from runtime import *
NABI=json.loads((ROOT/'config/m4b/native_abi.json').read_text())
def token_amount(a):return struct.unpack_from('<Q',bytes(a.data),64)[0]
def supply(a):return struct.unpack_from('<Q',bytes(a.data),36)[0]
def withheld(a):return m3.token_view(bytes(a.data))['withheld']
class AMM(VM):
 def __init__(self,label,build='build-003',mode='primary'):
  super().__init__(label,build,load_h=True,native_mint=True);self.mode=mode;self.clock(7,4064,1699999970)
  m3.VM.genesis(self);self.send('unchanged_H_initialize',[m3.VM.initialize_ix(self)])
  self.send('native_creator_SOL_funding',[native_transfer(self.i.pubkey(),self.g.pubkey(),10**12)])
  self.ata('creator_wsol','wsol_mint','legacy_token');self.ata('creator_htfp','mint','token2022')
  self.send('native_initial_wrap_100SOL',[native_transfer(self.g.pubkey(),K['creator_wsol'],10**11),ix(K['legacy_token'],bytes([17]),[am(K['creator_wsol'],w=True)])],[self.g])
  self.transfer_htfp(K['genesis_holding'],K['creator_htfp'],10**13,self.g)
  config=NATIVE['raw_config0'];raw=(ROOT/config['path']).read_bytes();self.svm.set_account(K['amm_config'],Account(self.svm.minimum_balance_for_rent_exemption(len(raw)),raw,K['amm']))
  l=self.svm.minimum_balance_for_rent_exemption(165);self.svm.set_account(K['creation_fee_receiver'],Account(l,bytes(165),K['legacy_token']))
  self.events.append(dict(kind='explicit_reviewed_nonmonetary_prestate',config_sha256=sha(raw),config_owner=str(K['amm']),fee_receiver_address=str(K['creation_fee_receiver']),fee_receiver_owner=str(K['legacy_token']),fee_receiver_data_hex=bytes(165).hex(),fee_receiver_rent=l,positive_token_state_injected=False))
  self.send('native_initialize_fixed_fee_receiver',[ix(K['legacy_token'],bytes([18])+bytes(self.g.pubkey()),[am(K['creation_fee_receiver'],w=True),am(K['wsol_mint'])])])
  fee=self.account('creation_fee_receiver');assert token_amount(fee)==0 and fee.lamports==l
  assert self.account('creator_lp') is None
 def ata(self,role,mint,program,owner=None):
  owner=owner or self.g.pubkey();key=K[role]
  expected,bump=Pubkey.find_program_address([bytes(owner),bytes(K[program]),bytes(K[mint])],K['associated_token']);assert key==expected
  self.send('native_ATA_'+role,[ix(K['associated_token'],b'\1',[am(self.i.pubkey(),w=True,s=True),am(key,w=True),am(owner),am(K[mint]),am(K['system']),am(K[program])])])
 def transfer_htfp(self,source,dest,n,owner):
  return self.send('native_HTFP_TransferChecked',[ix(K['token2022'],bytes([12])+struct.pack('<QB',n,7),[am(source,w=True),am(K['mint']),am(dest,w=True),am(owner.pubkey(),s=True)])],[owner])
 def native_instruction(self,name,mapping=None,data=None):
  spec=NABI['instructions'][name];mapping=mapping or {};metas=[]
  for row in spec['accounts']:metas.append(am(mapping.get(row['role'],K.get(row['role'])),row['writable'],row['signer']))
  return ix(K['amm'],bytes.fromhex(spec['primary_data_hex']) if data is None else data,metas)
 def initialize_pool(self):
  data=bytes.fromhex(NABI['instructions']['initialize_v2']['primary_data_hex'])
  mode={'primary':bytes([1,1]),'HTFP_tax_collection':bytes([1,2]),'both_input_fee':bytes([1,0]),'creator_disabled':bytes([0])}[self.mode];data=data[:-2]+mode
  self.initial_lp_before=0;row=self.send('actual_CPMM_InitializeV2_'+self.mode,[self.native_instruction('initialize_v2',data=data)],[self.g]);self.initial_receipt=token_amount(self.account('creator_lp'))
  assert self.initial_receipt==999999999900 and supply(self.account('lp_mint'))==self.initial_receipt
  pool=bytes(self.account('pool').data);assert len(pool)==637 and pool[:8].hex()==NABI['account_discriminators']['PoolState'];assert int.from_bytes(pool[333:341],'little')==10**12
  assert token_amount(self.account('vault_wsol'))==10**11 and token_amount(self.account('vault_htfp'))==10**13
  assert token_amount(self.account('creation_fee_receiver'))==150000000
  assert self.account('creation_fee_receiver').lamports==self.svm.minimum_balance_for_rent_exemption(165)+150000000
  # Subsequent trading inventory: genuine native funds, separate from pool/init LP outcome.
  self.transfer_htfp(K['genesis_holding'],K['creator_htfp'],10**11,self.g)
  self.send('native_later_trader_wrap',[native_transfer(self.g.pubkey(),K['creator_wsol'],10**10),ix(K['legacy_token'],b'\x11',[am(K['creator_wsol'],w=True)])],[self.g]);return row
 def burn_initial(self):
  before=token_amount(self.account('creator_lp'));total=supply(self.account('lp_mint'))
  self.send('actual_exact_initial_LP_receipt_BurnChecked',[ix(K['legacy_token'],bytes([15])+struct.pack('<QB',self.initial_receipt,9),[am(K['creator_lp'],w=True),am(K['lp_mint'],w=True),am(self.g.pubkey(),s=True)])],[self.g])
  assert token_amount(self.account('creator_lp'))==before-self.initial_receipt and supply(self.account('lp_mint'))==total-self.initial_receipt
 def swap_ix(self,htfp_in,n,output=None):
  mapping={'input_authority':self.g.pubkey(),'input_token':K['creator_htfp' if htfp_in else 'creator_wsol'],'output_token':output or K['creator_wsol' if htfp_in else 'creator_htfp'],'input_vault':K['vault_htfp' if htfp_in else 'vault_wsol'],'output_vault':K['vault_wsol' if htfp_in else 'vault_htfp'],'input_token_program':K['token2022' if htfp_in else 'legacy_token'],'output_token_program':K['legacy_token' if htfp_in else 'token2022'],'input_mint':K['mint' if htfp_in else 'wsol_mint'],'output_mint':K['wsol_mint' if htfp_in else 'mint']}
  data=bytes.fromhex(NABI['instructions']['swap_base_input']['anchor_discriminator_hex'])+struct.pack('<QQ',n,0)
  return self.native_instruction('swap_base_input',mapping,data)
 def swap(self,htfp_in,n):return self.send('actual_CPMM_swap_'+('HTFP_in' if htfp_in else 'wSOL_in'),[self.swap_ix(htfp_in,n)],[self.g])
 def collect(self,permissionless=False,expected=None):
  name='collect_creator_fee_permissionless' if permissionless else 'collect_creator_fee'
  return self.send('actual_CPMM_'+name,[self.native_instruction(name)],[self.g] if not permissionless else [],expected=expected)
