import unittest

import pylse


class TestWire(unittest.TestCase):
    def setUp(self):
        pylse.working_circuit().reset()

    def test_wire_name(self):
        w1, w2, w3 = pylse.Wire(), pylse.Wire(), pylse.Wire()
        self.assertEqual(w1.name, pylse.Wire.prefix + '0')
        self.assertEqual(w2.name, pylse.Wire.prefix + '1')
        self.assertEqual(w3.name, pylse.Wire.prefix + '2')

    def test_wire_accessible_given_name(self):
        w1, w2 = pylse.Wire(name='w1'), pylse.Wire(name='w2')
        self.assertIs(pylse.working_circuit().get_wire_by_name('w1'), w1)
        self.assertIs(pylse.working_circuit().get_wire_by_name('w2'), w2)

    def test_wire_already_connected(self):
        w1, w2, w3 = pylse.Wire(name='w1'), pylse.Wire(name='w2'), pylse.Wire(name='w3')
        w1 <<= w2
        with self.assertRaises(pylse.PylseError) as ex:
            w1 <<= w3
        self.assertEqual(
            str(ex.exception),
            "Wire 'w1' is already connected to a node."
        )


class TestNode(unittest.TestCase):
    def setUp(self):
        pylse.working_circuit().reset()

    def test_create_nodes(self):
        element = pylse.sfq_cells.JTL()
        w1 = pylse.Wire()
        w2 = pylse.Wire()
        n = pylse.Node(element, [w1], [w2])
        self.assertEqual(n.node_id, 0)
        n = pylse.Node(element, [w1], [w2])
        self.assertEqual(n.node_id, 1)
        n = pylse.Node(element, [w1], [w2])
        self.assertEqual(n.node_id, 2)


if __name__ == '__main__':
    unittest.main()
