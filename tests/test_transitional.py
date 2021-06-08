# pylint: disable=no-member

import unittest

from pylse import working_circuit, PylseError, Simulation, Transitional
from pylse import inp, inp_at
from pylse.transitional import NormalizedTransition, get_matching_transition, FSM


class TestSpecial(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_inp(self):
        delay = 5
        niter = 3
        _in0 = inp(delay=delay, niter=niter, name='in0')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [(i + 1) * delay for i in range(niter)],
        })

    def test_inputs_at(self):
        _ins = inp_at(0.0, 1.0, 4.0, 13.0, name='ins')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'ins': [0.0, 1.0, 4.0, 13.0],
        })


class TestTransitional(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_defaults(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'bar', 'firing': 'q'},
            ]
            name = 'Simple'

        s = Simple()
        self.assertEqual(s.firing_delay, 0.0)
        self.assertEqual(s.strict, True)
        self.assertEqual(s.transition_time, 0.0)
        self.assertEqual(s.get_transition_by_id(0).transition_time, 0.0)

    def test_firing_delay_overriden(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar', 'firing': 'q'},
            ]
            firing_delay = 4.3
            transition_time = 2.1
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(s.firing_delay, 4.3)
        self.assertEqual(t.firing_delay, {'q': 4.3})
        self.assertEqual(s.transition_time, 2.1)

    def test_firing_delay_overriden_in_transition(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': 'q', 'firing_delay': 2.3},
            ]
            firing_delay = 4.3
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(t.firing_delay, {'q': 2.3})

    def test_firing_delay_overriden_per_firing_output(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': ['q', 'r'], 'firing_delay': {'q': 2.3, 'r': 3.2}},
            ]
            firing_delay = 4.3
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(t.firing_delay, {'q': 2.3, 'r': 3.2})

    def test_firing_delay_overriden_per_firing_output_with_default(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': ['q', 'r'], 'firing_delay': {'q': 2.3}},
            ]
            firing_delay = 4.3
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(t.firing_delay, {'q': 2.3, 'r': 4.3})

    def test_transition_time_not_a_number(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': 'q', 'transition_time': 'xyz'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Transition time must be a number, got type str."
        )

    def test_missing_source(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'trigger': 'a', 'dest': 'bar', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "The given FSM is missing a 'source' key in a transition."
        )

    def test_missing_trigger(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'dest': 'bar', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "The given FSM is missing a 'trigger' key in a transition."
        )

    def test_missing_dest(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "The given FSM is missing a 'dest' key in a transition."
        )

    def test_no_idle_state(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'foo', 'trigger': 'a', 'dest': 'bar', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "The given FSM does not have an 'idle' source state."
        )

    def test_duplicate_inputs_in_same_trigger(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': ['a', 'a'], 'dest': 'idle', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            _s = Simple()
        self.assertRegexpMatches(
            str(ex.exception),
            r"Input trigger 'a' is found multiple times in trigger field ['a', 'a']."
        )

    def test_given_input_not_in_transitions(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "No transitions specified for inputs 'a' from state 'idle'."
        )

    def test_input_in_transitions_not_supplied(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Input trigger 'b' from transitions was not found in list of inputs."
        )

    def test_duplicate_outputs_in_same_trigger(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': ['q', 'q']},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            _s = Simple()
        self.assertRegexpMatches(
            str(ex.exception),
            r"Output 'q' is found multiple times in firing field ['q', 'q']."
        )

    def test_given_output_not_in_transitions(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'r'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "There must be at least one transition that fires output 'q'."
        )

    def test_output_in_transitions_not_supplied(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'r'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Output 'r' from transitions was not found in list of outputs."
        )

    def test_no_firing_transition(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = []
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "There must be at least one output; found none."
        )

    def test_firing_delay_is_not_a_number(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'firing_delay': 'xyz'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Firing delay must be a number, or a dictionary "
            "from output name to a number; got str."
        )

    def test_firing_delay_is_not_a_number_in_dict(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'firing_delay': {'q': True}},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Firing delay dictionary values must be numbers; got bool."
        )

    def test_firing_delay_dict_has_invalid_keys(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'firing_delay': {'r': 4.0}},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "The following keys of a firing delay dictionary are not firing "
            "outputs for this transition: r."
        )

    def test_unknown_transition_ignore_input(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q',
                 'transition_ignore': 'b'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Ignored input 'b' from transitions was not found in list of inputs."
        )

    def test_duplicate_transition_ignore_input(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q',
                 'transition_ignore': ['a', 'a']},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Input trigger 'a' is found multiple times in 'transition_ignore' field '['a', 'a']'."
        )

    def test_multiple_same_ids(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
                {'id': '0', 'source': 'idle', 'trigger': 'b', 'dest': 'idle'}
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Multiple transitions with the same id '0' found:\n"
            "1) {'id': '0', 'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'}\n"
            "2) {'id': '0', 'source': 'idle', 'trigger': 'b', 'dest': 'idle'}"
        )

    def test_automatic_transition_ids_added_in_order(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle'}
            ]
            name = 'Simple'

        s = Simple()
        self.assertEqual(s.get_transition_by_id('0').firing, ['q'])
        self.assertEqual(s.get_transition_by_id('1').firing, [])

    def test_access_transition_by_user_defined_id(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'id': 'my_special_id', 'source': 'idle', 'trigger': 'a',
                 'dest': 'idle', 'firing': 'q'},
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle'}
            ]
            name = 'Simple'

        s = Simple()
        self.assertEqual(s.get_transition_by_id('my_special_id').firing, ['q'])

    def test_bad_error_transitions_ids(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': {'a', '~b'},
                 'dest': 'idle', 'firing': 'q'},
                {'id': '1', 'source': 'idle', 'trigger': 'b', 'dest': 'idle'}
            ]
            name = 'Simple'
            error_transitions = {'2'}

        with self.assertRaises(PylseError) as ex:
            Simple()
            self.assertEqual(
                str(ex.exception),
                "Error transition id(s) {'2'} do(es) not "
                "match any given transition."
            )

    def test_error_fields_assigned(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'a',
                 'dest': 'idle', 'firing': 'q'},
                {'id': '1', 'source': 'idle', 'trigger': 'b', 'dest': 'idle'}
            ]
            name = 'Simple'
            error_transitions = {'1'}

        s = Simple()
        for transition in s.normalized_transitions:
            if transition.id == '0':
                self.assertFalse(transition.is_error)
            elif transition.id == '1':
                self.assertTrue(transition.is_error)

    def test_ambiguous_triggers(self):
        t1 = {'id': '0', 'source': 'idle', 'trigger': 'a', 'dest': 'idle'}
        t2 = {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'}

        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [t1, t2]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            _s = Simple()
        self.assertEqual(
            str(ex.exception),
            "Ambiguous triggers 'a' found on transitions:\n"
            f"1) {str(t1)}\n"
            f"2) {str(t2)}."
        )

    def test_get_matching_transition(self):
        t1 = NormalizedTransition('0', 'idle', 'idle', 'a')
        t2 = NormalizedTransition('1', 'idle', 'idle', 'b')
        t3 = NormalizedTransition('2', 'foo', 'bar', 'b')
        t4 = NormalizedTransition('3', 'foo', 'baz', 'c', 'd')
        ts = [t1, t2, t3, t4]

        t = get_matching_transition('idle', 'a', ts)
        self.assertEqual(t, t1)
        t = get_matching_transition('idle', 'b', ts)
        self.assertEqual(t, t2)
        t = get_matching_transition('foo', 'e', ts, strict=False)
        self.assertEqual(t, None)
        t = get_matching_transition('foo', 'c', ts)
        self.assertEqual(t, t4)


class TestFSM(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_step_1(self):
        inputs = ['a', 'b']
        transitions = [
            NormalizedTransition('0', 'idle', 'state1', 'a'),
            NormalizedTransition('1', 'idle', 'state2', 'b'),
            NormalizedTransition('2', 'state1', 'idle', 'b'),
            NormalizedTransition('3', 'state1', 'state1', 'a'),
        ]
        outputs = ['q']
        fsm = FSM(inputs, outputs, transitions)
        self.assertEqual(fsm.curr_state, 'idle')
        fsm.step('a', 0)
        self.assertEqual(fsm.curr_state, 'state1')
        fsm.step('a', 0, strict=False)
        self.assertEqual(fsm.curr_state, 'state1')
        fsm.step('b', 0)
        self.assertEqual(fsm.curr_state, 'idle')

    def test_step_via_error_transition(self):
        inputs = ['a', 'b']
        transitions = [
            NormalizedTransition('0', 'idle', 'state1', 'a'),
            NormalizedTransition('1', 'idle', 'idle', 'b', is_error=True),
        ]
        outputs = ['q']
        fsm = FSM(inputs, outputs, transitions)
        self.assertEqual(fsm.curr_state, 'idle')
        with self.assertRaises(PylseError) as ex:
            fsm.step('b', 0)
        self.assertEqual(
            str(ex.exception),
            "Triggered erroneous transition id '1'"
        )


if __name__ == '__main__':
    unittest.main()
