import pylse
from helpers import BaseTest, sim_and_gen

from collections import defaultdict
import unittest

class TestHole(BaseTest):
    def test_memory(self):
        # 4x2 memory: (16 address, each storing 2 bits)
        mem = defaultdict(lambda: 0)
        raddr = 0
        waddr = 0
        wenable = 0
        data = 0

        # We update the address first, if the clock is high.
        # We return the old value before updating it, if 'we' is high.
        @pylse.hole(delay=5.0, inputs=['ra3', 'ra2', 'ra1', 'ra0',
                                       'wa3', 'wa2', 'wa1', 'wa0', 'd1', 'd0', 'we', 'clk'],
                    outputs=['q1', 'q0'])
        def memory(ra3, ra2, ra1, ra0, wa3, wa2, wa1, wa0, d1, d0, we, clk, time):
            nonlocal raddr, waddr, wenable, data
            raddr |= ra3*8 + ra2*4 + ra1*2 + ra0
            waddr |= wa3*8 + wa2*4 + wa1*2 + wa0
            data |= d1*2 + d0
            wenable |= we
            if clk:
                # print(f"clk at time {time}!")
                # print(f"raddr: {raddr}")
                # print(f"waddr: {waddr}")
                # print(f"wenable: {wenable}")
                # print(f"data: {data}")
                # print(f"mem: {mem}")
                if wenable:
                    mem[waddr] = data
                value = mem[raddr]
                raddr = 0
                waddr = 0
                wenable = 0
                data = 0
            else:
                value = 0
            # print(f"value: {value}")
            return ((value >> 1) & 1), value & 1

        # ra[3:0] 0b1010    0b0011     0b0110     0b1111    0b0000    0b0001
        #  ra3    |                                 |
        #  ra2                          |          |
        #  ra1      |          |          |            |
        #  ra0                |                           |             |
        # wa[3:0] 0b0011    0b1111     0b0000     0b0001    0b0010    0b1001
        #  wa3                  |                                      |
        #  wa2                   |
        #  wa1     |           |                            |
        #  wa0    |          |                     |                      |
        # d[1:0]
        #  d1     |                     |           |
        #  d0                   |       |             |        |
        # we            |      |                   |
        # q[1:0]   0b00       0b10      0b00       0b01      0b00      0b11
        #  q1               |                                       |
        #  q0                                   |                   |
        # clk               |         |         |         |         |         |
        # t      0         50        100       150       200       250       300
        ra3 = pylse.inp_at(0, 160, name='ra3')
        ra2 = pylse.inp_at(110, 155, name='ra2')
        ra1 = pylse.inp_at(30, 72, 115, 161, name='ra1')
        ra0 = pylse.inp_at(53, 200, 275, name='ra0')
        wa3 = pylse.inp_at(67, 266, name='wa3')
        wa2 = pylse.inp_at(71, 266, name='wa2')
        wa1 = pylse.inp_at(8, 60, 210, 280, name='wa1')
        wa0 = pylse.inp_at(0, 55, 162, name='wa0')
        d1 = pylse.inp_at(3, 112, 165, name='d1')
        d0 = pylse.inp_at(75, 112, 188, 230, name='d0')
        we = pylse.inp_at(35, 53, 162, name='we')
        clk = pylse.inp(start=50, period=50, n=6, name='clk')
        q1, q0 = memory(ra3, ra2, ra1, ra0, wa3, wa2, wa1, wa0, d1, d0, we, clk)
        pylse.inspect(q1, 'q1')
        pylse.inspect(q0, 'q0')
        sim = pylse.Simulation()
        events = sim.simulate()
        ordered_outputs = ['ra3', 'ra2', 'ra1', 'ra0', 'wa3', 'wa2', 'wa1', 'wa0',
                           'd1', 'd0', 'we', 'q1', 'q0', 'clk']
        sim.plot(wires_to_display=ordered_outputs)
        delay = 5.0
        self.assertEqual(events['q1'], [t + delay for t in (100, 300)])
        self.assertEqual(events['q0'], [t + delay for t in (200, 300)])
        sim_and_gen('hole-memory', create_ta=False)

if __name__ == "__main__":
    unittest.main()
