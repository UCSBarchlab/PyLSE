from typing import List, Dict, Set, Optional, Union
from collections import defaultdict

from .core import Node, Wire, Element
from .transitional import Transitional
from .pylse_exceptions import PylseError


class Circuit:
    ''' Holds information about the circuit being constructed '''

    def __init__(self):
        self._initialize()

    def reset(self):
        self._initialize()
        Wire._reset_wire_id()
        Node._reset_node_id()

    def __iter__(self):
        src_nodes = [] if self._source_wire is None else [self.src_map[self._source_wire]]
        # src_nodes = self.dst_map[self._source_wire]  # Do this to hide the implicit _Source node
        seen = set()

        while src_nodes:
            src_node, src_nodes = src_nodes[0], src_nodes[1:]
            if src_node in seen:
                continue
            seen.add(src_node)
            yield(src_node)

            for w in src_node.output_wires:
                ns = self.dst_map[w]
                src_nodes.extend(ns)

    def _initialize(self):
        self.nodes: Set[Node] = set()
        self.wires: Set[Wire] = set()
        self._source_wire = None
        self._sink_node = None
        # The following are for efficiency:
        self._wire_by_name: Dict[str, Wire] = {}
        self._src_map: Dict[Wire, Node] = {}
        self._dst_map: Dict[Wire, List[Node]] = defaultdict(list)

    # Hide both of these since they should only be updated internally
    @property
    def src_map(self):
        return self._src_map

    @src_map.setter
    def src_map(self, _):
        raise PylseError("Cannot explicitly set the circuit's src_map")

    @property
    def dst_map(self):
        return self._dst_map

    @dst_map.setter
    def dst_map(self, _):
        raise PylseError("Cannot explicitly set the circuit's dst_map")

    def node_subset(self, typ):
        return set(node for node in self.nodes if isinstance(node.element, typ))

    def source_wire(self) -> Wire:
        if not self._source_wire:
            self._source_wire = Wire('_sys_input')
            self.add_node(_Source(), [], [self._source_wire])
        return self._source_wire

    def sink_node(self) -> Node:
        if not self._sink_node:
            sink_wire = Wire('_sys_output')
            self._sink_node = Node(_Sink(), [sink_wire], [])
        return self._sink_node

    def get_wire_by_name(self, name) -> Optional[Wire]:
        return self._wire_by_name.get(name)

    def replace_wire(self, remove, add):
        src_node = self._src_map[remove]
        self._src_map[add] = src_node
        src_node.output_wires[src_node.output_wires.index(remove)] = add
        self.wires.remove(remove)

    def sanity_check_node(self, node):
        if len(node.element.inputs) != len(node.input_wires):
            raise PylseError(f"{type(node.element).__name__} expected "
                             f"{len(node.element.inputs)} inputs, got {len(node.input_wires)}")

        if len(node.element.outputs) != len(node.output_wires):
            raise PylseError(f"{type(node.element).__name__} expected "
                             f"{len(node.element.outputs)} outputs, got {len(node.output_wires)}")

        for i in node.input_wires:
            if not isinstance(i, Wire):
                raise PylseError(f"Input {i} is not of type Wire, instead has type {type(i)}.")

        for o in node.output_wires:
            if not isinstance(o, Wire):
                raise PylseError(f"Output {o} is not of type Wire, instead has type {type(o)}.")

        dups = [i for i in node.input_wires if node.input_wires.count(i) > 1]
        for i in dups:
            if i is not self.source_wire():
                raise PylseError(
                    f"'{i.name}' is used in the input list multiple times. "
                    f"Did you want to use a splitter to split '{i.name}'?"
                )

        for i in node.input_wires:
            # Wire coming out of InPad can be connected to multiple nodes (which must be InGen only)
            if i is not self.source_wire() and i in self.dst_map:
                raise PylseError(
                    f"Wire '{i.name}' is already connected to a node. "
                    f"Did you want to use a splitter to split '{i.name}'?"
                )

        for i in node.input_wires:
            if i not in self.wires:
                raise PylseError(f"Wire '{i.name}' ({str(i)}) is not an existing wire.")

        if self.source_wire() in node.input_wires and not isinstance(node.element, InGen):
            raise PylseError('Pseudo-element "InPad" can only be connected to "InGen" elements')

    def add_node(self, element: Element, inputs: List[Wire], outputs: List[Wire]):
        # Wires were added to the environment separately
        n = Node(element, inputs, outputs)
        self.sanity_check_node(n)
        self.nodes.add(n)
        for w in outputs:
            self._src_map[w] = n
        for w in inputs:
            # Checking that w is not already connected to something is done in sanity_check_node()
            self._dst_map[w].append(n)

    def add_wire(self, wire: Wire):
        self.wires.add(wire)

    def is_sink(self, wire: Wire):
        return not self.dst_map[wire]

    @property
    def outputs(self) -> Set[Wire]:
        # NOTE: the following should be equivalent:
        # return {w for w in self.wires if self.is_sink(w)}
        outs = set()
        for n in self.nodes:
            outs.update({w for w in n.output_wires if self.is_sink(w)})
        return outs


_singleton_circuit = Circuit()


def working_circuit(circuit=None) -> Circuit:
    if circuit:
        return circuit
    return _singleton_circuit


class _Source(Transitional):
    ''' Input reference pulse appearing at t=0 (Pseudo-Element).

    This is not intended to be used by the end-user; instead, it is
    automatically connected to all `InGen` elements and used for
    starting the simulation. Use `InGen` or the helpers `inp` and `inp_at`
    for generating inputs.
    '''
    inputs = []
    outputs = ['q']
    transitions = [
        {'source': 'idle', 'trigger': '*', 'dest': 'idle', 'firing': 'q', 'firing_delay': 0.0}
    ]
    name = '_Source'


class _Sink(Transitional):
    ''' Psuedo-Element where circuit edge elements can send their signals into the void.

    This is not intended to be used or seen by the end-user, but instead is an aid for simulation.
    '''
    inputs = ['a']
    outputs = []
    transitions = [
        {'source': 'idle', 'trigger': 'a', 'dest': 'idle'},
    ]
    name = '_Sink'


class InGen(Transitional):
    ''' Create input pulses at arbitrary times (Pseudo-Element).

    These are the sole user-visible input elements of the system.
    '''
    times: List[float]
    inputs = ['a']
    outputs = ['q']
    transitions = [
        {'source': 'idle', 'trigger': 'a', 'dest': 'done', 'firing': 'q'},
    ]
    name = 'InGen'

    def __init__(self, times: List[Union[int, float]]):
        if any(type(t) not in (int, float) for t in times):
            raise PylseError(f"InGen times must be ints or floats, given {times}.")
        self.times = [float(t) for t in times]
        super().__init__()

    def handle_inputs(self, inputs, time) -> Dict[str, List[float]]:
        assert len(inputs) == 1
        assert inputs['a']

        self.fsm.step('a', time)
        assert(self.fsm.curr_state == 'done')
        return {'q': self.times}


class _Connection(Transitional):
    ''' Internally used to connect to wires together, in a purely passthrough/non-delayed way.

    This is for convenience and should probably be omitted when emitting BLIF or other formats.
    '''
    inputs = ['a']
    outputs = ['q']
    transitions = [
        {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
    ]
    name = '_Connection'
    firing_delay = 0.0
    transition_time = 0.0


def inp_at(*times, name=None):
    ''' Create input pulses at specific times.

    :param times: variable-length argument
    :param name: name to give the resulting input wire
    :return: wire where input pulses will come from
    '''
    from .circuit import working_circuit
    out = Wire(name)
    working_circuit().add_node(InGen(list(times)), [working_circuit().source_wire()], [out])
    return out


def inp(start=0.0, period=0.0, n=1, name=None):
    ''' Create an input pulse for some number of iterations/delay.

    :param start: time at which to start the pulses (default 0.0)
    :param period: delay between successive pulse generations (default 0.0)
    :param n: number of pulses to generate (default 1)
    :param name: name to given the resulting input wire
    :return: wire where input pulses will come from

    For example, given `input(start=5.0, period=1.3, n=3)`, pulses
    will be produced at times 5.0, 6.3, and 7.6.

    Without any arguments, it produces a single pulse at time 0.0.
    '''
    if n > 1 and period == 0.0:
        raise PylseError("Period must be non-zero if niter > 1")

    times = [start + period*n for n in range(n)]
    return inp_at(*times, name=name)


def _connect(inwire, outwire):
    working_circuit().add_node(_Connection(), [inwire], [outwire])
