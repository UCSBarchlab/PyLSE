from pylse.simulation import Simulation
import unittest

from pylse import working_circuit, inspect, inp, Simulation


class TestHelpers(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_inspect_adds_visible_event(self):
        in0 = inp(delay=1.2)
        inspect(in0, 'in0')
        sim = Simulation()
        events = sim.simulate()
        self.assertDictEqual(events, {
            'in0': [1.2],
        })


if __name__ == "__main__":
    unittest.main()
