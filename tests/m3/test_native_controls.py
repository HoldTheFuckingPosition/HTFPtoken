"""Direct native burns have independent VMs/sources from HTFP positive cases."""
import struct,unittest
from solders.keypair import Keypair
import harness as h
from harness import VM,K,SUPPLY,am,ix,count

class NativeBurnControls(unittest.TestCase):
    def test_isolated_native_multisig_threshold_burns(self):
        for legacy in [False,True]:
            for duplicate_members in [False,True]:
                with self.subTest(legacy=legacy,duplicate_members=duplicate_members):
                    f=VM(self.id()+str((legacy,duplicate_members)))
                    a,b,c=Keypair(),Keypair(),Keypair()
                    members=[a.pubkey(),a.pubkey(),b.pubkey()] if duplicate_members else [a.pubkey(),b.pubkey(),c.pubkey()]
                    multi=f.multisig('direct_multisig',2,members,legacy=legacy)
                    source=f.create_token('direct_source',owner=multi);f.token_transfer(source,10**18)
                    signing=[a] if duplicate_members else [a,b]
                    direct=ix(bytes([15])+struct.pack('<QB',10**17,7),
                        [am(source,w=True),am(K['mint'],w=True),am(multi),*[am(x.pubkey(),s=True) for x in signing]])
                    baseline_failure=legacy and h.NATIVE_FIXTURE.selector=='bundled'
                    f.send('isolated_direct_native_multisig_BurnChecked',[direct],signing,
                        error='MissingRequiredSignature' if baseline_failure else None,index=0 if baseline_failure else None)
                    if baseline_failure:
                        self.assertEqual(f.view('direct_source')['spendable'],10**18)
                        self.assertEqual(f.view('mint')['supply'],SUPPLY)
                        count('isolated_baseline_legacy_native_failures')
                    else:
                        self.assertEqual(f.view('direct_source')['spendable'],9*10**17)
                        self.assertEqual(f.view('mint')['supply'],SUPPLY-10**17)
                        self.assertEqual(f.view('inventory'),{'R':0,'guard':0})
                        count('isolated_native_threshold_burn_successes')
