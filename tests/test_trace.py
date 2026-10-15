import tempfile
import unittest
from pathlib import Path
from analysis.trace import parse_trace

class TraceTests(unittest.TestCase):
    def test_trace_parser(self):
        sample='''+ 1.0 0 2 tcp 1000 ------- 1 0.0 4.0 1 100
r 1.1 3 4 tcp 1000 ------- 1 0.0 4.0 1 100
+ 1.0 1 2 cbr 1000 ------- 2 1.0 5.0 1 101
r 1.2 3 5 cbr 1000 ------- 2 1.0 5.0 1 101
+ 1.3 1 2 cbr 1000 ------- 2 1.0 5.0 2 102
d 1.4 2 3 cbr 1000 ------- 2 1.0 5.0 2 102
'''
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.tr';path.write_text(sample)
            metrics=parse_trace(path)
        self.assertEqual(metrics['tcp']['received_packets'],1)
        self.assertEqual(metrics['udp']['sent_packets'],2)
        self.assertEqual(metrics['udp']['received_packets'],1)
        self.assertEqual(metrics['udp']['delivery_ratio_percent'],50)
        self.assertEqual(metrics['udp']['trace_drop_events'],1)

if __name__=='__main__':unittest.main()
