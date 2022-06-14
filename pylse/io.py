from typing import Protocol, List, Dict

from .circuit import working_circuit, InGen, _Source, _Sink, Circuit, Node, _Connection
from .pylse_exceptions import PylseError
from .core import Wire
from .simulation import Simulation, GraphicalSimulation
from .sfq_cells import C_INV, C, DRO, split


def import_from_pyrtl_xsfq(block=None):
    """ Import a PyRTL block (having already been synthesized into XSFQ),
    turning & into LA (i.e. C elements), | into FA (i.e. C INV elements),
    registers into DROs, and adding the splitters as needed.

    :param block: PyRTL block to import
    :return: tuple of the wires corresponding to inputs and outputs into the PyLSE circuit
    """
    import pyrtl  # pylint: disable=import-error

    block = pyrtl.working_block(block)
    circuit = working_circuit()

    def wire(name: str):
        w = circuit.get_wire_by_name(name)
        if w is None:
            w = Wire(name)
        return w

    # Add splitters for all normal PyRTL wires, and the implicit `clk` is there are registers
    _, dst_nets = block.net_connections()
    split_map = {}
    for w in block.wirevector_subset(exclude=pyrtl.Output):
        pylse_wire = wire(w.name)
        if (n := len(dst_nets[w])) > 1:
            new_ws = split(pylse_wire, n)
            split_map[w] = new_ws
    if (n := len(block.wirevector_subset(pyrtl.Register))) > 1:
        w = wire('clk')
        new_ws = split(w, n)
        split_map[w] = new_ws

    split_indices = {w: 0 for w in split_map}

    def get_next_split_wire(w):
        ix = split_indices[w]
        s_wire = split_map[w][ix]
        split_indices[w] = ix + 1
        return s_wire

    for net in block:

        def arg(n):
            w = net.args[n]
            if w in split_map:
                return get_next_split_wire(w)
            return wire(w.name)

        dest = wire(net.dests[0].name)

        if net.op == 'w':
            circuit.add_node(_Connection(), [arg(0)], [dest])
        elif net.op == '&':  # LA
            circuit.add_node(C(), [arg(0), arg(1)], [dest])
        elif net.op == '|':  # FA
            circuit.add_node(C_INV(), [arg(0), arg(1)], [dest])
        elif net.op == 'r':
            circuit.add_node(DRO(), [arg(0), get_next_split_wire(wire('clk'))], [dest])
        else:
            raise PylseError(
                f"Don't know how to convert {net.op} net. You need to call "
                "`and_or_synth(merge_io_vectors=True, emulate_inv_inputs=False)` "
                "beforehand on the block."
            )

    ins = [wire(w.name) for w in block.wirevector_subset(pyrtl.Input)]
    if (w := circuit.get_wire_by_name('clk')) is not None:
        ins.append(w)
    outs = [wire(w.name) for w in block.wirevector_subset(pyrtl.Output)]
    return ins, outs


def run_xsfq(input_times, wires_to_display=None, block=None):
    """ Import a PyRTL block (having already been synthesized into XSFQ)
    and run it in the PyLSE simulator. This automatically takes care of adding
    the InGen nodes needed to do so.

    :param Dict[str, List[float]] input_times: Dictionary mapping wire names
        to list of times pulses should appear on that wire.
    :param wires_to_display: list of wire names to display after the simulation.
        If None, defaults to just the inputs/outputs; if 'all', will display
        all wires with a non-temporary name.
    :param block: PyRTL block to import
    """

    circuit = working_circuit()
    in_wires, out_wires = import_from_pyrtl_xsfq(block)

    if (left := {w.name for w in in_wires}) != (right := set(input_times.keys())):
        raise PylseError(
            "Must supply times for each input. "
            f"Input wires in circuit: {','.join(left)}. "
            f"Provided inputs: {','.join(right)}."
        )

    for in_wire in in_wires:
        times = input_times[in_wire.name]
        circuit.add_node(InGen(list(times)), [circuit.source_wire()], [in_wire])

    sim = Simulation()
    # sim = GraphicalSimulation()
    sim.simulate()

    if wires_to_display is None:
        wires_to_display = {w.name for w in in_wires + out_wires}
    elif wires_to_display == 'all':
        wires_to_display = None
    sim.plot(wires_to_display=wires_to_display)


def export_to_blif(file, circuit: Circuit = None):
    circuit = working_circuit(circuit)

    def _print(s):
        print(s, file=file)

    connection_elements = circuit.node_subset(_Connection)

    def wire_name(wire):
        for ce in connection_elements:
            if wire in ce.output_wires:
                return ce.input_wires[0].name
        return wire.name

    _to_blif_header(circuit, wire_name, _print)
    _to_blif_body(circuit, wire_name, _print)
    _to_blif_footer(circuit, wire_name, _print)


def _node_sort_key(node: Node):
    return node.element.name +\
           ' '.join([n.name for n in node.input_wires]) +\
           ' '.join([n.name for n in node.output_wires])


def _to_blif_header(circuit: Circuit, _wire_name, print):
    print('# Generated automatically via PyLSE')
    print('')
    print('.model top')
    print('')

    in_list = set()
    for n in circuit.node_subset(InGen):
        assert len(n.output_wires) == 1
        in_list.add(n.output_wires[0].name)

    print('.inputs {:s}'.format(' '.join(sorted(in_list))))
    # TODO outputs if/when we have them...


def _to_blif_body(circuit: Circuit, wire_name, print):
    for node in sorted(circuit.nodes, key=_node_sort_key):
        if isinstance(node.element, (_Source, _Sink, _Connection, InGen)):
            continue

        gn = node.element.blif_gate_name
        ins = []
        # Relies on order being the same
        for formal_name, iwire in zip(node.element.blif_input_names, node.input_wires):
            actual_name = wire_name(iwire)
            ins.append(f'{formal_name}={actual_name}')

        outs = []
        for formal_name, owire in zip(node.element.blif_output_names, node.output_wires):
            actual_name = wire_name(owire)
            outs.append(f'{formal_name}={actual_name}')

        io = ' '.join(ins + outs)
        print(f'.gate {gn} {io}')
    print('')


def _to_blif_footer(_block, _wire_name, print):
    print('.end')
