import pylse
from helpers import BaseTest, sim_and_gen, N_times, S_delay, C_delay, C_inv_delay

import math
import unittest

def balance(a, b):
    jtl_delay = pylse.delay(a) - pylse.delay(b)
    if jtl_delay < 0:
        a = pylse.jtl(a, firing_delay=-jtl_delay)
    elif jtl_delay > 0:
        b = pylse.jtl(b, firing_delay=jtl_delay)
    return a, b

C_reset_time = 5
S_reset_time = 5
C_inv_reset_time = 5

# AKA comparator
def min_max(a, b):
    # Helpers to make the actual code below more readable.
    # If we just use the s/c/c_inv defaults, no need for these
    # helper functions at all.
    def s(a):
        return pylse.s(a, firing_delay=S_delay, transition_time=S_reset_time)

    def c(a, b):
        return pylse.c(a, b, firing_delay=C_delay, transition_time=C_reset_time)

    def c_inv(a, b):
        return pylse.c_inv(a, b, firing_delay=C_inv_delay, transition_time=C_inv_reset_time)

    a1, a2 = s(a)
    b1, b2 = s(b)
    low = c_inv(a1, b1)  # FA
    high = c(a2, b2)  # LA
    high = pylse.jtl(high, firing_delay=C_inv_delay - C_delay)  # D
    return low, high

    # Using the above hardcoded jtl for paper presentation,
    # but can also use this for more generality:
    # return balance(low, high)

class TestMinMaxPair(BaseTest):
    def setUp(self):
        super().setUp()
        self.path_delay = S_delay + C_inv_delay

    def min_max_pair_tester(self, variability):
        # Minimum distance depends on transition time of C and Inv C elements.
        # We're not testing the minimum right now.

        a_times = [115.0, 215.0, 315.0]
        b_times = [64.0, 184.0, 304.0]
        a = pylse.inp_at(*a_times, name='A')
        b = pylse.inp_at(*b_times, name='B')
        low, high = min_max(a, b)
        pylse.inspect(low, 'LOW')
        pylse.inspect(high, 'HIGH')

        if variability:
            variability = {'wires_to_exclude': ['A', 'B']}
        events, ta = sim_and_gen(
            "min-max-pair-spice-comp",
            variability=variability,
            get_average_sim=N_times,
            wires_to_display=['A', 'B', 'LOW', 'HIGH']
        )
        self.assertEqual(len(events['LOW']), 3)
        self.assertEqual(len(events['HIGH']), 3)

        if variability:
            # Check that low occurs before high
            low = events['LOW']
            high = events['HIGH']
            self.assertLess(low[0], high[0])
            self.assertLess(high[0], low[1])
            self.assertLess(low[1], high[1])
            self.assertLess(high[1], low[2])
            self.assertLess(low[2], high[2])
        else:
            # No variability, so we can check actual expected times...
            self.assertTrue(math.isclose(events['LOW'][0],
                min(a_times[0], b_times[0]) + self.path_delay, rel_tol=1e-5))
            self.assertTrue(math.isclose(events['HIGH'][0],
                max(a_times[0], b_times[0]) + self.path_delay, rel_tol=1e-5))
            self.assertTrue(math.isclose(events['LOW'][1],
                min(a_times[1], b_times[1]) + self.path_delay, rel_tol=1e-5))
            self.assertTrue(math.isclose(events['HIGH'][1],
                max(a_times[1], b_times[1]) + self.path_delay, rel_tol=1e-5))


    def test_min_max_pair_var(self):
        self.min_max_pair_tester(True)

    def test_min_max_pair_spice_comp(self):
        self.min_max_pair_tester(False)

if __name__ == "__main__":
    unittest.main()
