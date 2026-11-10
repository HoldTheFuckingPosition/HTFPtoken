import unittest
from harness import VM,K,R,SUPPLY
class Smoke(unittest.TestCase):
    def test_native_genesis_initialize_redeem(self):
        f=VM(self.id())
        f.fund(R,10_000_000_000)
        f.send('redeem_smoke',[f.redeem_ix(SUPPLY//10)],[f.holder])
        self.assertEqual(f.view('mint')['supply'],SUPPLY-SUPPLY//10)
        self.assertEqual(f.view('inventory'),{'R':0,'guard':0})
