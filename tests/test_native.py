import unittest
from experiments.native import simulate

class NativeTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(simulate(2,20,20,7,3,5,10),simulate(2,20,20,7,3,5,10))
    def test_metrics(self):
        data=simulate()
        for f in ('tcp','udp'):
            m=data[f]
            self.assertGreater(m['sent_packets'],0)
            self.assertLessEqual(m['received_packets'],m['sent_packets'])
            self.assertGreaterEqual(m['throughput_kbps'],0)
    def test_bad_inputs(self):
        with self.assertRaises(ValueError): simulate(loss=101)
