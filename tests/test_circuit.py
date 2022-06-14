from pylse.simulation import Simulation
import unittest

from pylse import working_circuit, PylseError, Wire
from pylse import jtl, m, inp, inp_at
from pylse.circuit import _Source, InGen


class TestCircuit(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_nonexisting_input(self):
        with self.assertRaises(PylseError):
            _j1 = jtl(3, name='j1')

    def test_variable_used_twice(self):
        '''
            Fan-out violation
        '''
        i1 = inp(name='rin')
        jtl1 = jtl(i1, name='j1')
        with self.assertRaises(PylseError) as ex:
            _mout = m(jtl1, jtl1, name='m_out')  # jtl1 used twice
        self.assertEqual(
            str(ex.exception),
            f"'j1' is used in the input list multiple times. "
            f"Did you want to use a splitter to split 'j1'?"
        )

    def test_backward_references(self):
        i1 = inp(name='i1')
        j1 = jtl(i1, name='j1')
        j2 = Wire(name='j2')
        mout = m(j1, j2, name='mout')
        jtl_delay = working_circuit()._src_map[j1].element.firing_delay
        m_delay = working_circuit()._src_map[mout].element.firing_delay
        # Note: there are issues if you supply a name that already exists,
        # since that will cause the new wire coming out of the jtl to be
        # given that name, and cause the other wire to be renamed. So be careful.
        j2 <<= jtl(mout, firing_delay=jtl_delay)
        # Note: must supply 'until' parameter, or we'll go on __forever__
        sim = Simulation()
        events = sim.simulate(until=45)
        self.assertEqual(events['i1'], [0.0])
        self.assertEqual(events['j1'], [jtl_delay])
        # Rounding because actual result is something like 19.599999999999998,
        # and we calculate 19.6 here...
        self.assertEqual(
            [round(e, 1) for e in events['j2']],
            [2*jtl_delay+m_delay, 3*jtl_delay+2*m_delay]
        )
        self.assertEqual(
            events['mout'],
            [jtl_delay+m_delay, 2*jtl_delay+2*m_delay, 3*jtl_delay+3*m_delay]
        )

    def test_too_many_outputs(self):
        """ Illegal because jtl only has one output. """
        i1 = inp(name="rin")
        jtl1 = jtl(i1, name="j1")
        with self.assertRaises(PylseError) as ex:
            _mout = m(jtl1, i1, name="m_out")
        self.assertEqual(
            str(ex.exception),
            f"Wire 'rin' is already connected to a node. "
            f"Did you want to use a splitter to split 'rin'?"
        )

    def test_input_used_twice(self):
        """ Illegal because jtl only has one output. """
        i1 = inp(name="rin")
        jtl1 = jtl(i1, name="j1")
        with self.assertRaises(PylseError) as ex:
            _mout = m(jtl1, jtl1, name="m_out")
        self.assertEqual(
            str(ex.exception),
            f"'j1' is used in the input list multiple times. "
            f"Did you want to use a splitter to split 'j1'?"
        )


class TestSpecial(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_source(self):
        src = working_circuit().source_wire()
        self.assertIsInstance(src, Wire)
        src_node = working_circuit()._src_map[src]
        self.assertIsInstance(src_node.element, _Source)

    def test_ingen_bad_times(self):
        with self.assertRaises(PylseError) as ex:
            InGen([1.0, 3, 'a'])
        self.assertEqual(
            str(ex.exception),
            "InGen times must be ints or floats, given [1.0, 3, 'a']."
        )

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


if __name__ == "__main__":
    unittest.main()
