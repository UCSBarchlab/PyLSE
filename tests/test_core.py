import unittest

from pylse import working_circuit, Wire, PylseError


class TestWire(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_wire_name(self):
        w1, w2, w3 = Wire(), Wire(), Wire()
        self.assertEqual(w1.name, Wire.prefix + '0')
        self.assertEqual(w2.name, Wire.prefix + '1')
        self.assertEqual(w3.name, Wire.prefix + '2')

    def test_wire_accessible_given_name(self):
        w1, w2 = Wire(name='w1'), Wire(name='w2')
        self.assertIs(working_circuit().get_wire_by_name('w1'), w1)
        self.assertIs(working_circuit().get_wire_by_name('w2'), w2)

    def test_wire_already_connected(self):
        w1, w2, w3 = Wire(name='w1'), Wire(name='w2'), Wire(name='w3')
        w1 <<= w2
        with self.assertRaises(PylseError) as ex:
            w1 <<= w3
        self.assertEquals(
            str(ex.exception),
            "'w1' is already connected to a node."
        )


if __name__ == '__main__':
    unittest.main()
