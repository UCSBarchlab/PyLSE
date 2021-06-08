from pylse.pylse_exceptions import PylseError
import unittest

from pylse import inp, inp_at, working_circuit, c, Simulation, Wire, Transitional


class TestSimulation(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_an_input_doesnt_fire(self):
        in0 = inp_at(1.0, 3.0, name='in0')
        in1 = inp_at(name='in1')
        _c = c(in0, in1, name='c')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [1.0, 3.0],
            'in1': [],
            'c': [],
        })

    def test_no_events_no_named_wires(self):
        _in0 = inp(delay=1.2)
        sim = Simulation()
        events = sim.simulate()
        self.assertDictEqual(events, {})

    def test_input_arrives_during_setup(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 's1', 'transition_time': 4.0},
                {'source': 's1',   'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
            ]
            name = 'Simple'

        i = inp_at(0.0, 3.0)
        o = Wire('o')
        working_circuit().add_node(Simple(), [i], [o])
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending inputs to the node with output wire 'o':\n"
            "Transition time violation. Received input 'a' at 3.0 while still transitioning "
            "from idle to s1 on 'a' (transition id '0'). The earliest it is legal to transition "
            "is at time 4.0."
        )

    def test_normal_sim_with_transition_time(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 's1', 'transition_time': 4.0},
                {'source': 's1',   'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
            ]
            name = 'Simple'
            firing_delay = 1.3
        i = inp_at(0.0, 5.0, name='i')
        o = Wire('o')
        s = Simple()
        working_circuit().add_node(s, [i], [o])
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [0.0, 5.0],
            'o': [6.3],
        })


if __name__ == "__main__":
    unittest.main()
