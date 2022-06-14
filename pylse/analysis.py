from typing import List, Union, Set
from warnings import warn

from .circuit import working_circuit
from .core import Wire, Node
from .transitional import NormalizedTransition, Transitional
from .pylse_exceptions import PylseError


def output_name(wire):
    """ Gets the name of element output of the node from which this wire originates """
    node = working_circuit()._src_map[wire]
    output_ix = node.output_wires.index(wire)
    output_name = node.element.outputs[output_ix]
    return output_name


def delay(wire) -> Union[float, Set[float]]:
    """ It may be that multiple transitions fire this output, and each may
        have a different firing delay. We return warning and set of delays
        in that case. Note that this doesn't take into account any variability
        that may exist when you run the simulation with variability turned on.
    """
    node = working_circuit()._src_map[wire]
    oname = output_name(wire)
    delays = set()
    assert isinstance(node.element, Transitional)
    for t in node.element.transitions:
        assert isinstance(t, NormalizedTransition)
        for wn, d in t.firing.items():
            if wn == oname:
                delays.add(d)
    if not delays:
        raise PylseError(
            f"No delay found for wire {wire} named {wire.name} (is it connected to a node?)"
        )
    if len(delays) == 1:
        return delays.pop()
    else:
        warn("Returning multiple delays for wire {}".format(wire.name))
        return delays


def critical_path(clk_wire, circuit=None):
    pass


def paths(src: Wire, dst: Wire, circuit=None) -> List[List[Node]]:
    # Untested
    dst_nets = working_circuit(circuit).dst_map

    paths = []

    # Use DFS to get the paths [each a list of nets] from src wire to dst wire
    def dfs(w, curr_path):
        if w is dst:
            # Found valid path
            paths.append(curr_path)
        for dst_node in dst_nets.get(w, []):
            # Avoid loops?
            if dst_node not in curr_path:
                for o in dst_node.output_wires:
                    dfs(o, curr_path + [dst_node])
    dfs(src, [])
    return paths


def path_delay(src: Wire, dest: Wire, circuit=None):
    """ Get the propagation delay """
    ps = paths(src, dest, circuit)
    ds = [sum(n.element.transition_time) for p in ps for n in p]
    return max(*ds)
