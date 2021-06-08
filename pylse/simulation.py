import random
from typing import List, Dict
from heapq import heappop, heappush
from collections import defaultdict, namedtuple

from .plot import plot
from .circuit import working_circuit
from .core import Node
from .pylse_exceptions import PylseError

Pulse = namedtuple('Pulse', ['time', 'wire'])


class Simulation:
    def __init__(self, circuit=None):
        self.circuit = working_circuit(circuit)
        self.pulse_heap: List[Pulse] = []
        self.now: float = 0.0
        self.events_to_plot: Dict[str, List[float]] = {}  # result from simulating
        self.until: float = 0.0  # computed during simulation

    def add_pulse(self, time, wire):
        assert time >= self.now
        heappush(self.pulse_heap, Pulse(time, wire))

    def _add_initial_pulse(self):
        self.add_pulse(self.now, self.circuit.source_wire())

    def _set_variability(self, variability):

        def default_variability(delay, element):
            '''
            :param float delay: delay to add variability to
            :param element element: element object
            '''
            stdev = (delay * 0.2) / 3  # unlikely to fall outside range (3 std devs)
            delay = random.gauss(delay, stdev)
            # Remove the following if want it to be truly unbounded/gaussian
            min_delay = delay * 0.8
            max_delay = delay * 1.2
            if delay < min_delay:
                delay = min_delay
            elif delay > max_delay:
                delay = max_delay
            return delay

        if variability:
            if isinstance(variability, bool):
                # Use default variability function
                self.variability = default_variability
            elif callable(variability):
                self.variability = variability
            else:
                raise PylseError(
                    "Invalid variability argument; must be a boolean or a function. "
                    "If True, will use the default variability function, which multiplies "
                    "an element's delay by a random factor between 0.8 and 1.2, chosen from "
                    "a normal distribution."
                )
        else:
            self.variability = None

    def simulate(self, until=None, variability=False):

        def dst_nodes(p: Pulse):
            # If pulse's wire has no destination node, implicitly send their signal to global sink.
            # Right now, this makes it simpler that the pulse is recorded.
            dsts = self.circuit._dst_map[p.wire]
            if not dsts:
                dsts = [self.circuit.sink_node()]
            return dsts

        def get_all_simultaneous_pulses() -> Dict[Node, List[Pulse]]:
            """ Group by destination """
            pulses = defaultdict(list)
            p = heappop(self.pulse_heap)
            for dn in dst_nodes(p):
                pulses[dn].append(p)
            assert p.time >= self.now
            self.now = p.time
            while self.pulse_heap and (self.pulse_heap[0].time == p.time):
                p = heappop(self.pulse_heap)
                for dn in dst_nodes(p):
                    pulses[dn].append(p)
            return pulses

        self._set_variability(variability)
        self._add_initial_pulse()

        # Print all named wires, even those that don't receive a pulse during simulation.
        for w in self.circuit.wires:
            if w.observed_as is not None:
                self.events_to_plot[w.observed_as] = []

        while until is None or self.now < until:
            # Get the next pulses to process
            if len(self.pulse_heap) == 0:
                break

            pulses = get_all_simultaneous_pulses()

            # Add the selected output pulses to the dictionary
            for dst, ps in pulses.items():
                for p in ps:
                    if p.wire.observed_as is not None:
                        self.events_to_plot[p.wire.observed_as].append(self.now)
                self.send_pulses(dst, ps)

        self.until = until if until else self.now
        return self.events_to_plot

    def send_pulses(self, dst_node: Node, pulses: List[Pulse]):
        """ Alert node listening for these pulses.

        For all wires except the wire coming out of the InPad, there should
        be only one destination, but we store a singleton list regardless.
        Right now, final wires don't connect to any such pseudo-'output' node.
        """

        # At least one pulse, and they are all the same time
        assert(len(set(p.time for p in pulses)) == 1)

        def get_pulse(inp_wire):
            for p in pulses:
                if inp_wire is p.wire:
                    return True
            return False

        def get_input_wire_name(inp_wire):
            ix = dst_node.input_wires.index(inp_wire)
            return dst_node.element.inputs[ix]

        def get_output_wire(out_name):
            ix = dst_node.element.outputs.index(out_name)
            return dst_node.output_wires[ix]

        inputs = {get_input_wire_name(i): get_pulse(i) for i in dst_node.input_wires}
        try:
            outputs = dst_node.element.handle_inputs(inputs, pulses[0].time)
        except PylseError as err:
            raise PylseError("Error while sending inputs to the node with output wire '{0}':\n{1}".
                             format(dst_node.output_wires[0].name, err))
        for out_name, delays in outputs.items():
            outw = get_output_wire(out_name)
            for delay in delays:
                if self.variability:
                    delay = self.variability(delay, dst_node.element)
                self.add_pulse(self.now + delay, outw)

    def display(self, segment_size=10):
        plot(self.events_to_plot, int(self.until), segment_size=segment_size)
