from collections import defaultdict
import unittest

from pylse import working_circuit, inp_at, Simulation, inspect, hole, PylseError


class TestHole(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_hole(self):
        # order of inputs and outputs matters
        # only is called when at least one input is high...
        @hole(delay=2.5, inputs=['a'], outputs=['q'], name='custom_hole')
        def custom_element(a, time):
            assert a is True
            return True

        i = inp_at(1.0, 3.0, name='i')
        o = custom_element(i)  # pylint: disable=no-value-for-parameter
        inspect(o, 'o')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [1.0, 3.0],
            'o': [3.5, 5.5],
        })
        hole_node = working_circuit()._src_map[o]
        self.assertEqual(hole_node.element.name, 'custom_hole')

    def test_hole_memory(self):
        mem = {}

        @hole(delay=1.0, inputs=['a0', 'a1', 'd0', 'd1', 'clk'], outputs=['q'], dict_io=True)
        def custom_element(a0, a1, d0, d1, clk, time):
            pass

    def test_hole_multiple_inputs_check_simultaneous(self):
        delay = 1.3

        @hole(delay=delay, dict_io=True, inputs=['a', 'b'], outputs=['q'])
        def custom_element(inputs, time):
            a = inputs['a']
            b = inputs['b']
            return {'q': a and b}

        i = inp_at(1.0, 3.0, name='i')
        j = inp_at(2.0, 3.0, 4.5, name='j')
        o = custom_element(i, j)  # pylint: disable=no-value-for-parameter
        inspect(o, 'o')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [1.0, 3.0],
            'j': [2.0, 3.0, 4.5],
            'o': [3.0 + delay],
        })

    def test_hole_multiple_inputs_check_remember_arrival(self):
        delay = 1.3
        inputs_arrived = defaultdict(list)

        @hole(delay=delay, dict_io=True, inputs=['a', 'b'], outputs=['q'])
        def custom_element(inputs, time):
            for inp, val in inputs.items():
                if val:
                    inputs_arrived[inp].append(time)

            at_least_two = all(len(times) >= 2 for times in inputs_arrived.values())
            return {'q': at_least_two}

        i = inp_at(1.0, 3.0, name='i')
        j = inp_at(2.0, 4.5, name='j')
        o = custom_element(i, j)  # pylint: disable=no-value-for-parameter
        inspect(o, 'o')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [1.0, 3.0],
            'j': [2.0, 4.5],
            'o': [4.5 + delay]
        })

    def test_hole_multiple_inputs_use_time(self):
        delay = 1.3
        between_time = 2.0
        last_arrived = defaultdict(lambda: None)

        @hole(delay=delay, dict_io=True, inputs=['a', 'b'], outputs=['q'])
        def custom_element(inputs, time: float):
            if inputs['a']:
                last_arrived['a'] = time
            if inputs['b']:
                last_arrived['b'] = time
            fire = last_arrived['a'] is not None and last_arrived['b'] is not None and \
                (max(last_arrived['a'], last_arrived['b']) >=
                    (min(last_arrived['a'], last_arrived['b']) + between_time))
            return {'q': fire}

        i = inp_at(1.0, 4.2, name='i')
        j = inp_at(2.0, 4.5, name='j')
        o = custom_element(i, j)  # pylint: disable=no-value-for-parameter
        inspect(o, 'o')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [1.0, 4.2],
            'j': [2.0, 4.5],
            'o': [4.2 + delay],
        })

    def test_hole_multiple_outputs(self):
        delay = 3.2

        @hole(delay=delay, inputs=['a'], outputs=['q', 'r'])
        def custom_element(a, time):
            return True, False

        i = inp_at(1.0, 3.0, name='i')
        o, p = custom_element(i)  # pylint: disable=no-value-for-parameter
        inspect(o, 'o')
        inspect(p, 'p')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [1.0, 3.0],
            'o': [1.0 + delay, 3.0 + delay],
            'p': [],
        })

    def test_hole_no_time_argument(self):
        with self.assertRaises(PylseError) as ex:
            @hole(delay=1.0, inputs=['a'], outputs=['q'])
            def custom_element(a):
                return True
        self.assertEqual(
            str(ex.exception),
            "Hole functions must have an argument named 'time'."
        )

    def test_hole_bad_output_map_returned(self):
        @hole(delay=1.0, inputs=['a'], outputs=['q'], dict_io=True)
        def custom_element(a, time):
            return {'r': True}
        i = inp_at(0.0)
        o = custom_element(i)  # pylint: disable=no-value-for-parameter
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'a' to the node with output wire '_1':\n"
            "Output 'q' is not found in dictionary "
            "returned from call to functional hole: {'r': True}."
        )


if __name__ == "__main__":
    unittest.main()
