# pylint: disable=no-member

import unittest

from pylse import working_circuit, PylseError, Simulation, Transitional, Wire
from pylse import inp, inp_at
from pylse.transitional import NormalizedTransition, get_matching_transition, FSM


class TestSpecial(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_inp(self):
        period = 5
        n = 3
        _in0 = inp(period=period, n=n, name='in0')
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [i * period for i in range(n)],
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
        self.assertEqual(t.firing, {'q': 4.3})
        self.assertEqual(s.transition_time, 2.1)

    def test_firing_delay_overriden_in_transition(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': 'q'},
            ]
            firing_delay = 4.3
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(t.firing, {'q': 4.3})

    def test_firing_delay_overriden_per_firing_output(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': {'q': 2.3, 'r': 3.2}},
            ]
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(t.firing, {'q': 2.3, 'r': 3.2})

    def test_firing_delay_overriden_per_firing_output_with_default(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q', 'r']
            transitions = [
                {'id': '1', 'source': 'idle', 'trigger': 'a', 'dest': 'bar',
                 'firing': {'q': 2.3, 'r': 4.3}},
            ]
            name = 'Simple'

        s = Simple()
        t = s.get_transition_by_id('1')
        self.assertEqual(t.firing, {'q': 2.3, 'r': 4.3})

    def test_catch_negative_firing_delay(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'firing_delay': -4},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Firing delay must be a non-negative number, got -4."
        )

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
            "The given FSM is missing a 'source' (or 'src') key in a transition."
        )

    def test_duplicate_source(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'foo', 'src': 'foo',
                 'trigger': 'a', 'dest': 'bar', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Must supply either the 'source' or 'src' key, but not both (they are equivalent)."
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
            "The given FSM is missing a 'destination' (or 'dest') key in a transition."
        )

    def test_duplicate_dest(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'foo', 'trigger': 'a',
                 'dest': 'bar', 'destination': 'bar', 'firing': 'q'},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Must supply either the 'destination' or 'dest' key, "
            "but not both (they are equivalent)."
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
        self.assertRegex(
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
            f"Input trigger 'b' from transitions was not "
            "found in list of inputs."
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
        self.assertRegex(
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
            "Output 'r' from transition was not found in list of outputs."
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

    def test_catch_negative_transition_time(self):
        class Simple(Transitional):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'transition_time': -4},
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()

        self.assertEqual(
            str(ex.exception),
            "Transition time must be a non-negative number, got -4."
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

    def test_asterisk_illegal_prior(self):
        class Simple(Transitional):
            inputs = ['a', 'b', 'c']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'b', 'dest': 'idle',
                 'firing': 'q', 'past_constraints': {'*': 4, 'b': 1}},
                {'source': 'idle', 'trigger': ['a', 'c'], 'dest': 'idle'},
            ]
            name = 'Simple'
        s = Simple()
        self.assertEqual(
            s.get_transition_by_id('0').past_constraints,
            {'a': 4, 'b': 1, 'c': 4}
        )

    def test_catch_illegal_prior_bad_trigger_name(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle',
                 'firing': 'q', 'illegal_priors': {'c': -3}},
            ]
            name = 'Simple'
        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Unrecognized key for 'illegal_priors' dictionary: c. "
            "Must use valid inputs to this machine."
        )

    def test_catch_illegal_prior_negative_value(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle',
                 'firing': 'q', 'illegal_priors': {'b': -3}},
            ]
            name = 'Simple'
        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Value for an illegal_prior mapping must be non-negative number, got -3 "
            "in transition 0."
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
        self.assertEqual(s.get_transition_by_id('0').firing, {'q': 0.0})
        self.assertEqual(s.get_transition_by_id('1').firing, dict())

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
        self.assertEqual(s.get_transition_by_id('my_special_id').firing, {'q': 0})

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
        for transition in s.transitions:
            if transition.id == '0':
                self.assertFalse(transition.is_error)
            elif transition.id == '1':
                self.assertTrue(transition.is_error)

    def test_not_all_priorities_given(self):
        class Simple(Transitional):
            inputs = ['a', 'b']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'priority': 0,
                 'dest': 'idle', 'firing': 'q'},
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle'}
            ]
            name = 'Simple'

        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Given a set of transitions originating from the same source ('idle'), "
            "either all of them must have a priority field, or none of them "
            "must (in which case the priority is determined by the order in "
            "which they were given in the transition list)."
        )

    def test_non_consecutive_priorities(self):
        class Simple(Transitional):
            inputs = ['a', 'b', 'c']
            outputs = ['q']
            transitions = [
                {'source': 'idle', 'trigger': 'a', 'priority': 0,
                 'dest': 'idle', 'firing': 'q'},
                {'source': 'idle', 'trigger': 'b', 'dest': 'idle', 'priority': 2},
                {'source': 'idle', 'trigger': 'c', 'dest': 'state1', 'priority': 0},
                {'source': 'state1', 'trigger': ['a', 'b'], 'dest': 'idle', 'firing': 'q'},
                {'source': 'state1', 'trigger': 'c', 'dest': 'state1'},
            ]
            name = 'Simple'
        with self.assertRaises(PylseError) as ex:
            Simple()
        self.assertEqual(
            str(ex.exception),
            "Given a set of transitions originating from the same source ('idle'), "
            "set of priorites for that group must be consecutive (i.e. if transitions A and C "
            "have priority 0, transition B can have priority 0 or 1, but not 2, since priority 1 "
            "hasn't been used yet)."
        )

    def test_priorities_assigned_correctly(self):
        class Simple(Transitional):
            inputs = ['a', 'b', 'c']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'a', 'priority': 0,
                 'dest': 'idle', 'firing': 'q'},
                {'id': '1', 'source': 'idle', 'trigger': 'b', 'dest': 'idle', 'priority': 1},
                {'id': '2', 'source': 'idle', 'trigger': 'c', 'dest': 'state1', 'priority': 0},
                {'id': '3', 'source': 'state1', 'trigger': ['a', 'b'],
                 'dest': 'idle', 'firing': 'q'},
                {'id': '4', 'source': 'state1', 'trigger': 'c', 'dest': 'state1'},
            ]
            name = 'Simple'
        s = Simple()
        self.assertEqual(s.get_transition_by_id('0').priority, 0)
        self.assertEqual(s.get_transition_by_id('1').priority, 1)
        self.assertEqual(s.get_transition_by_id('2').priority, 0)
        self.assertEqual(s.get_transition_by_id('3').priority, 0)
        self.assertEqual(s.get_transition_by_id('4').priority, 1)

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
        t1 = NormalizedTransition('0', 'idle', 'idle', 'a', 0)
        t2 = NormalizedTransition('1', 'idle', 'idle', 'b', 0)
        t3 = NormalizedTransition('2', 'foo', 'bar', 'b', 0)
        t4 = NormalizedTransition('3', 'foo', 'baz', 'c', 0)
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
            NormalizedTransition('0', 'idle', 'state1', 'a', 0),
            NormalizedTransition('1', 'idle', 'state2', 'b', 0),
            NormalizedTransition('2', 'state1', 'idle', 'b', 0),
            NormalizedTransition('3', 'state1', 'state1', 'a', 0),
        ]
        outputs = ['q']
        fsm = FSM('Test', inputs, outputs, transitions)
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
            NormalizedTransition('0', 'idle', 'state1', 'a', 0),
            NormalizedTransition('1', 'idle', 'idle', 'b', 0, is_error=True),
        ]
        outputs = ['q']
        fsm = FSM('Test', inputs, outputs, transitions)
        self.assertEqual(fsm.curr_state, 'idle')
        with self.assertRaises(PylseError) as ex:
            fsm.step('b', 0)
        self.assertEqual(
            str(ex.exception),
            "Triggered erroneous transition id '1'"
        )


if __name__ == '__main__':
    unittest.main()
