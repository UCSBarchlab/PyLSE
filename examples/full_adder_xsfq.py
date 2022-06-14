# Reference: G. Tzimpragos et al.,
# "Superconducting Computing with Alternating Logic Elements," ISCA 2021.

from pylse import inp_at, inspect, Simulation
from pylse import c_inv, c, s, jtl


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


def full_adder_xSFQ(a_p, a_n, b_p, b_n, cin_p, cin_n):
    """
        xSFQ (dual-rail) full adder composed of 14 FA/LA cells -- Fig. 7
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

    cout_n = fa(and03_1, and20_0)
    cout_p = fa(and21_1, and02_1)
    s_n = fa(and21_0, and22)
    s_p = fa(and20_1, and23)
    return s_p, s_n, cout_p, cout_n


if __name__ == "__main__":

    T = 80  # duration of a phase

    # Provided input: a=1, b=1, cin=0
    a_p = inp_at(0*T, name='a_p')
    a_n = inp_at(1*T,  name='a_n')
    b_p = inp_at(0*T, name='b_p')
    b_n = inp_at(1*T, name='b_n')
    cin_p = inp_at(1*T, name='cin_p')
    cin_n = inp_at(0*T, name='cin_n')

    # Call full_adder_xSFQ()
    s_p, s_n, cout_p, cout_n = full_adder_xSFQ(a_p, a_n, b_p, b_n, cin_p, cin_n)

    # Probe outputs
    # Expected output: s=0, cout=1
    inspect(s_p, 's_p')
    inspect(s_n, 's_n')
    inspect(cout_p, 'cout_p')
    inspect(cout_n, 'cout_n')

    # Run simulation
    sim = Simulation()
    events = sim.simulate()
    sim.plot()
