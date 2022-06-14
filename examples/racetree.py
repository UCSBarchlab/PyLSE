import pylse

from helpers import BaseTest, sim_and_gen

import math
import unittest

# Race tree with 3 nodes
def racetree(x, y, thr0, thr1, thr2, tub):
    # Split upper bound reference signal
    tub_0, tub_1, tub_2 = pylse.split(tub, n=3)

    # Split input x
    x_0, x_1 = pylse.s(x)

    # Node 0
    n0 = pylse.inv(thr0, x_0, 'n0')
    n0_0, n0_10, n0_11 = pylse.split(n0, n=3)
    not_n0 = pylse.inv(n0_11, tub_0)
    not_n0_0, not_n0_1 = pylse.s(not_n0)

    # Node 1
    n1 = pylse.inv(thr1, x_1, 'n1')
    n1_0, n1_1 = pylse.s(n1)
    not_n1 = pylse.inv(n1_1, tub_1)

    # Node 2
    n2 = pylse.inv(thr2, y, 'n2')
    n2_0, n2_1 = pylse.s(n2)
    not_n2 = pylse.inv(n2_1, tub_2)

    # Combine decisions
    dec_a = pylse.c(n0_0, n1_0)
    dec_b = pylse.c(n0_10, not_n1)
    dec_c = pylse.c(not_n0_0, n2_0)
    dec_d = pylse.c(not_n0_1, not_n2)

    return dec_a, dec_b, dec_c, dec_d

class TestRaceTree(BaseTest):
    def test_race_tree(self):
        x = pylse.inp_at(10.0, name='x')
        y = pylse.inp_at(6.0, name='y')
        thr0 = pylse.inp_at(4.0, name='thr0')  # node 0: x < thr0
        thr1 = pylse.inp_at(8.0, name='thr1')  # node 1: x < thr1
        thr2 = pylse.inp_at(11.0, name='thr2')  # node 2: y < thr2
        tub = pylse.inp_at(20.0, name='tub')  # upper bound pulse
        # All the following cases are mutually exclusive:
        # Label a wants node 0 True and node 1 True (dc about node 2)
        # Label b wants node 0 True and node 1 False (dc about node 2)
        # Label c wants node 0 False and node 2 True (dc about node 1)
        # Label d wants node 0 False and node 2 False (dc about node 1)
        dec_a, dec_b, dec_c, dec_d = racetree(x, y, thr0, thr1, thr2, tub)
        pylse.inspect(dec_a, 'a')
        pylse.inspect(dec_b, 'b')
        pylse.inspect(dec_c, 'c')
        pylse.inspect(dec_d, 'd')

        events, _ta = sim_and_gen("race_tree", call_verify=False, exact=False)

        # only one output went high...
        self.assertEqual(sum(len(l) for o, l in events.items()
                         if o in ('a', 'b', 'c', 'd')), 1)
        # and it was the correct output, at the right time...
        self.assertTrue(math.isclose(events['c'][0], 46.199999999999996, rel_tol=1e-5))

if __name__ == "__main__":
    unittest.main()
