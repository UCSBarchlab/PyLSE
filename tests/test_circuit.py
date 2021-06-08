from pylse.simulation import Simulation
import unittest

from pylse import working_circuit, PylseError, Wire
from pylse import jtl, c, inp, inp_at
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
            _cout = c(jtl1, jtl1, name='m_out')  # jtl1 used twice
        self.assertEqual(
            str(ex.exception),
            f"'j1' is used in the input list multiple times. "
            f"Did you want to use a splitter to split 'j1'?"
        )

    def test_too_many_outputs(self):
        """ Illegal because jtl only has one output. """
        i1 = inp(name="rin")
        jtl1 = jtl(i1, name="j1")
        with self.assertRaises(PylseError) as ex:
            _mout = c(jtl1, i1, name="m_out")
        self.assertEquals(
            str(ex.exception),
            f"'rin' is already connected to a node. "
            f"Did you want to use a splitter to split 'rin'?"
        )

    def test_input_used_twice(self):
        """ Illegal because jtl only has one output. """
        i1 = inp(name="rin")
        jtl1 = jtl(i1, name="j1")
        with self.assertRaises(PylseError) as ex:
            _mout = c(jtl1, jtl1, name="m_out")
        self.assertEquals(
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


if __name__ == "__main__":
    unittest.main()
