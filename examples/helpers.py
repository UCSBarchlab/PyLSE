from collections import defaultdict
import os
import re
import subprocess
import timeit
import unittest

import pylse

UPPAAL_dir = "uppaal"
Log_file = "results.txt"
Log = None
N_times = 5  # number of times to simulate, when we're timing the simulation

S_delay = 11
C_delay = 12
C_inv_delay = 14

def print_cell_info():
    circuit = pylse.working_circuit()
    nodes = set(node for node in circuit.nodes
        if not isinstance(node.element, (pylse.circuit.InGen,
                                         pylse.circuit._Source,
                                         pylse.circuit._Sink)))
    total_cells = len(nodes)
    print(f"# of cells: {total_cells}")                            
    def get_states(el):
        states = set()
        if isinstance(el, pylse.Functional):
            # Not "states" for a functional element
            return set()
        else:
            for t in el.transitions:
                states.add(t.source)
                states.add(t.destination)
            return states
    total_states = sum(len(get_states(n.element)) for n in nodes)
    print(f"# total states: {total_states}")

    def get_transitions(el):
        if isinstance(el, pylse.Functional):
            # No "transitions" for a functional element
            return []
        else:
            return el.transitions
    total_transitions = sum(len(get_transitions(n.element)) for n in nodes)
    print(f"# total transitions (fully expanded): {total_transitions}")

    return total_cells, total_states, total_transitions

def print_ta_info(ta):
    print("Total TA system: ")
    print(f"# templates: {len(ta.templates)}")
    print(f"# ta instances (including inpAt and Sink): {len(ta.instances)}")
    print(f"# channels: {len(ta.channels)} (including to Sink)")

    total_locations = 0  # not including inpAt, Sink locations
    total_transitions = 0  # not including transitions to/from inpAt, Sink locations
    total_instances = 0  # not including inpAt, Sink instances
    for template in ta.templates:
        nlocs = len(template.locations)
        ntrans = len(template.transitions)
        print(f"\t# {template.name} tas: {ta.cell_ctr[template.name]}")
        print(f"\t\t# locations: {nlocs}")
        print(f"\t\t# transitions: {ntrans}")
        if template.name == 'Sink' or template.name.startswith('inpAt'):
            continue
        total_locations += ta.cell_ctr[template.name] * nlocs
        total_transitions += ta.cell_ctr[template.name] * ntrans
        total_instances += ta.cell_ctr[template.name]

    total_channels = len(ta.channels) - len(ta.circuit.outputs)  # i.e. not to Sink

    print(f"# ta instances: {total_instances}")
    print(f"# locations: {total_locations}")
    print(f"# transitions: {total_transitions}")
    print(f"# channels: {total_channels}")

    return total_instances, total_locations, total_transitions, total_channels

def check_ta_query(ta_file_name, query_file_name):

    def is_satisfied(output):
        satisfied_line = [line for line in output.split('\n') if 'Formula is' in line]
        assert len(satisfied_line) == 1
        if 'Formula is satisfied' in satisfied_line[0]:
            return True
        elif 'Formula is NOT satisfied' in satisfied_line[0]:
            return False
        else:
            raise Exception(f"Could not parse output: {satisfied_line}")
    
    out = subprocess.check_output(
        ["verifyta", "-u", "-q", ta_file_name, query_file_name], encoding='UTF-8')
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    out = ansi_escape.sub('', out)
    return is_satisfied(out), out

def sim_and_gen(name, variability=None, view=True, get_average_sim=None, negative=False,
                wires_to_display=None, call_verify=True, create_ta=True, exact=True):
    print("\n*********************************")
    name = name + ("_var" if variability else "")
    print(name)

    # Run simulation...
    sim = pylse.Simulation()
    times = []
    events = None  # to appease the type-checker
    n_times = get_average_sim or 1
    assert n_times > 0
    for i in range(n_times):
        try:
            ts = timeit.default_timer()
            events = sim.simulate(variability=variability)
            te = timeit.default_timer()
            time = te - ts
            times.append(time)
        except pylse.PylseError as e:
            print(f"Error during run {i}: {e}") 
        else:
            if n_times > 1:
                print(f"Simulation time for run {i}: {time}")
    if n_times > 1:
        print(f"Average simulation time: {sum(times)/len(times)}")
    elif n_times == 0:
        print(f"Sim time: {times[0]}")
    else:
        pass

    pylse_cells, pylse_states, pylse_trans = print_cell_info()

    if view:
        sim.plot(wires_to_display=wires_to_display)

    assert events is not None
    print("Events:")
    for w_name, pulses in sorted(events.items(), key=lambda x: x[0]):
        print(f"\t{w_name}: {pulses}")

    if not os.path.isdir(UPPAAL_dir):
        print(f"No {UPPAAL_dir} directory found, skipping storage of timed automata")
        return events, None

    ta_file_name = f"{UPPAAL_dir}/{name}.xml"
    ta = pylse.export_to_uppaal(ta_file_name) if create_ta else None

    if ta is None:
        return events, ta

    # UPPAAL-related
    uppaal_ta, uppaal_locs, uppaal_trans, _uppaal_chans = print_ta_info(ta)

    print(f"# TA/Cells: {round(uppaal_ta / pylse_cells, 2)}")
    print(f"# States/Locations: {round(uppaal_locs / pylse_states, 2)}")
    print(f"# Transitions (PyLSE)/Transitions (UPPAAL): {round(uppaal_trans / pylse_trans, 2)}")

    # Queries:
    query1 = pylse.generate_correctness_query(ta, events, exact=exact)
    print("Correctness query:")
    print(query1)
    query_file_name_correctness = f"{UPPAAL_dir}/{name}_correctness.q"
    with open(query_file_name_correctness, "w") as f:
        f.write(query1)

    # Generate more queries here...
    query2 = pylse.generate_error_reachability_query(ta, events)
    reachable_prefix = "" if negative else "un"
    print(f"Error reachability query (errors {reachable_prefix}reachable)")
    print(query2)
    query_file_name_reachability = f"{UPPAAL_dir}/{name}_{reachable_prefix}reachability.q"
    with open(query_file_name_reachability, "w") as f:
        f.write(query2)

    if call_verify:
        sat, out = check_ta_query(ta_file_name, query_file_name_correctness)
        print(f"Correctness? {'Y' if sat else 'N'}") 
        print(out)

        sat, out = check_ta_query(ta_file_name, query_file_name_reachability)
        print(f"Errors {reachable_prefix}reachable? {'Y' if sat else 'N'}") 
        print(out)

    else:
        print("Not verifying; run it manually via:")
        print(f"verifyta -u -q {ta_file_name} {query_file_name_correctness}")
        print(f"verifyta -u -q {ta_file_name} {query_file_name_reachability}")

    return events, ta # in case you want to do other assertion tests or generate more uppaal queries

def pulse_in_period(n, period_length, events, offset=0):
    # v: value to check for
    # n: period number
    start = n * period_length - offset
    end = start + period_length
    items = [i for i in events if i >= start and i < end]
    if len(items) == 0:
        return False
    elif len(items) == 1:
        return True
    else:
        raise Exception(f"There should be at most one pulse in period {n}.")

class BaseTest(unittest.TestCase):
    def setUp(self):
        pylse.working_circuit().reset()
