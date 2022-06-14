import matplotlib.pyplot as plt
import collections

from pylse.pylse_exceptions import PylseError

from .circuit import working_circuit, _Source, InGen
from .core import is_temporary_wire_name
from .transitional import Transitional


def plot(events_to_plot, until=None, sort=True, segment_size=5, display=True, filename=None):
    """ Plot the given events on a Matplotlib plot.

    :param dict events_to_plot: dictionary of events to plot
        (the result of running simulate() on a Simulation object)
    :param float until: optional, the last time to plot, on the x-axis
    :param sort: if True, sort the events by name; set to False if you
        specifically want the Y axis (pulse names) to be in the order
        that they are given in the events_to_plot dictionary
    :param int segment_size: how many ticks between x-axis labels
    :param str filename: optional, the filename to save the plot to
    :param bool display: optional, if True, display the plot on the screen
    :return: None
    """
    if filename is None and not display:
        raise PylseError("Must specify either a file_name or display=True")

    if until is None:
        until = 0
        for times in events_to_plot.values():
            until = max(max(times) if times else 0, until)
    # There may be other pulses that were created extending a little beyond
    until += 1
    events = events_to_plot.items()
    if sort:
        events = sorted(events)
    od = collections.OrderedDict(events)
    variables = list(od.keys())
    data = list(od.values())
    _fig, ax = plt.subplots()
    plt.eventplot(data, orientation='horizontal', color='red', linelengths=0.5)
    ax.set_xlabel('Time (ps)')
    ax.set_xlim(-1, until)
    ax.set_xticks([x for x in range(until+1) if (x % segment_size == 0)])
    ax.set_xticklabels(ax.get_xticks(), rotation=45)
    ax.set_ylabel('Tracked Wires')
    ax.set_ylim(-1, len(variables))
    ax.set_yticks([(i) for i in range(len(variables))])
    ax.set_yticklabels(variables)
    ax.invert_yaxis()
    ax.grid(True)
    # plt.subplots_adjust(left=0.15, right=0.92, bottom=0.13)
    plt.subplots_adjust(left=0.15, right=0.985, top=0.985, bottom=0.12)
    # save the waveform plot if desired
    if filename is not None:
        plt.savefig(filename)
    if display:
        plt.show()
    return


def _graph_elements(circuit):
    elements = []
    for node in circuit:

        if isinstance(node.element, _Source):
            continue

        # Create the nodes
        elements.append({
            'data': {
                'id': str(node.node_id),
                'label': node.element.name,
            },
        })

        if isinstance(node.element, InGen):
            # Since for now, we're not including the _Source element,
            # the InGen source node won't be present either.
            continue

        # Create the edges
        for input_wire in node.input_wires:
            src_id = str(circuit.src_map[input_wire].node_id)
            dst_id = str(node.node_id)
            elements.append({
                'data': {
                    'id': input_wire.name,
                    'source': src_id,
                    'target': dst_id,
                    'label': input_wire.observed_as or '',
                }
            })

        # Since we don't have explicit output nodes, need to handle the leaf nodes
        # special so we can see them, thus creating pseudo-nodes. Note that node.output_wires
        # is always length 1, except for _Source going to many InGens.
        if circuit.is_sink(node.output_wires[0]):
            # Create the node
            sink_node_id = str(node.output_wires[0].name)
            label = node.output_wires[0].observed_as or ''
            elements.append({
                'data': {
                    'id': sink_node_id,
                    'label': label,
                }
            })
            # Create the edge
            elements.append({
                'data': {
                    'source': str(node.node_id),
                    'target': sink_node_id,
                }
            })
    return elements


_graph_default_stylesheet = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(label)',
        }
    },
    {
        'selector': 'edge',
        'style': {
            'curve-style': 'bezier',
            'target-arrow-shape': 'vee',
            'label': 'data(label)',
        }
    },
]


def graph(circuit=None):
    import dash
    import dash_cytoscape as cyto
    import dash_html_components as html

    circuit = working_circuit(circuit)
    elements = _graph_elements(circuit)
    stylesheet = _graph_default_stylesheet

    cyto.load_extra_layouts()
    app = dash.Dash(__name__)
    app.layout = html.Div([
        html.P("PyLSE via Dash Cytoscape:"),
        cyto.Cytoscape(
            id='cytoscape',
            layout={'name': 'dagre'},
            style={'width': '1200px', 'height': '800px'},
            elements=elements,
            stylesheet=stylesheet,
        )
    ])

    app.run_server(debug=True)
