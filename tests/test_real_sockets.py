import unittest
from socket_lab.real_experiment import run_real

class RealSocketsTest(unittest.TestCase):
    def test_baseline(self):
        metrics, events = run_real(0, 0, 20, seed=5)
        for proto in ('tcp', 'udp'):
            self.assertEqual(metrics[proto]['received_packets'], 36)
            self.assertEqual(metrics[proto]['corrupted_packets'], 0)
        self.assertTrue(events)

    def test_full_relay_loss(self):
        metrics, events = run_real(100, 0, 20, seed=5)
        for proto in ('tcp', 'udp'):
            self.assertEqual(metrics[proto]['received_packets'], 0)
            self.assertEqual(metrics[proto]['trace_drop_events'], 36)

    def test_corruption(self):
        metrics, _ = run_real(0, 0, 20, seed=5, corruption=100)
        for proto in ('tcp', 'udp'):
            self.assertEqual(metrics[proto]['received_packets'], 0)
            self.assertEqual(metrics[proto]['corrupted_packets'], 36)

if __name__ == '__main__': unittest.main()
