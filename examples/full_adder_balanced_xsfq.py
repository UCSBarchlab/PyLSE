# Reference: G. Tzimpragos et al.,
# "Superconducting Computing with Alternating Logic Elements," ISCA 2021.

import pylse
from helpers import BaseTest, sim_and_gen, pulse_in_period

import unittest


def full_adder_balanced_xSFQ(a_p, a_n, b_p, b_n, cin_p, cin_n, clk):
    """ Pipelined (dual-rail) xSFQ full adder -- Fig. 12 of
        G. Tzimpragos et al., "Superconducting Computing with Alternating Logic Elements," ISCA 2021.

        Gate IOs buffered with JTL for better flux transmission.
        Fan_outs of two or more require splitters.
    """
    # These are all helpers to make it easy to ensure
    # we use the same delay numbers as the paper.

    def jtl(*args):
        return pylse.jtl(*args, firing_delay=5.7)

    def fa(x, y):
        """ First-arrival cell based on an inverted C-element.
            Inputs buffered with JTL for better flux transmission.
        """
        return pylse.c_inv(jtl(x), jtl(y), firing_delay=9.0)

    def la(x, y):
        """ Last-arrival cell based on a C-element.
            Inputs buffered with JTL for better flux transmission.
        """
        return pylse.c(jtl(x), jtl(y), firing_delay=8.0)

    def s(x):
        return pylse.s(x, firing_delay=4.3)

    def dro(*args):
        return pylse.dro(*args, firing_delay=5.1)

    # Create a clock tree
    clks = pylse.split(clk, n=10, firing_delay=4.3)

    a_p0, a_p1 = s(a_p)
    a_n0, a_n1 = s(a_n)
    b_p0, b_p1 = s(b_p)
    b_n0, b_n1 = s(b_n)
    cin_p0, cin_p1 = s(dro(jtl(cin_p), clks[0]))
    cin_n0, cin_n1 = s(dro(jtl(cin_n), clks[1]))

    and00 = la(a_p0, b_n0)
    and01 = la(a_n0, b_p0)
    and02 = la(b_p1, a_p1)
    and02_0, and02_1 = s(and02)
    and03 = la(b_n1, a_n1)
    and03_0, and03_1 = s(and03)

    or10 = fa(and00, and01)
    or10_0, or10_1 = s(dro(jtl(or10), clks[2]))
    or11 = fa(and02_0, and03_0)
    or11_0, or11_1 = s(dro(jtl(or11), clks[3]))

    and20 = la(cin_n0, or10_0)
    and20_0, and20_1 = s(and20)
    and21 = la(cin_p0, or10_1)
    and21_0, and21_1 = s(and21)
    and22 = la(cin_n1, or11_0)
    and23 = la(cin_p1, or11_1)

    or30 = fa(dro(jtl(and03_1), clks[4]), and20_0)
    or31 = fa(and21_1, dro(jtl(and02_1), clks[5]))
    or32 = fa(and21_0, and22)
    or33 = fa(and20_1, and23)

    s_p = dro(jtl(or33), clks[6])
    s_n = dro(jtl(or32), clks[7])
    cout_p = dro(jtl(or31), clks[8])
    cout_n = dro(jtl(or30), clks[9])
    return s_p, s_n, cout_p, cout_n


class TestAdders(BaseTest):
    def test_full_adder_xsfq(self):
        # Create clock signal
        t = 100  # duration of a phase
        clk = pylse.inp(start=2, period=t, n=4, name='clk')
        offset = 10

        # Provided input: a=1, b=1, cin=0
        a_p = pylse.inp_at(offset, name='a_p')
        a_n = pylse.inp_at(t+offset, name='a_n')
        b_p = pylse.inp_at(offset, name='b_p')
        b_n = pylse.inp_at(t+offset, name='b_n')
        cin_p = pylse.inp(t+offset, name='cin_p')
        cin_n = pylse.inp(offset, name='cin_n')

        # Call full_adder_balanced_xSFQ()
        s_p, s_n, cout_p, cout_n = full_adder_balanced_xSFQ(a_p, a_n, b_p, b_n, cin_p, cin_n, clk)

        # Probe outputs
        # Expected output: s=0, cout=1
        pylse.inspect(s_p, 's_p')
        pylse.inspect(s_n, 's_n')
        pylse.inspect(cout_p, 'cout_p')
        pylse.inspect(cout_n, 'cout_n')

        events, _ta = sim_and_gen("full_adder_xsfq", call_verify=False, exact=False)
        self.assertTrue(pulse_in_period(2, t, events['cout_p']))  # 224.3ish
        self.assertFalse(pulse_in_period(3, t, events['cout_p']))
        self.assertTrue(pulse_in_period(2, t, events['s_n']))  # 220.0ish
        self.assertFalse(pulse_in_period(3, t, events['s_n']))
        self.assertTrue(pulse_in_period(3, t, events['s_p']))  # 320.0ish
        self.assertFalse(pulse_in_period(2, t, events['s_p']))
        self.assertTrue(pulse_in_period(3, t, events['cout_n']))  # 324.3ish
        self.assertFalse(pulse_in_period(2, t, events['cout_n']))

if __name__ == "__main__":
    unittest.main()
