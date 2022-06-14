import unittest
import random

from pylse import working_circuit, inp, inp_at, Simulation, SFQ, Wire, PylseError
from pylse import jtl, c, c_inv, m, s, dro, dro_sr, dro_c, inv, and_s, or_s, xor_s, \
                  xnor_s, nor_s, nand_s, split, jtl_chain


def delay(wire):
    return working_circuit()._src_map[wire].element.firing_delay


class TestCellsSetup(unittest.TestCase):
    # Just for checking we can set arbitrary parameters and override class defaults
    def setUp(self):
        working_circuit().reset()

    def test_jtl_custom(self):
        in0 = inp(period=3.0, n=2, name='in0')
        jtl_out = jtl(in0, name='jtl_out', jjs=8, firing_delay=7.5)
        j_node = working_circuit()._src_map[jtl_out]
        self.assertEqual(j_node.element.jjs, 8)
        self.assertEqual(j_node.element.transitions[0].firing['q'], 7.5)

    def test_c_custom(self):
        in0 = inp(period=2, n=3, name='in0')
        in1 = inp(period=5, n=2, name='in1')
        c_out = c(in0, in1, name='c_out', jjs=5, firing_delay=11.4)
        c_node = working_circuit()._src_map[c_out]
        self.assertEqual(c_node.element.jjs, 5)
        self.assertEqual(c_node.element.get_transition_by_id('2').firing['q'], 11.4)
        self.assertEqual(c_node.element.get_transition_by_id('4').firing['q'], 11.4)


# Most of these tests assume/set a transition time of 0, because we're just
# testing that the state machines respond to inputs correctly.
class TestAsynchronousCells(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_jtl(self):
        in_period = 3.0
        in_n = 2
        in0 = inp(period=in_period, n=in_n, name='in0')
        jtl_out = jtl(in0, name='jtl_out')
        jtl_delay = delay(jtl_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [i * in_period for i in range(in_n)],
            'jtl_out': [t + jtl_delay for t in events['in0']]
        })

    def test_jtl_chain(self):
        in0 = inp_at(0.0, 3.0, 4.0, name='in0')
        firing_delay = 4.2
        jtl_out = jtl_chain(in0, 3, firing_delay=firing_delay, names='jtl0 jtl1 jtl_out')
        jtl_1 = working_circuit()._src_map[jtl_out].input_wires[0]
        jtl_0 = working_circuit()._src_map[jtl_1].input_wires[0]
        self.assertEqual(jtl_out.name, 'jtl_out')
        self.assertEqual(jtl_1.name, 'jtl1')
        self.assertEqual(jtl_0.name, 'jtl0')

        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [0.0, 3.0, 4.0],
            'jtl0': [t + firing_delay for t in events['in0']],
            'jtl1': [t + firing_delay for t in events['jtl0']],
            'jtl_out': [t + firing_delay for t in events['jtl1']],
        })

    def test_c(self):
        in0_times = [2.0, 4.0, 13.0]
        in1_times = [5.0, 14.0]
        in0 = inp_at(*in0_times, name='in0')
        in1 = inp_at(*in1_times, name='in1')
        c_out = c(in0, in1, name='c_out')
        c_delay = delay(c_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': in0_times,
            'in1': in1_times,
            'c_out': [5.0 + c_delay, 14.0 + c_delay]
        })

    def test_c_inv(self):
        in0 = inp(start=2.0, period=2, n=3, name='in0')
        in1 = inp(start=18.0, period=10, n=2, name='in1')
        c_inv_out = c_inv(in0, in1, name='c_inv_out')
        c_inv_delay = delay(c_inv_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [2.0, 4.0, 6.0],
            'in1': [18.0, 28.0],
            'c_inv_out': [2.0 + c_inv_delay, 28.0 + c_inv_delay]
        })

    def test_c_inv2(self):
        in0_times = [2.0, 5.1, 9.3]
        in1_times = [10.0, 20.0]
        in0 = inp_at(*in0_times, name='in0')
        in1 = inp_at(*in1_times, name='in1')
        c_inv_out = c_inv(in0, in1, name='c_inv_out')
        c_inv_delay = delay(c_inv_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': in0_times,
            'in1': in1_times,
            'c_inv_out': [2.0 + c_inv_delay, 20.0 + c_inv_delay]
        })

    def test_c_inv3(self):
        a_times = [6.0, 10.0, 12.0]
        b_times = [2.0, 4.0, 8.0, 16.0]
        a = inp_at(*a_times, name='a')
        b = inp_at(*b_times, name='b')
        c_inv_out = c_inv(a, b, name='c_inv_out', transition_time=0)
        c_inv_delay = delay(c_inv_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'a': a_times,
            'b': b_times,
            'c_inv_out': [2.0 + c_inv_delay, 8.0 + c_inv_delay, 12.0 + c_inv_delay]
        })

    def test_c_inv_simultaneous_inputs(self):
        in0_times = [2.0, 13.0, 23.0]
        in1_times = [2.0, 12.0, 23.0]
        in0 = inp_at(*in0_times, name='in0')
        in1 = inp_at(*in1_times, name='in1')
        c_inv_out = c_inv(in0, in1, name='c_inv_out')
        c_inv_delay = delay(c_inv_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': in0_times,
            'in1': in1_times,
            'c_inv_out': [2.0 + c_inv_delay, 12.0 + c_inv_delay, 23.0 + c_inv_delay]
        })

    def test_m(self):
        in_period = [2, 3]
        in_n = [5, 2]
        in0 = inp(period=in_period[0], n=in_n[0], name='in0')
        in1 = inp(period=in_period[1], n=in_n[1], name='in1')
        m_out = m(in0, in1, name='m_out', transition_time=0)
        m_delay = delay(m_out)
        sim = Simulation()
        events = sim.simulate()
        # NOTE: There are simultaneous events on both of m's incoming ports at
        # time 6.0, and so two outputs (since it transitions and produces output
        # once for each input). When/if we had hold transition_time constraints
        # on this particular cell, this may instead be an error.
        self.assertEqual(events, {
            'in0': [i * in_period[0] for i in range(in_n[0])],
            'in1': [i * in_period[1] for i in range(in_n[1])],
            'm_out': [t + m_delay for t in sorted(events['in0'] + events['in1'])]
        })

    def test_s(self):
        in_period = 5
        in_n = 3
        in0 = inp(period=in_period, n=in_n, name='in0')
        s_out0, _s_out1 = s(in0, left_name='s_out0', right_name='s_out1')
        s_delay = delay(s_out0)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [i * in_period for i in range(in_n)],
            's_out0': [t + s_delay for t in events['in0']],
            's_out1': [t + s_delay for t in events['in0']]
        })

    def test_split(self):
        iperiod = 5.0
        n = 4
        clk = inp(period=iperiod, n=n, name='clk')
        clk1, clk2, clk3 = split(clk, 3, names='clk1 clk2 clk3')
        #   clk
        #    |
        #    s
        #   / \
        # clk1 s
        #     / \
        #   clk2 clk3
        s_delay = delay(clk1)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'clk': [i * iperiod for i in range(n)],
            'clk1': [t + s_delay for t in events['clk']],
            'clk2': [t + s_delay for t in events['clk1']],
            'clk3': [t + s_delay for t in events['clk1']],
        })

        self.assertEqual(clk1.name, 'clk1')
        self.assertEqual(clk2.name, 'clk2')
        self.assertEqual(clk3.name, 'clk3')


class TestFlipFlopCells(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_dro(self):
        in0 = inp_at(2.0, 2.5, 6.0, name='in0')
        clk = inp(start=5.3, period=6, n=3, name='clk')
        dro_out = dro(in0, clk, name='dro_out')
        dro_delay = delay(dro_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [2.0, 2.5, 6.0],
            'clk': [5.3, 11.3, 17.3],
            'dro_out': [5.3 + dro_delay, 11.3 + dro_delay]
        })

    def test_dro_sr(self):
        set = inp(start=3.0, period=3, n=2, name='set')
        rst = inp(start=7.0, period=7, n=1, name='rst')
        clk = inp(start=5.0, period=5, n=2, name='clk')
        dro_sr_out = dro_sr(set, rst, clk, name='dro_sr_out')
        dro_sr_delay = delay(dro_sr_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'set': [3.0, 6.0],
            'rst': [7.0],
            'clk': [5.0, 10.0],
            'dro_sr_out': [5.0+dro_sr_delay]
        })

    @unittest.skip("Need to check")
    def test_dro_c(self):
        in0 = inp(start=2.0, period=2, n=3, name='in0')
        clk = inp(start=5.0, period=5, n=4, name='clk')
        dro_c_out0, _dro_c_out1 = dro_c(in0, clk, name_q='dro_c_q', name_q_not='dro_c_q_not')
        dro_c_delay = delay(dro_c_out0)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [2.0, 4.0, 6.0],
            'clk': [5.0, 10.0, 15.0, 20.0],
            'dro_c_q': [15.0 + dro_c_delay, 20.0 + dro_c_delay],
            'dro_c_q_not': [5.0 + dro_c_delay, 10.0 + dro_c_delay]
        })

    @unittest.skip("Need to check")
    def test_dro_c_2(self):
        d = inp_at(50.0, name='di')
        c = inp_at(78.0, 104.0, name='ci')
        dro_c_out, _ = dro_c(d, c, name_q='out', name_q_not='nout')
        dro_c_delay = delay(dro_c_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'di': [50.0],
            'ci': [78.0, 104.0],
            'out': [104.0 + dro_c_delay],
            'nout': [78.0 + dro_c_delay],
        })


class TestSynchronousCells(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_inv_normal(self):
        # Currently testing based off of 1.2 setup time, 5.0 hold time
        # in0      |     |               |
        # clk                    |                |     |
        # time 0.0 2.0 4.0 ... 10.0 ... 16.2     20.0  30.0
        in0 = inp_at(2.0, 4.0, 16.2, name='in0')
        clk = inp(start=10.0, period=10.0, n=3, name='clk')
        inv_out = inv(in0, clk, name='inv_out')
        inv_delay = delay(inv_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [2.0, 4.0, 16.2],
            'clk': [10.0, 20.0, 30.0],
            'inv_out': [30.0 + inv_delay]
        })

    def test_inv_setup_time_violation(self):
        # Issue it's testing: that an input arrives too soon before a clock pulse.
        # Currently testing based off of 1.2 setup time, 5.0 hold time
        # in0           |
        # clk                |
        # time 0.0 4.8 5.0  6.0
        #           |--------|
        #           setup_time
        in0 = inp_at(5.0, name='in0')
        clk = inp_at(6.0, name='clk')
        _inv_out = inv(in0, clk, name='inv_out')
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            _events = sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'clk' to the node with output wire 'inv_out':\n"
            "Prior input violation on FSM 'INV'. "
            "A constraint on transition '2', triggered at time 6.0, given via "
            "the 'past_constraints' field says it is an error to trigger this transition if "
            "input 'a' was seen as recently as 1.2 time units ago. It was last seen at 5.0, which "
            "is 0.19999999999999996 time units to soon."
        )

    def test_inv_hold_time_violation(self):
        # Issue it's testing: that an input arrives too soon after a clock pulse.
        # Currently testing based off of 1.2 setup time, 5.0 hold time
        # in0      |          |
        # clk            |
        # time 0.0 1.0  3.0  6.0
        # hold_time = 5.0
        in0 = inp_at(1.0, 6.0, name='in0')
        clk = inp_at(3.0, name='clk')
        inv_out = inv(in0, clk, name='inv_out')
        inv_delay = delay(inv_out)
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            events = sim.simulate()
            self.assertEqual(events, {
                'in0': [1.0, 6.0],
                'clk': [3.0],
                'inv_out': [3.0 + inv_delay]
            })
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'a' to the node with output wire 'inv_out':\n"
            "Transition time violation on FSM 'INV'. "
            "Received input 'a' at 6.0 while still transitioning from a_arrived to idle on 'clk' (transition id '2'). "  # noqa
            "The earliest it is legal to transition is at time 8.0."
        )

    def test_inv_simultaneous_inputs(self):
        # Because of the priority defined on INV, simultaneous
        # inputs (i.e. in0 and clock) will cause an error, as is expected.
        # We want that error since it's a setup/hold time violation.
        in0 = inp_at(2.0, name='in0')
        clk = inp_at(2.0, name='clk')
        _inv_out = inv(in0, clk, name='inv_out')
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            _events = sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'a, clk' to the node with output wire 'inv_out':\n"
            "Transition time violation on FSM 'INV'. "
            "Received input 'a' at 2.0 while still transitioning from idle to idle on 'clk' (transition id '0'). "  # noqa
            "The earliest it is legal to transition is at time 7.0."
        )

    def test_and_s(self):
        in0_times = [5.0, 14.0]
        in1_times = [3.0, 6.0, 13.0]
        clk_times = [9.0, 17.0]
        in0 = inp_at(*in0_times, name='in0')
        in1 = inp_at(*in1_times, name='in1')
        clk = inp_at(*clk_times, name='clk')
        and_out = and_s(in0, in1, clk, name='and_out')
        and_s_delay = delay(and_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': in0_times,
            'in1': in1_times,
            'clk': clk_times,
            'and_out': [9.0 + and_s_delay, 17.0 + and_s_delay],
        })

    def test_and_s_setup_time_violation(self):
        in0_times = [0.0]
        in1_times = [1.0]
        clk_times = [3.5]  # comes it .5 ps too soon
        in0 = inp_at(*in0_times, name='in0')
        in1 = inp_at(*in1_times, name='in1')
        clk = inp_at(*clk_times, name='clk')
        _and_out = and_s(in0, in1, clk, name='and_out')
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            _events = sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'clk' to the node with output wire 'and_out':\n"
            "Prior input violation on FSM 'AND'. A constraint on transition '9', "
            "triggered at time 3.5, given via the 'past_constraints' field says it is "
            "an error to trigger this transition if input 'b' was seen as recently as "
            "2.8 time units ago. It was last seen at 1.0, which is 0.2999999999999998 "
            "time units to soon."
        )

    def test_or_s(self):
        in0 = inp_at(4.0, 12.0, name='in0')
        in1 = inp_at(3.0, 11.0, 18.1, name='in1')
        clk = inp_at(10.0, 18.0, 32.0, name='clk')
        or_out = or_s(in0, in1, clk, name='or_out')
        or_s_delay = delay(or_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [4.0, 12.0],
            'in1': [3.0, 11.0, 18.1],
            'clk': [10.0, 18.0, 32.0],
            'or_out': [10.0 + or_s_delay, 18.0 + or_s_delay, 32.0 + or_s_delay],
        })

    def test_or_s_2(self):
        in0 = inp_at(1.0, name='in0')
        in1 = inp_at(1.0, name='in1')
        clk = inp_at(7.0, name='clk')
        or_out = or_s(in0, in1, clk, name='or_out')
        or_s_delay = delay(or_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [1.0],
            'in1': [1.0],
            'clk': [7.0],
            'or_out': [7.0 + or_s_delay],
        })

    def test_xor_s(self):
        in0 = inp_at(5, 7, 20, 30, 40, name='in0')
        in1 = inp_at(13, 15, 25, 33, 38, name='in1')
        clk = inp_at(3, 10, 18, 23, 28, 35, 43, name='clk')
        xor_out = xor_s(in0, in1, clk, name='xor_out', transition_time=0, past_constraints=0)
        xor_s_delay = delay(xor_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [5.0, 7.0, 20.0, 30.0, 40.0],
            'in1': [13.0, 15.0, 25.0, 33.0, 38.0],
            'clk': [3.0, 10.0, 18.0, 23.0, 28.0, 35.0, 43.0],
            'xor_out': [10.0 + xor_s_delay, 18.0 + xor_s_delay,
                        23.0 + xor_s_delay, 28.0 + xor_s_delay],
        })

    def test_nand_s(self):
        in0 = inp_at(0, 75, name='in0')
        in1 = inp_at(85, name='in1')
        clk = inp_at(50, 100, 150, name='clk')
        nand_out = nand_s(in0, in1, clk, name='nand_out')
        nand_delay = delay(nand_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [0, 75],
            'in1': [85],
            'clk': [50, 100, 150],
            'nand_out': [50 + nand_delay, 150 + nand_delay],
        })

    def test_xnor_s(self):
        in0 = inp_at(0, 75, name='in0')
        in1 = inp_at(85, name='in1')
        clk = inp_at(50, 100, 150, name='clk')
        xnor_out = xnor_s(in0, in1, clk, name='xnor_out')
        xnor_delay = delay(xnor_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [0, 75],
            'in1': [85],
            'clk': [50, 100, 150],
            'xnor_out': [100 + xnor_delay, 150 + xnor_delay],
        })

    def test_nor_s(self):
        in0 = inp_at(0, 75, name='in0')
        in1 = inp_at(85, name='in1')
        clk = inp_at(50, 100, 150, name='clk')
        nor_out = nor_s(in0, in1, clk, name='nor_out')
        nor_delay = delay(nor_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0': [0, 75],
            'in1': [85],
            'clk': [50, 100, 150],
            'nor_out': [150 + nor_delay],
        })


class TestCombinations(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_medium(self):
        i1 = inp(name="in1")
        i2 = inp(name="in2")
        j = jtl(i1, name="j0")
        for n in range(4):
            j = jtl(j, name="j%d" % (n+1))
        jdelay = delay(j)
        merge_out = m(i2, j, name="m_out")
        mdelay = delay(merge_out)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in1': [0.0],
            'in2': [0.0],
            'j0': [(t + jdelay) for t in events['in1']],
            'j1': [(t + jdelay) for t in events['j0']],
            'j2': [(t + jdelay) for t in events['j1']],
            'j3': [(t + jdelay) for t in events['j2']],
            'j4': [(t + jdelay) for t in events['j3']],
            'm_out': [(t + mdelay) for t in (events['in2'] + events['j4'])],
        })

    def test_with_arbitrary_inputs(self):
        ins1_times = [0.0, 1.0, 4.0, 13.0]
        ins2_times = [1.0, 6.0, 8.0]
        ins11, ins12 = split(inp_at(*ins1_times, name='ins1'), 2, transition_time=0)
        ins21, ins22 = split(inp_at(*ins2_times, name='ins2'), 2, transition_time=0)
        _c = c(ins11, ins21, name='c', transition_time=0)
        _m = m(ins12, ins22, name='m', transition_time=0)
        delay1 = delay(_c) + delay(ins11)
        delay2 = delay(_m) + delay(ins11)
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'ins1': ins1_times,
            'ins2': ins2_times,
            'c': [1.0 + delay1, 6.0 + delay1, 13.0 + delay1],  # Note, the 4.0 from ins1 is ignored
            # Note, 2nd 1.0 + md was previously dropped
            'm': [0.0 + delay2, 1.0 + delay2, 1.0 + delay2,
                  4.0 + delay2, 6.0 + delay2, 8.0 + delay2, 13.0 + delay2]
        })


class TestVariableDelays(unittest.TestCase):
    min_factor = 0.8
    max_factor = 1.2

    def setUp(self):
        working_circuit().reset()

    def check_valid(self, value, time, delay, lower_factor=min_factor, upper_factor=max_factor):
        self.assertTrue(value >= (time + delay) * lower_factor)
        self.assertTrue(value <= (time + delay) * upper_factor)

    @unittest.skip("This fails...ocassionally, which is telling since we're testing variability.")
    def test_variability_c_element(self):
        i = inp_at(1.0, 13.0)
        j = inp_at(2.0, 10.0)
        _c = c(i, j, name='c')
        c_delay = delay(_c)
        sim = Simulation()
        events = sim.simulate(variability=True)
        self.assertEqual(len(events['c']), 2)
        self.check_valid(events['c'][0], 2.0, c_delay)
        self.check_valid(events['c'][1], 10.0, c_delay)

    def test_variability_c_inv_element(self):
        i = inp_at(6.0, 10.0, 12.0)
        j = inp_at(2.0, 4.0, 8.0, 16.0)
        _c = c_inv(i, j, name='c_inv', transition_time=0)
        c_inv_delay = delay(_c)
        sim = Simulation()
        events = sim.simulate(variability=True)
        self.assertEqual(len(events['c_inv']), 3)
        self.check_valid(events['c_inv'][0], 2.0, c_inv_delay)
        self.check_valid(events['c_inv'][1], 8.0, c_inv_delay)
        self.check_valid(events['c_inv'][2], 12.0, c_inv_delay)

    def test_variability_m_element(self):
        i = inp_at(1.0, 10.0)
        j = inp_at(2.0, 8.0)
        _m = m(i, j, name='m', transition_time=0)
        m_delay = delay(_m)
        sim = Simulation()
        events = sim.simulate(variability=True)
        self.assertEqual(len(events['m']), 4)
        self.check_valid(events['m'][0], 1.0, m_delay)
        self.check_valid(events['m'][1], 2.0, m_delay)
        self.check_valid(events['m'][2], 8.0, m_delay)
        self.check_valid(events['m'][3], 10.0, m_delay)

    def test_variability_jtl_element(self):
        i = inp_at(1.0, 10.0)
        _j = jtl(i, name='j')
        j_delay = delay(_j)
        sim = Simulation()
        events = sim.simulate(variability=True)
        self.assertEqual(len(events['j']), 2)
        self.check_valid(events['j'][0], 1.0, j_delay)
        self.check_valid(events['j'][1], 10.0, j_delay)

    def test_variability_custom_function(self):
        def custom_variability(delay, _node):
            factor = random.uniform(0.5, 1.5)
            return delay * factor

        i = inp_at(1.0, 10.0)
        _j = jtl(i, name='j')
        j_delay = delay(_j)
        sim = Simulation()
        events = sim.simulate(variability=custom_variability)
        self.assertEqual(len(events['j']), 2)
        self.check_valid(events['j'][0], 1.0, j_delay, lower_factor=0.5, upper_factor=1.5)
        self.check_valid(events['j'][1], 10.0, j_delay, lower_factor=0.5, upper_factor=1.5)


class TestFakeSFQForTimeConstraints(unittest.TestCase):
    def setUp(self):
        working_circuit().reset()

    def test_default_transition_time_automatically_added(self):
        class Simple(SFQ):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'a', 'dest': 's1'},
                {'id': '1', 'source': 's1', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'transition_time': 'default'},
            ]
            jjs = 2
            transition_time = 2.7  # Will be automatically added to transition '1'
            name = 'Simple'
            firing_delay = 0.0

        i = inp_at(0.0, 3.0, name='i')
        o = Wire('o')
        s = Simple()
        self.assertEqual(s.get_transition_by_id('1').transition_time, 2.7)
        working_circuit().add_node(s, [i], [o])
        sim = Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'i': [0.0, 3.0],
            'o': [3.0],
        })

    def test_input_arrives_during_transition(self):
        class Simple(SFQ):
            inputs = ['a']
            outputs = ['q']
            transitions = [
                {'id': '0', 'source': 'idle', 'trigger': 'a', 'dest': 's1'},
                {'id': '1', 'source': 's1', 'trigger': 'a', 'dest': 'idle',
                 'firing': 'q', 'transition_time': 'default'},
            ]
            jjs = 4
            transition_time = 2.7  # Auto addeded to transition '1'
            name = 'Simple'
            firing_delay = 1.0

        i = inp_at(0.0, 2.0, 3.0)
        o = Wire('o')
        working_circuit().add_node(Simple(), [i], [o])
        sim = Simulation()
        with self.assertRaises(PylseError) as ex:
            sim.simulate()
        self.assertEqual(
            str(ex.exception),
            "Error while sending input(s) 'a' to the node with output wire 'o':\n"
            "Transition time violation on FSM 'Simple'. Received input 'a' at 3.0 while still "
            "transitioning from s1 to idle on 'a' (transition id '1'). The earliest it is legal "
            "to transition is at time 4.7."
        )


if __name__ == '__main__':
    unittest.main()
