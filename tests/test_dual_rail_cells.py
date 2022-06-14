import unittest

import pylse
try:
    from .test_sfq_cells import delay
except ImportError:
    from test_sfq_cells import delay


class TestDualRail(unittest.TestCase):
    def setUp(self):
        pylse.working_circuit().reset()

    def test_join(self):
        in0_t = pylse.inp(start=2.0, period=2.0, n=1, name='in0_t')
        in0_f = pylse.inp(start=6.0, period=6.0, n=2, name='in0_f')
        in1_t = pylse.inp(start=4.0, period=4.0, n=2, name='in1_t')
        in1_f = pylse.inp(start=10.0, period=10.0, n=1, name='in1_f')
        join_out00, _join_out01, _join_out10, _join_out11 = \
            pylse.join(in0_t, in0_f, in1_t, in1_f,
                       name_q00='join_out00', name_q01='join_out01',
                       name_q10='join_out10', name_q11='join_out11')
        join_delay = delay(join_out00)
        sim = pylse.Simulation()
        events = sim.simulate()
        self.assertEqual(events, {
            'in0_t': [2.0],
            'in0_f': [6.0, 12.0],
            'in1_t': [4.0, 8.0],
            'in1_f': [10.0],
            'join_out00': [12.0 + join_delay],
            'join_out01': [8.0 + join_delay],
            'join_out10': [],
            'join_out11': [4.0 + join_delay]
        })

    def test_join_2(self):
        # A_T                                      |               |       |               |
        # A_F |          |     |            |
        # B_T                     |     |                                      |       |
        # B_F    |     |                                |       |
        # Q00      |        |
        # Q01                        |         |
        # Q10                                               |          |
        # Q11                                                                       |            |
        #     0 10 20 30 40 50 60 70 80 90 100 110 120 130 140 150 160 170 180 190 200 210 220 230
        in0_t = pylse.inp_at(120, 160, 180, 220, name='A_T')
        in0_f = pylse.inp_at(0, 40, 60, 100, name='A_F')
        in1_t = pylse.inp_at(70, 90, 190, 210, name='B_T')
        in1_f = pylse.inp_at(10, 30, 130, 150, name='B_F')
        join_out00, _join_out01, _join_out10, _join_out11 = \
            pylse.join(in0_t, in0_f, in1_t, in1_f,
                 name_q00='Q00', name_q01='Q01',
                 name_q10='Q10', name_q11='Q11')
        join_delay = pylse.delay(join_out00)
        assert isinstance(join_delay, float)

        sim = pylse.Simulation()
        events = sim.simulate()
        self.assertEqual(events['Q00'], [t + join_delay for t in [10, 40]])
        self.assertEqual(events['Q01'], [t + join_delay for t in [70, 100]])
        self.assertEqual(events['Q10'], [t + join_delay for t in [130, 160]])
        self.assertEqual(events['Q11'], [t + join_delay for t in [190, 220]])
        # assert that the every pairs contains one and only one of (one of: a_t, a_f) and a b (one of: b_t, b_f)
        inputs = sorted(((w, p) for w, evs in events.items()
            for p in evs if w in ('A_T', 'A_F', 'B_T', 'B_F')),
            key=lambda x: x[1])
        zipped = list(zip(inputs[0::2], inputs[1::2]))
        self.assertTrue(all(x[0] != y[0] for x, y in zipped))

        # Q00 pulses only if A_F and B_F arrived (in any order)
        # Q01 pulses only if A_F and B_T arrived (in any order)
        # Q10 pulses only if A_T and B_F arrived (in any order)
        # Q11 pulses only if A_T and B_T arrived (in any order)
        outputs = sorted(((w, p) for w, evs in events.items()
            for p in evs if w in ('Q00', 'Q01', 'Q10', 'Q11')),
            key=lambda x: x[1])
        def to_output(*names):
            x, y = sorted(names)
            return {
                ('A_F', 'B_F'): 'Q00',
                ('A_F', 'B_T'): 'Q01',
                ('A_T', 'B_F'): 'Q10',
                ('A_T', 'B_T'): 'Q11',
            }[(x, y)]
        self.assertEqual([w[0] for w in outputs], [to_output(x[0], y[0]) for x, y in zipped])

if __name__ == "__main__":
    unittest.main()
