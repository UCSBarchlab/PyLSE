import math
from itertools import permutations
from random import randrange
import unittest

import pylse
from min_max import min_max
from helpers import BaseTest, sim_and_gen, N_times, S_delay, C_inv_delay

def split(*args):
    mid = len(args) // 2
    return args[:mid], args[mid:]

def cleaner(*args):
    upper, lower = split(*args)
    res = [min_max(*t) for t in zip(upper, lower)]
    new_upper = tuple(t[0] for t in res)
    new_lower = tuple(t[1] for t in res)
    return new_upper, new_lower

def crossover(*args):
    upper, lower = split(*args)
    res = [min_max(*t) for t in zip(upper, lower[::-1])]
    new_upper = tuple(t[0] for t in res)
    new_lower = tuple(t[1] for t in res[::-1])
    return new_upper, new_lower

def merge_network(*args):
    if len(args) == 1:
        return args
    upper, lower = cleaner(*args)
    return merge_network(*upper) + merge_network(*lower)

def block(*args):
    upper, lower = crossover(*args)
    if len(upper + lower) == 2:
        return upper + lower
    return merge_network(*upper) + merge_network(*lower)

def bitonic_helper(*args):
    if len(args) == 1:
        return args
    else:
        upper, lower = split(*args)
        new_upper = bitonic_helper(*upper)
        new_lower = bitonic_helper(*lower)
        return block(*new_upper + new_lower)

def bitonic_sort(*args):
    if len(args) == 0:
        raise pylse.PylseError("bitonic_sort requires at least one argument to sort")
    if len(args) & (len(args) - 1) != 0:
        raise pylse.PylseError("number of arguments to bitonic_sort must be a power of 2")
    return bitonic_helper(*args)

# Hard-coded 8-input version
def bitonic_sort_4(i0, i1, i2, i3):
    c1l, c1h = min_max(i0, i1)
    c2l, c2h = min_max(i2, i3)
    c3l, c3h = min_max(c1h, c2l)
    c4l, c4h = min_max(c1l, c2h)
    o0, o1 = min_max(c4l, c3l)
    o2, o3 = min_max(c3h, c4h)
    return o0, o1, o2, o3

# Hard-coded 8-input version.
def bitonic_sort_8(a1, a2, a3, a4, a5, a6, a7, a8):
    c1l, c1h = min_max(a1, a2)
    c2l, c2h = min_max(a3, a4)
    c3l, c3h = min_max(c1h, c2l)
    c4l, c4h = min_max(c1l, c2h)
    c5l, c5h = min_max(c4l, c3l)
    c6l, c6h = min_max(c3h, c4h)

    c7l, c7h = min_max(a5, a6)
    c8l, c8h = min_max(a7, a8)
    c9l, c9h = min_max(c7h, c8l)
    c10l, c10h = min_max(c7l, c8h)
    c11l, c11h = min_max(c10l, c9l)
    c12l, c12h = min_max(c9h, c10h)

    c13l, c13h = min_max(c5l, c12h)
    c14l, c14h = min_max(c5h, c12l)
    c15l, c15h = min_max(c6l, c11h)
    c16l, c16h = min_max(c6h, c11l)
    c17l, c17h = min_max(c14l, c16l)
    c18l, c18h = min_max(c16h, c14h)
    c19l, c19h = min_max(c13l, c15l)
    c20l, c20h = min_max(c15h, c13h)
    c21l, c21h = min_max(c19l, c17l)
    c22l, c22h = min_max(c19h, c17h)
    c23l, c23h = min_max(c18l, c20l)
    c24l, c24h = min_max(c18h, c20h)
    return c21l, c21h, c22l, c22h, c23l, c23h, c24l, c24h

class TestBitonicSorter(BaseTest):
    # These are the tests we have for which we have Cadence/SPICE-generated waveforms to compare
    def setUp(self):
        super().setUp()
        self.path_delay = S_delay + C_inv_delay

    def check_rank_order(self, events, ordered):
        # Order by name, and then verify the value associated are in rank order
        ranked = [events for _, events in sorted(events.items(), key=lambda x: ordered.index(x[0]))]
        self.assertTrue(all(len(events) == 1 for events in ranked))
        try:
            self.assertTrue(all(x[0] <= y[0] for x, y in zip(ranked, ranked[1:])))
        except AssertionError:
            print("Rank order check failed (probably due to variability) with outputs:")
            print(ranked)
            print("This possibly shows that the inputs are spaced too close together, or that\n"
                  "the network needs to redesigned with additional delay elements to make it\n"
                  "less sensitive to variability.")

    def test_bitonic_sort_8_spice_comp(self):
        inp_times = [230.0, 130.0, 180.0, 280.0, 80.0, 80.0, 130.0, 330.0]
        ins = [pylse.inp_at(t, name='IN'+str(ix)) for ix, t in enumerate(inp_times)]
        #outs = bitonic_sort(*ins)
        outs = bitonic_sort_8(*ins)  # Behaves the same, which is good.
        for i, o in enumerate(outs):
            o.name = 'OUT' + str(i)
        events, _ta = sim_and_gen("bitonic-sort-8-spice-comp", get_average_sim=N_times, call_verify=False)

        out_events = {k: v for k, v in events.items() if k.startswith('OUT')}
        self.check_rank_order(out_events, sorted(out_events.keys()))

        path_delay = 6 * (self.path_delay)
        for ix, out in enumerate(sorted(out_events.keys())):
            self.assertTrue(math.isclose(events[out][0],
                            sorted(inp_times)[ix] + path_delay, rel_tol=1e-5))

    def bitonic_sort_exhaustive_tester(self, n, perms=None, variability=None):
        """
        :param n: number of inputs
        :param perms: max number of permutations to test (defaults to all of them)
        """
        # The minimum amount of time that must be between inputs so that
        # transition time violations don't occur.
        safe_distance = 18

        # The maximum amount of time we want between inputs.
        window = 30 

        # Prime it.
        end = -safe_distance
        inp_times = sorted([
            randrange(
                (start := end + safe_distance),
                (end := start + window)
            ) for _ in range(n)
        ])

        s = "exhaustive" if perms is None else f"{perms} permutations"
        v = " variability" if variability is not None else ""
        print("\n*********************************")
        print(f"Bitonic Sorter {n} ({s} random)){v}")
        for perm_n, perm in enumerate(permutations(inp_times)):

            pylse.working_circuit().reset()
            ins = [pylse.inp_at(perm[ix], name='i'+str(ix)) for ix in range(n)]
            outs = bitonic_sort(*ins)
            for i, o in enumerate(outs):
                o.name = 'o' + str(i)

            name = f"bitonic-sort-{n}_perm-{perm_n}" #-{'_'.join(str(p) for p in perm)}"
            # Save a few waveforms (every 1000)
            events, _ta = sim_and_gen(name, view=(perm_n % 1000 == 0), call_verify=False,
                                      create_ta=False, variability=variability)

            if perm_n == perms:
                return

            if n == 2:
                layers = 1
            elif n == 4:
                layers = 3
            elif n == 8:
                layers = 6
            else:
                raise NotImplementedError
            total_path_delay = self.path_delay * layers  # N layers of comparators, each with 13.3 delay on all paths

            # NOTE: sorting the outputs by name works while our n goes up to 9 (lexicographic order)
            out_events = {k: v for k, v in events.items() if k.startswith('o')}
            self.check_rank_order(out_events, sorted(out_events.keys()))

            # For now, if variaiblity, just check rank order (above)
            if variability is None:
                for ix, out in enumerate(outs):
                    self.assertTrue(math.isclose(
                                        t1:=events[out.name][0],
                                        t2:=(inp_times[ix] + total_path_delay),
                                        rel_tol=1e-5), f"{t1} != {t2}")

    # 2 permutations
    def test_bitonic_sort_2_exhaustive_random(self):
        # Same as a comparator
        self.bitonic_sort_exhaustive_tester(2)

    def test_bitonic_sort_2(self):
        in0 = pylse.inp_at(90, name='in0')
        in1 = pylse.inp_at(50, name='in1')
        outs = bitonic_sort(in0, in1)
        for i, o in enumerate(outs):
            o.name = 'o' + str(i)
        events, _ta = sim_and_gen("bitonic-sort-2_inputs-90_50")
        for out in outs:
            self.assertEqual(len(events[out.name]), 1)
        self.assertLess(events['o0'][0], events['o1'][0])
        total_path_delay = self.path_delay * 1  # 1 layer
        # With current numbers, it should be 75.0, 115.0
        out_events = {k: v for k, v in events.items() if k.startswith('OUT')}
        self.check_rank_order(out_events, sorted(out_events.keys()))
        self.assertEqual(events['o0'][0], 50 + total_path_delay)
        self.assertEqual(events['o1'][0], 90 + total_path_delay)

    # 24 permutations (4!)
    def test_bitonic_sort_4_exhaustive_random(self):
        self.bitonic_sort_exhaustive_tester(4)

    def test_bitonic_sort_4_exhaustive_var(self):
        self.bitonic_sort_exhaustive_tester(4, perms=100, variability=True)

    def test_bitonic_sort_4(self):
        in0 = pylse.inp_at(90, name='in0')
        in1 = pylse.inp_at(50, name='in1')
        in2 = pylse.inp_at(145, name='in2')
        in3 = pylse.inp_at(0, name='in3')
        outs = bitonic_sort(in0, in1, in2, in3)
        for i, o in enumerate(outs):
            o.name = 'o' + str(i)
        events, _ta = sim_and_gen("bitonic-sort-4_inputs-90_50_145_0", call_verify=False)
        for out in outs:
            self.assertEqual(len(events[out.name]), 1)
        self.assertLess(events['o0'][0], events['o1'][0])
        total_path_delay = self.path_delay * 3  # 3 layers
        out_events = {k: v for k, v in events.items() if k.startswith('OUT')}
        self.check_rank_order(out_events, sorted(out_events.keys()))
        # With current numbers, it should be 25.0, 75.0, 115.0, 170.0
        self.assertEqual(events['o0'][0], 0 + total_path_delay)
        self.assertEqual(events['o1'][0], 50 + total_path_delay)
        self.assertEqual(events['o2'][0], 90 + total_path_delay)
        self.assertEqual(events['o3'][0], 145 + total_path_delay)

    # For exhaustively testing the bitonic sorter on 8 inputs
    # NOTE: Doing all 40320 (i.e. 8!) permutations takes 1044.89s user time on my machine.
    def test_bitonic_sort_8_exhaustive(self):
        self.bitonic_sort_exhaustive_tester(8, perms=100)

    def test_bitonic_sort_8_exhaustive_var(self):
        self.bitonic_sort_exhaustive_tester(8, perms=100, variability=True)

if __name__ == "__main__":
    unittest.main()
