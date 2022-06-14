from pylse.pylse_exceptions import PylseError
import unittest

from pylse import inp, inp_at, working_circuit, c, m, s, Simulation, Wire, Transitional
try:
    from .test_sfq_cells import delay
except ImportError:
    from test_sfq_cells import delay


class TestSimulation(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_an_input_doesnt_fire(self):
        in0 = inp_at(name='in0')
        in1_times = [1.0, 3.0]
        in1 = inp_at(*in1_times, name='in1')
        in01, in02 = s(in0, transition_time=0)
        in11, in12 = s(in1, transition_time=0)
        mout = m(in01, in11, name='m', transition_time=0)
        _c = c(in02, in12, name='c', transition_time=0)
        d = delay(in01) + delay(mout)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [],
            'in1': in1_times,
            'm': [t + d for t in events['in1']],
            'c': [],
        })

    def test_no_events_no_named_wires(self):
        _in0 = inp(1.2)
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
            "Error while sending input(s) 'a' to the node with output wire 'o':\n"
            "Transition time violation on FSM 'Simple'. Received input 'a' at 3.0 while "
            "still transitioning from idle to s1 on 'a' (transition id '0'). The earliest "
            "it is legal to transition is at time 4.0."
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

    def test_catch_past_constraints(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'a', 'dest': 'a_arrived'},
                {'id': '1', 'source': 'idle', 'trigger': 'b', 'dest': 'idle'},
                {'id': '2', 'source': 'a_arrived', 'trigger': 'b', 'dest': 'idle',
                 'firing': 'q', 'past_constraints': {'a': 3.0}},
                {'id': '3', 'source': 'a_arrived', 'trigger': 'a', 'dest': 'a_arrived'},
            ]
            name = 'Simple'
        atb = Simple()
        ai = inp_at(0.0, name='a')
        bi = inp_at(2.0, name='b')
        o = Wire(name='o')
        working_circuit().add_node(atb, [ai, bi], [o])
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'b' to the node with output wire 'o':\n"
            "Prior input violation on FSM 'Simple'. A constraint on "
            "transition '2', triggered at time 2.0, "
            "given via the 'past_constraints' field says it is an error to "
            "trigger this transition if input 'a' was seen as recently as "
            "3.0 time units ago. It was last seen at 0.0, "
            "which is 1.0 time units to soon."
        )


if __name__ == "__main__":
    unittest.main()
