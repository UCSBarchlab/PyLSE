import unittest

import pylse
from helpers import BaseTest, pulse_in_period, sim_and_gen

# Full adder (synchronous):
#
# I wrote this like a typical CMOS-style full adder,
# but of course with dros added to path balance, and
# splitters to deal with fanout. It has a depth of 3,
# and uses 8 clocks (so a clock tree depth of 3 too).
#
# Reuses intermediate xor_s result
# 5 splitters + 7 splitters for clock tree
# 2 and_s elements
# 1 or_s element
# 2 xor_s elements
# 3 dro elements
#
# The clock splitter tree looks like this (8 splitters):
#         /---- clk[0]  3 levels  (3 * 4.3 = 12.9 ps)
#       -<
#      /  \---- clk[1]
#    -<
#   /  \   ---- clk[2]
#  |    - < 
#  |       \--- clk[3]
# -<
#  |       /--- clk[4]
#  |    -<
#   \  /  ----- clk[5]
#    -< 
#      \ /----- clk[6]
#       -<
#          \--- clk[7]
def full_adder_sync(a, b, cin, clk):
    # Helpers to make overriding times easier
    # These are not counted in the line count in the paper since they
    # are commented out and doing literally nothing.
    def split(*args):
        return pylse.split(*args) #, firing_delay=0, transition_time=0, past_constraints={})
    def xor_s(*args):
        return pylse.xor_s(*args) #, firing_delay=0, transition_time=0, past_constraints={})
    def dro(*args):
        return pylse.dro(*args) #, firing_delay=0, transition_time=0, past_constraints={})
    def and_s(*args):
        return pylse.and_s(*args) #, firing_delay=0, transition_time=0, past_constraints={})
    def or_s(*args):
        return pylse.or_s(*args) #, firing_delay=0, transition_time=0, past_constraints={})

    clks = split(clk, 8)
    a0, a1 = split(a)
    b0, b1 = split(b)

    w0 = xor_s(a0, b0, clks[0])
    w0_0, w0_1 = split(w0)
    w1 = dro(cin, clks[1])
    cin0, cin1 = split(w1)
    w3 = xor_s(w0_0, cin0, clks[2])
    sum = dro(w3, clks[3])
    w5 = and_s(w0_1, cin1, clks[4])
    w6 = and_s(a1, b1, clks[5])
    w7 = dro(w6, clks[6])
    cout = or_s(w5, w7, clks[7])

    return sum, cout

class TestFullAdderSync(BaseTest):
    def test_full_adder_sync(self):
        # Assumptions for the following discussion
        # (add in manually if defaults changed in sfq_cells.py):
        #
        # s:
        #   delay: 4.3
        # dro:
        #   delay: 5.1
        #   setup: 1.2
        #   hold: 0.0
        # and:
        #   delay: 9.2
        #   setup: 2.8
        #   hold: 3.0
        # or:
        #   delay: 8.0
        #   setup: 5.8
        #   hold: 0.0
        # xor:
        #   delay: 6.5
        #   setup: 3.7
        #   hold: 4.1
        #
        # Constraints:
        # - that signals arrive at least <setup time> before clock (per gate),
        # - that signals arrive at least <hold time> after clock (per gate)
        #
        # Longest delay between any two synchronous gates is 10.8 (the xor + splitter to the and),
        # so 10.8 + 2.8 (the subsequent and gate's setup time) = 13.6.
        # However, the delay between the and gate and or is 9.2, and
        # the or's setup is 5.8, so 9.2 + 5.8 = 15.0, so 15.0 is the minimum time
        # that must exist between data signals and the next clock pulse.
        # With the maximum hold time of 4.1 (see assumptions above), there's a 19.1 window in
        # which nothing can arrive. So making the clock period, say 25, gives a 5.9 ps
        # window for pulses to arrive.
        # 
        # Also, note that the clock takes 12.9 to arrive to each gate due to splitter tree.
        a = pylse.inp_at(0.0, 30.0, 55.0, name='A')
        b = pylse.inp_at(3.0, 32.0, name='B')
        cin = pylse.inp_at(31.0, name='CIN')

        # Offset 25.0 period by 12.9 because of delay of clock getting through splitters to each gate.
        clk = pylse.inp(start=25.0 - 12.9, period=25.0, n=6, name='CLK')
        sum, cout = full_adder_sync(a, b, cin, clk)
        pylse.inspect(sum, 'SUM')
        pylse.inspect(cout, 'COUT')

        events, _ta = sim_and_gen("full_adder_sync", call_verify=False, exact=False)

        # The depth of the circuit is 3 (i.e. 3 synchronous gates in all paths),
        # so our first result shouldn't appear until after the 3rd clock pulse is seen.
        self.assertFalse(pulse_in_period(0, 25.0, events['SUM'], 12.9))
        self.assertFalse(pulse_in_period(1, 25.0, events['SUM'], 12.9))
        self.assertFalse(pulse_in_period(2, 25.0, events['SUM'], 12.9))
        self.assertFalse(pulse_in_period(3, 25.0, events['SUM'], 12.9))
        self.assertTrue(pulse_in_period(4, 25.0, events['SUM'], 12.9))
        self.assertTrue(pulse_in_period(5, 25.0, events['SUM'], 12.9))

        self.assertFalse(pulse_in_period(0, 25.0, events['COUT'], 12.9))
        self.assertFalse(pulse_in_period(1, 25.0, events['COUT'], 12.9))
        self.assertFalse(pulse_in_period(2, 25.0, events['COUT'], 12.9))
        self.assertTrue(pulse_in_period(3, 25.0, events['COUT'], 12.9))
        self.assertTrue(pulse_in_period(4, 25.0, events['COUT'], 12.9))
        self.assertFalse(pulse_in_period(5, 25.0, events['COUT'], 12.9))

if __name__ == "__main__":
    unittest.main()
