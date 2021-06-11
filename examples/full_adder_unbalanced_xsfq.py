# Reference: G. Tzimpragos et al., "Superconducting Computing with Alternating Logic Elements," ISCA 2021.

from pylse import inp, inp_at, inspect, Simulation
from pylse import c_inv, c, s, jtl, dro, split


def fa(x, y):
    """
        First-arrival cell based on an inverted C-element.
        Inputs buffered with JTL for better flux transmission.
    """
    return c_inv(jtl(x), jtl(y))


def la(x, y):
    """
        Last-arrival cell based on a C-element.
        Inputs buffered with JTL for better flux transmission.
    """
    return c(jtl(x), jtl(y))


def dro_pair(x, clk):
    """
        xSFQ storage element consisting of two DRO cells in series.
    """
    return dro(jtl(dro(jtl(x), clk[0])), clk[1])


def full_adder_unbalanced_xSFQ(a_p, a_n, b_p, b_n, cin_p, cin_n, clk):
    """
        xSFQ (dual-rail) full adder followed by a pair of DRO cells-- Fig. 11
        Gate IOs buffered with JTL for better flux transmission.
        Fan_outs of two or more require splitters.
    """
    a_p0, a_p1 = s(a_p)
    a_n0, a_n1 = s(a_n)
    b_p0, b_p1 = s(b_p)
    b_n0, b_n1 = s(b_n)
    cin_p0, cin_p1 = s(cin_p)
    cin_n0, cin_n1 = s(cin_n)

    and00 = la(a_p0, b_n0)
    and01 = la(a_n0, b_p0)
    and02 = la(b_p1, a_p1)
    and02_0, and02_1 = s(and02)
    and03 = la(b_n1, a_n1)
    and03_0, and03_1 = s(and03)

    or10 = fa(and00, and01)
    or10_0, or10_1 = s(or10)
    or11 = fa(and02_0, and03_0)
    or11_0, or11_1 = s(or11)

    and20 = la(cin_n0, or10_0)
    and20_0, and20_1 = s(and20)
    and21 = la(cin_p0, or10_1)
    and21_0, and21_1 = s(and21)
    and22 = la(cin_n1, or11_0)
    and23 = la(cin_p1, or11_1)

    or30 = fa(and03_1, and20_0)
    or31 = fa(and21_1, and02_1)
    or32 = fa(and21_0, and22)
    or33 = fa(and20_1, and23)

    # Create a clock tree
    clks = split(clk, n=8)

    s_p = dro_pair(or33, clks[0:2])
    s_n = dro_pair(or32, clks[2:4])
    cout_p = dro_pair(or31, clks[4:6])
    cout_n = dro_pair(or30, clks[6:8])
    return s_p, s_n, cout_p, cout_n


if __name__ == "__main__":
    # Create clock signal
    T = 80  # duration of a phase
    clk = inp(delay=T, niter=4, name='clk')

    # Provided input: a=1, b=1, cin=0
    a_p = inp(delay=0*T, niter=1, name='a_p')
    a_n = inp(delay=1*T, niter=1, name='a_n')
    b_p = inp(delay=0*T, niter=1, name='b_p')
    b_n = inp(delay=1*T, niter=1, name='b_n')
    cin_p = inp(delay=1*T, niter=1, name='cin_p')
    cin_n = inp(delay=0*T, niter=1, name='cin_n')

    # Call full_adder_unbalanced_xSFQ()
    s_p, s_n, cout_p, cout_n = full_adder_unbalanced_xSFQ(a_p, a_n, b_p, b_n, cin_p, cin_n, clk)

    # Probe outputs
    # Expected output: s=0, cout=1
    inspect(s_p, 's_p')
    inspect(s_n, 's_n')
    inspect(cout_p, 'cout_p')
    inspect(cout_n, 'cout_n')

    # Run simulation
    sim = Simulation()
    events = sim.simulate()
    sim.display()
