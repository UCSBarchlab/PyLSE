import random
import sys
import itertools
from typing import List, Dict
from heapq import heappop, heappush
from collections import defaultdict, namedtuple
import json

from .visual import plot, _graph_default_stylesheet, _graph_elements
from .circuit import working_circuit, InGen, _Source
from .core import Node
from .transitional import Transitional
from .pylse_exceptions import PylseError

Pulse = namedtuple('Pulse', ['time', 'wire'])


class Simulation:
    def __init__(self, circuit=None):
        self.circuit = working_circuit(circuit)
        self._initialize()

    def _initialize(self):
        self.pulse_heap: List[Pulse] = []
        self.now: float = 0.0
        self.events_to_plot: Dict[str, List[float]] = {}  # result from simulating
        self.until: float = 0.0  # computed during simulation
        # self.states = {}  # Map from time to state of the system? For backwards stepping

    def add_pulse(self, time, wire):
        assert time >= self.now
        heappush(self.pulse_heap, Pulse(time, wire))

    def _add_initial_pulse(self):
        self.add_pulse(self.now, self.circuit.source_wire())

    def _set_variability(self, variability):
        # If variability is a dictionary, it can take the following options:
        #
        #   - 'element_names_{include, exclude}': <list of str>
        #   - 'element_types_{include, exclude}': <list of Class names>
        #   - 'elements_{include, exclude}':      <list of Element objects>
        #   - 'wire_names_(include, exclude}':    <list of str>
        #   - 'wires_{include, exclude}':         <list of Wire objects>
        #
        # If an `_include` option is used, only elements/wires of that name/id will be used.
        # If an `_exclude` option is used, all *but* elements/wires of that name/id will be used.
        # Using a wire means to look at the node from which it originates.
        # We'll try and combine these options best we can to get the intersecting set.

        def default_variability(delay, node):
            '''
            :param float delay: delay to add variability to
            :param node node: Node object, which you can use to get:
                - the node.element's name/type
                - the node.input Wire object(s)
                - the node.output Wire object(s)
            '''
            if isinstance(variability, dict):
                if 'element_names_include' in variability:
                    if node.element.name not in variability['element_names_include']:
                        return delay
                if 'element_names_exclude' in variability:
                    if node.element.name in variability['element_names_exclude']:
                        return delay
                if 'element_types_include' in variability:
                    if node.element.__class__.__name__ not in variability['element_types_include']:
                        return delay
                if 'element_types_exclude' in variability:
                    if node.element.__class__.__name__ in variability['element_types_exclude']:
                        return delay
                if 'elements_include' in variability:
                    if node.element not in variability['elements_include']:
                        return delay
                if 'elements_exclude' in variability:
                    if node.element in variability['elements_include']:
                        return delay
                if 'wire_names_include' in variability:
                    if any(w.name not in variability['wire_names_include']
                           for w in node.output_wires):
                        return delay
                if 'wire_names_exclude' in variability:
                    if any(w.name in variability['wire_names_exclude'] for w in node.output_wires):
                        return delay

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
                if variability is True:
                    # Use default variability function
                    self.variability = default_variability
            elif isinstance(variability, dict):
                self.variability = default_variability
            elif callable(variability):
                self.variability = variability
            else:
                raise PylseError(
                    "Invalid variability argument; must be a boolean, dict, or function. "
                    "If True, will use the default variability function, which multiplies "
                    "an element's delay by a random factor between 0.8 and 1.2, chosen from "
                    "a normal distribution. If a dict, will use the default variability function "
                    "with possible options from the dict (see documentation). If a function, "
                    "will use that for determining the delay of each element."
                )
        else:
            self.variability = None

    def _restart_simulation(self, variability):
        self._initialize()
        for node in self.circuit:
            if isinstance(node.element, Transitional):
                node.element.fsm.reset()
        self._set_variability(variability)
        self._add_initial_pulse()

    def _get_all_simultaneous_pulses(self) -> Dict[Node, List[Pulse]]:
        """ Group by destination """

        def dst_nodes(p: Pulse):
            # If pulse's wire has no destination node, implicitly send their signal to
            # global sink. Why? Right now, only to make it simpler that the pulse is recorded.
            dsts = self.circuit._dst_map[p.wire]
            if not dsts:
                dsts = [self.circuit.sink_node()]
            return dsts

        pulses = defaultdict(list)
        if len(self.pulse_heap) == 0:
            return pulses

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

    def simulate(self, until=None, variability=False, log=None):
        """ Simulate the circuit until a certain time, or until the all the input pulses
            have been processed.

            :param until: time to simulate until (defaults to None,
                meaning run until all pulses have been processed)
            :param variability: whether to add noise to the delay of each element.
                If False, adds no noise. If True, multiplies an element's delay by
                a random factor between 0.8 and 1.2, chosen from a normal distribution.
                Can also a supply a function that takes a delay (float) and an element
                (Element object) as parameters, returning a float (the new delay for
                that particular element).

            You'll need to set `until` to non-None if you have a feedback loop
            that would cause the simulation to run forever.
        """
        def print_to_log():
            if log is not None:
                self.print_state(file=log)

        self._restart_simulation(variability)

        # Print all named wires, even those that don't receive a pulse during simulation.
        for w in self.circuit.wires:
            if w.observed_as is not None:
                self.events_to_plot[w.observed_as] = []

        while until is None or self.now < until:
            print_to_log()

            # Get the next pulses to process
            pulses = self._get_all_simultaneous_pulses()
            if not pulses:
                break

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
            high_inputs = [i for i in inputs if inputs[i]]
            raise PylseError(
                "Error while sending input(s) '{0}' to the node with output wire '{1}':\n{2}".
                format(', '.join(high_inputs), dst_node.output_wires[0].name, err)
            )
        for out_name, delays in outputs.items():
            outw = get_output_wire(out_name)
            for delay in delays:
                if self.variability:
                    delay = self.variability(delay, dst_node)
                self.add_pulse(self.now + delay, outw)

    def plot(self, wires_to_display: List[str] = None, segment_size=10,
             display=True, filename=None):
        events = self.events_to_plot
        if wires_to_display is not None:
            events = {w: events[w] for w in wires_to_display}

        plot(events, int(self.until), sort=(wires_to_display is None),
             segment_size=segment_size, filename=filename, display=display)

    def print_state(self, file=sys.stdout):
        # Iterate over the graph in topological order,
        # starting with the ones that don't have incoming wires.
        info = {}
        info['current_time'] = self.now

        graph = []
        for node in self.circuit:
            # Right now, don't clutter with these
            if isinstance(node.element, _Source):
                continue

            node_dict = {}
            node_dict['id'] = node.node_id
            node_dict['name'] = node.element.name
            node_dict['incoming_wires'] = {formal: w.name for formal, w in
                                           zip(node.element.inputs, node.input_wires)}
            node_dict['outgoing_wires'] = {formal: w.name for formal, w in
                                           zip(node.element.outputs, node.output_wires)}
            if isinstance(node.element, Transitional):
                node_dict['state'] = node.element.fsm.curr_state
            graph.append(node_dict)
        info['graph'] = graph

        pulses = []
        for pulse in self.pulse_heap:
            pulse = {'time': pulse.time, 'on_wire': pulse.wire.name}
            pulses.append(pulse)
        info['pending_pulses'] = pulses

        # json.dump(info, file)
        print(json.dumps(info, indent=4), file=file)


class GraphicalSimulation(Simulation):
    def simulate(self, variability=False):
        import dash
        import dash_cytoscape as cyto
        import dash_html_components as html
        from dash.dependencies import Input, Output

        self._restart_simulation(variability)
        circuit = working_circuit(self.circuit)

        elements = _graph_elements(circuit)
        stylesheet = _graph_default_stylesheet

        cyto.load_extra_layouts()
        app = dash.Dash(__name__)
        app.layout = html.Div([
            html.P("PyLSE via Dash Cytoscape:"),

            # html.Div(id="curr-time"),

            html.Div([
                html.Button('Restart', id='btn-restart', n_clicks=0)
            ]),

            html.Div([
                html.Button('Previous (not yet implemented)', id='btn-prev', n_clicks=0)
            ]),

            html.Div([
                html.Button('Next', id='btn-next', n_clicks=0)
            ]),

            cyto.Cytoscape(
                id='cytoscape',
                layout={
                    'name': 'dagre',
                    'nodeDimensionsIncludeLabels': True,
                },
                style={'width': '1200px', 'height': '800px'},
                elements=elements,
                stylesheet=stylesheet,
            )
        ])

        def get_button_id():
            ctx = dash.callback_context
            if not ctx.triggered:
                button_id = 'No clicks yet'
            else:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            return button_id

        # @app.callback(
        #     Output('curr-time', 'children'),
        #     Input('btn-next', 'n_clicks'),
        #     Input('btn-restart', 'n_clicks'))
        # def update_time(next_n_clicks, restart_n_clicks):
        #     button_id = get_button_id()
        #     if button_id == 'btn-restart':
        #         self._restart_simulation(variability=variability)
        #         return "Last pulse time: (None)"
        #     elif button_id in ['btn-next', 'No clicks yet']:
        #         if len(self.pulse_heap) == 0:
        #             return 'Done! (last pulse time: ' + str(self.now) + ')'
        #         return "Last pulse time: " + str(self.now)

        @app.callback(Output('cytoscape', 'stylesheet'),
                      Input('btn-restart', 'n_clicks'),
                      Input('btn-prev', 'n_clicks'),
                      Input('btn-next', 'n_clicks'))
        def update_stylesheet(restart_n_clicks, prev_n_clicks, next_n_clicks):
            # Don't care how many times this has been clicked in total,
            # just that it was clicked.

            button_id = get_button_id()
            if button_id == 'btn-restart':
                self._restart_simulation(variability=variability)
                return _graph_default_stylesheet
            elif button_id == 'btn-prev':
                pass
                # state = self.goto_previous_state()
            elif button_id == 'btn-next':
                pulses = self._get_all_simultaneous_pulses()
                new_edge_styles = []
                new_node_styles = []

                # Add the selected output pulses to the dictionary
                for dst, ps in pulses.items():

                    self.send_pulses(dst, ps)
                    for p in ps:
                        new_edge_styles.append({
                            'selector': '#' + p.wire.name,
                            'style': {
                                'curve-style': 'bezier',
                                'target-arrow-shape': 'vee',
                                'label': (p.wire.observed_as or '') + ' ' + str(self.now),
                                'line-color': "#0000ff",
                            }
                        })
                    new_node_styles.append({
                        'selector': '#' + str(dst.node_id),
                        'style': {
                            'background-color': '#0000ff',
                        }
                    })

                for node in circuit:
                    def state():
                        if isinstance(node.element, Transitional):
                            return ' (' + str(node.element.fsm.curr_state) + ')'
                        return ''

                    new_node_styles.append({
                        'selector': '#' + str(node.node_id),
                        'style': {
                            'label': node.element.name + state(),
                        }
                    })

                return _graph_default_stylesheet + new_node_styles + new_edge_styles
            else:
                return _graph_default_stylesheet

        app.run_server(debug=True)
