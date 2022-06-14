
# compile pylse machines to uppaal timed automata

import math
import warnings
from collections import defaultdict, namedtuple

import pyuppaal.pyuppaal as pyuppaal

from .circuit import working_circuit, InGen
from .sfq_cells import SFQ
from .transitional import NormalizedTransition
from .pylse_exceptions import PylseError

# just a holding container for all the str objects we create store them as
# objects, lists, etc. until we can write them out at the end


class PyLSENTA():

    Instance = namedtuple('Instance', ['instance_name', 'cell_name', 'channel_args',
                                       'extra_args', 'raw_inst'])

    def __init__(self, circuit, upscale_factor=None):
        """
        :param circuit: PyLSE circuit to work over
        :param int upscale_factor: if constraints involving floats are found,
            upscale them as needed to make them integers by multiplying
            by `upscale_factor` (thus maintaining their relative magnitudes).
            E.g. if `upscale_factor` is 10, then a float of 2.84 will be
            multiplied by 10 and then the converted to an int:
            int(2.84 * 10) = int(28.4) = 28. Thus you may lose some precision
            if your scaling factor won't make your number integral on its own.
        """
        self.instances = []
        self.templates = []
        self.channels = set()
        self.uppaal_nta = None
        self.cell_ctr = defaultdict(lambda: 0)
        self.circuit = circuit
        self.upscale_factor = upscale_factor

    def _get_template_names(self):
        return (x.name for x in self.templates)

    def _add_template(self, thing):
        if thing.name not in self._get_template_names():
            self.templates.append(thing)

    def _add_instance(self, cell_name, channels, extra=[]):
        self.channels.update(set(channels))
        # We use a coarse check to see if a location was added for error detection
        # purposes: if it contains 'err_' in the name. Since the cell name
        # is used to create location names, prevent clashes by doing this check here.
        if 'err_' in cell_name.lower():
            raise PylseError("Element names cannot contain the substring 'err_'; "
                             f"encountered problem with {cell_name}")

        instance_name = f"{cell_name.lower()}{self.cell_ctr[cell_name]}"
        self.cell_ctr[cell_name] += 1
        args = "(" + ", ".join(c.upper() for c in channels + extra) + ");\n"
        raw_inst = f"{instance_name} = {cell_name}{args}"
        self.instances.append(self.Instance(instance_name, cell_name, channels, extra, raw_inst))

    def _upscale(self, v):
        if self.upscale_factor is not None:
            v = v * self.upscale_factor
            if v != int(v):
                pass
                # warnings.warn(
                #     f"After upscaling by {self.upscale_factor}, {v} is still not an integer, "
                #     f"so it will be rounded to {int(v)}"
                # )
            v = int(v)
        return v

    def _create_template(self, node):
        assert isinstance(node.element, SFQ)

        def inputClk(name):
            # Used for keeping track of how long it's been since we saw a particular input.
            return f"{name}Clk"

        tranClk = f"{node.element.name}_x"
        if tranClk in [w for w in node.element.inputs + node.element.outputs]:
            raise PylseError(f"Output wire name {tranClk} clashes with "
                             f"channel name in {node.element.name}")

        template = pyuppaal.Template(
            node.element.name,
            declaration=f"clock {tranClk};\n" + "\n".join([f"clock {inputClk(i)};"
                                                           for i in node.element.inputs]),
            locations=[],
            initlocation=None,
            transitions=[],
            parameter=", ".join(f"chan& {c}" for c in node.element.inputs + node.element.outputs))

        ta_transitions = []
        ta_locations = []

        def get_location(name):
            locs = [loc for loc in ta_locations if loc.name.value == name]
            if len(locs) > 1:
                raise PylseError(f"Multiple locations named {name}")
            elif len(locs) == 0:
                return None
            return locs[0]

        def location_exists(name):
            return get_location(name) is not None

        ctr = 0
        fire_ctr = 0
        max_constraints = defaultdict(lambda: 0.0)

        # expand each pylse transition
        for t in node.element.transitions:  # Was 'normalized_'; we can now just use '.transitions'

            assert isinstance(t, NormalizedTransition)

            interms = []

            src, dst = t.source, t.destination

            src_loc_name = template.name + '_' + src
            dst_loc_name = template.name + '_' + dst
            if not location_exists(src_loc_name):
                loc_id = src_loc_name + '_' + t.id
                loc = pyuppaal.Location(name=src_loc_name, id=loc_id)
                ta_locations.append(loc)
            if not location_exists(dst_loc_name):
                loc_id = dst_loc_name + '_' + t.id
                loc = pyuppaal.Location(name=dst_loc_name, id=loc_id)
                ta_locations.append(loc)

            # calculate transition/delay times
            tranTime = self._upscale(t.transition_time)

            # create intermediate node for message received on channel
            # requires making a clock, checking if one doesn't already exist
            int_loc_name = template.name + '_' + 'interm' + '_' + str(ctr)
            loc = pyuppaal.Location(name=int_loc_name,
                                    id=int_loc_name,
                                    invariant=f"{tranClk} <= {tranTime}")
            ctr += 1
            ta_locations.append(loc)
            interms.append(loc)

            # orientation
            tbegin = get_location(template.name + '_' + src)
            tend = get_location(template.name + '_' + dst)

            inchan = t.trigger

            onTriggerAssignment = f"{tranClk} := 0, {inputClk(inchan)} := 0"
            onTriggerGuard = " && ".join([f"{inputClk(i)} >= {self._upscale(n)}" for
                                          i, n in t.past_constraints.items()])

            # if this transition causes the cell to fire, we expand again
            if t.firing:
                outchan = list(t.firing.keys())
                fires = []

                for (idx, _outs) in enumerate(outchan):
                    # should be committed
                    # Adding the fire_ctr to the name to make sure this is
                    # unique for each transition.
                    fire_loc_name = template.name + '_' + str(fire_ctr) +\
                                    '_' + 'fire' + '_' + str(idx)
                    fire_ctr += 1
                    floc = get_location(fire_loc_name)
                    if floc is not None:
                        fires.append(floc)
                    else:
                        f = pyuppaal.Location(name=fire_loc_name,
                                              id=fire_loc_name,
                                              committed=True)
                        ta_locations.append(f)
                        fires.append(f)

                # do some plumbing
                T1 = pyuppaal.Transition(tbegin,
                                         fires[0],
                                         synchronisation=f'{inchan}?',
                                         assignment=onTriggerAssignment,
                                         guard=onTriggerGuard)
                ta_transitions.append(T1)

                for (idx, pair) in (enumerate(zip(fires, fires[1:]))):
                    T = pyuppaal.Transition(pair[0],
                                            pair[1],
                                            synchronisation=f"{outchan[idx]}!")
                    ta_transitions.append(T)

                T2 = pyuppaal.Transition(fires[-1],
                                         loc,
                                         synchronisation=f"{outchan[-1]}!")  # fine unless list order can change by this point?  # noqa
                T3 = pyuppaal.Transition(loc,
                                         tend,
                                         assignment=f"{tranClk} := 0",
                                         guard=f"{tranClk} == {tranTime}")
                ta_transitions += [T2, T3]

            else:
                T1 = pyuppaal.Transition(tbegin,
                                         loc,
                                         synchronisation=f'{inchan}?',
                                         assignment=onTriggerAssignment,
                                         guard=onTriggerGuard)
                T2 = pyuppaal.Transition(loc,
                                         tend,
                                         assignment=f"{tranClk} := 0",
                                         guard=f"{tranClk} == {tranTime}")
                ta_transitions += [T1, T2]

            # add error states and transitions
            errs = []
            for loc in interms:
                for e in node.element.inputs:
                    err_loc_name = template.name + '_' + f"err_{e}" + '_' + str(ctr)
                    err = pyuppaal.Location(name=err_loc_name,
                                            id=err_loc_name)
                    ctr += 1
                    errs.append(err)
                    ta_locations.append(err)
                    T = pyuppaal.Transition(loc,
                                            err,
                                            synchronisation=f"{e}?",
                                            guard=f"{tranClk} > 0 && {tranClk} < {tranTime}")
                    ta_transitions.append(T)

            # Error state and transition if past constraints aren't met
            # I split them up so we can more easily see which constraint wasn't satisfied.
            # We could also make a single larger constraint:
            # aClk < aConstraint || bClk < bConstraint || ...
            for i, n in t.past_constraints.items():
                err_loc_name = template.name + '_' + f"err_{e}" + '_' + str(ctr)
                err = pyuppaal.Location(name=err_loc_name,
                                        id=err_loc_name)
                ctr += 1
                errs.append(err)
                ta_locations.append(err)
                T = pyuppaal.Transition(tbegin,
                                        err,
                                        synchronisation=f'{inchan}?',
                                        guard=f"{inputClk(i)} < {self._upscale(n)}")
                ta_transitions.append(T)
                max_constraints[i] = max(max_constraints[i], n)

        # Initial location so that the guard clocks are valid
        # (e.g. it's okay to see a clock as the first input regardless of setup time)
        init_loc = pyuppaal.Location(name=template.name + '_init',
                                     id=template.name + '_init',
                                     committed=True)
        idle_loc = get_location(template.name + '_idle')
        T = pyuppaal.Transition(init_loc, idle_loc,
                                assignment=', '.join(
                                    f'{inputClk(i)} := {self._upscale(max_constraints[i])}'
                                    for i in node.element.inputs))
        ta_transitions.append(T)
        ta_locations.append(init_loc)

        template.initlocation = init_loc
        idle_loc = get_location(template.name + '_idle')
        template.locations = sorted(ta_locations, key=lambda l: l.id)
        template.transitions = sorted(ta_transitions, key=lambda t: t.id)
        template.layout(auto_nails=True)

        self._add_template(template)

        return template, self

    def _create_sfq_ta(self):
        """ Create templates for all the SFQ cells in the circuit, and
            instantiate as many copies of them as are used.
        """

        for i in self.circuit.nodes:
            if i.element.name in ('InGen', '_Source', '_Sink'):
                # Handled elsewhere
                pass
            elif isinstance(i.element, SFQ):

                # template for cell already exists, just add an instance
                # can we just reuse the above params in this case or do we need to
                # recompute them as below?
                if i.element.name in self._get_template_names():
                    # print("already have one of those ", i.element.name)
                    pass

                # template doesn't exist, need to build one, then add an instance
                else:
                    # print("building template ", i.element.name)
                    temp, pnta = self._create_template(i)

                # instance of main cell
                # print("adding instance(s)")
                out_params = [x.name + '_fire' for x in i.output_wires]
                inst_params = [x.name for x in i.input_wires] + out_params
                self._add_instance(i.element.name, inst_params)

                # instance of corresponding firing cell(s)
                #
                # if a cell's transition time is less than the corresponding firing auto,
                # it's possible we need to fire again, so technically we need as many
                # firing auto as it takes to outlast the firing delay
                #
                # NOTE (MC): Right now the SFQ class is restricted to having a single firing delay
                # (meaning each transition that fires uses the same delay for all output)...
                delays = set(v for t in i.element.transitions for
                             v in t.firing.values() if t.firing)
                assert len(delays) == 1, f"SFQ cell has multiple firing delays: {delays}"
                firing_delay = delays.pop()
                # ...but each transition has its own transition time, so the soaking needs
                # to take into account all of the possible transition times.
                # In the future, to handle multiple firing delays, we need to create
                # firing automata per output/firing delay combination, and thus expand
                # the number of output parameters for the template (see above).
                transition_time = max(t.transition_time for t in i.element.transitions)

                if transition_time == 0:
                    soak = 1
                else:
                    if firing_delay > transition_time:
                        soak = math.ceil(firing_delay / transition_time)
                    else:
                        soak = 1

                firing_delay = str(self._upscale(firing_delay))
                # print("soak ", i.element.firing_delay, transition_time, soak)
                real_outputs = [x.name for x in i.output_wires]
                shared_outputs = [f"{x}_fire" for x in real_outputs]
                for f in range(soak):
                    for (shared, real) in zip(shared_outputs, real_outputs):
                        self._add_instance('FiringAuto', [shared, real], [firing_delay])
            else:
                raise Exception(f"Cannot convert {i.element.name} to PyLSE")

        return self

    def _create_firing_ta(self):
        """ Create a FiringAuto template. """

        firingClk = "yClk"

        start = pyuppaal.Location(name=f"fta_start",
                                  id=f"fta_start")
        duration = pyuppaal.Location(name=f"fta_duration",
                                     id=f"fta_duration",
                                     invariant=f"{firingClk} <= delay")
        end = pyuppaal.Location(name=f"fta_end",
                                id=f"fta_end",
                                committed=True)
        T1 = pyuppaal.Transition(start,
                                 duration,
                                 assignment=f"{firingClk} := 0",
                                 synchronisation=f"inchannel?")
        T2 = pyuppaal.Transition(duration,
                                 end,
                                 guard=f"{firingClk} == delay",
                                 synchronisation=f"outchannel!")
        T3 = pyuppaal.Transition(end,
                                 start)

        template = pyuppaal.Template(name=f"FiringAuto")
        template.locations = [start, duration, end]
        template.transitions = [T1, T2, T3]
        template.initlocation = start
        template.parameter = f"chan& inchannel, chan& outchannel, int delay"
        template.declaration = f"clock {firingClk};"
        template.layout(auto_nails=True)
        self._add_template(template)

        return self

    # this is the thing that builds the source automaton responsible for sending
    # inputs to the main circuit
    def _create_source_ta(self):
        """ Create InGen templates, one per inp_at node in circuit. """
        temps = []
        # pylse.inp_at allows a variable number of arguments so we
        # create a new template for every InGen we see; possibly should change
        name_ctr = 0

        for i in self.circuit.nodes:

            if isinstance(i.element, InGen):
                ta_locations = []
                ta_transitions = []
                ctr = 0
                temp_name = f"inpAt{name_ctr}"

                tranClk = f"{temp_name}_x"
                if tranClk in [o.name for o in i.output_wires]:
                    raise PylseError(f"Output wire name {tranClk} clashes with InGen channel name")

                name_ctr += 1
                self.cell_ctr[temp_name] = 0
                template = pyuppaal.Template(temp_name,
                                             declaration=f"clock {tranClk};")

                for ts in sorted(i.element.times):
                    loc_name = template.name + '_' + "t" + '_' + str(ctr)
                    loc = pyuppaal.Location(name=loc_name,
                                            id=loc_name,
                                            invariant=f"{tranClk} <= {self._upscale(ts)}")
                    ctr += 1
                    ta_locations.append(loc)

                # Create end location
                loc_name_end = template.name + '_' + "t" + '_' + str(ctr) + '_end'
                loc = pyuppaal.Location(name=loc_name_end,
                                        id=loc_name_end)  # invariant = f"x <= {int(ts)}") ??
                ctr += 1
                ta_locations.append(loc)

                # Create chain of transitions, from first user-defined inpAt time to
                # the automatically created end location (see above)
                for (s, t) in zip(ta_locations, ta_locations[1:]):
                    duration = s.invariant.value.split("<=")[1]
                    T = pyuppaal.Transition(s,
                                            t,
                                            guard=f"{tranClk} == {duration}",
                                            synchronisation=f"{i.output_wires[0].name}!")
                    ta_transitions.append(T)

                params = ", ".join(f"chan& {c.name}" for c in i.output_wires)

                template.parameter = params
                template.locations = ta_locations
                template.initlocation = ta_locations[0]
                template.transitions = ta_transitions
                template.layout(auto_nails=True)
                temps.append(template)
                self._add_instance(temp_name, [x.name for x in i.output_wires])

        self.templates += temps
        return self

    def _create_sink_ta(self):
        """ Create a Sink template. """
        ta_locations = []
        ta_transitions = []
        params = ""
        sink_nodes = []

        loc_name = "sink"
        loc = pyuppaal.Location(name=loc_name,
                                id=loc_name)
        ta_locations.append(loc)

        for w in sorted(self.circuit.outputs, key=lambda x: x.name):
            sink_nodes.append(w)
            t = pyuppaal.Transition(loc,
                                    loc,
                                    synchronisation=f"sink_{w.name}?")
            ta_transitions.append(t)

            params += (", " if params else "") + f"chan& sink_{w.name}"

        temp_name = "Sink"
        self.cell_ctr[temp_name] = 0
        template = pyuppaal.Template(temp_name,
                                     locations=ta_locations,
                                     initlocation=ta_locations[0],
                                     transitions=ta_transitions,
                                     parameter=params)
        template.layout(auto_nails=True)
        self._add_instance(temp_name, [x.name for x in sink_nodes])
        self.templates.append(template)

        return self

    def pylse2ta(self):
        """ Convert a PyLSE circuit into a UPPAAL-flavored Timed Automaton.

        :param NTA nta: object holding the state as we build the TA
        :param Circuit circuit: a PyLSE circuit (defaults to working circuit)
        """
        self._create_firing_ta()
        self._create_source_ta()
        self._create_sfq_ta()
        self._create_sink_ta()
        return self

    def build_nta(self):
        nta = pyuppaal.NTA()
        nta.templates += sorted(self.templates, key=lambda t: t.name)

        # create concrete channels and constants
        nta.declaration += "clock global;\n" + \
            "\n".join(f"chan {x.upper()};" for x in sorted(self.channels))
        names = sorted([i.instance_name for i in self.instances])
        insts = sorted([i.raw_inst for i in self.instances])
        nta.system += "\n".join(insts) + "\nsystem " + ", ".join(names) + ";"
        # print(nta.system)
        self.uppaal_nta = nta

    def write_system(self, filename=None):
        if not self.uppaal_nta:
            raise PylseError("UPPAAL automata has not been built; nothing to write out!")
        if not filename:
            filename = "system_circuit.xml"
        if not filename.endswith(".xml"):
            warnings.warn("UPPAAL filename should end with .xml")
        with open(filename, 'w') as outf:
            outf.write(self.uppaal_nta.to_xml())


def export_to_uppaal(filename, upscale_factor=10, circuit=None):
    """
    :param filename: name of an xml file to write to
    :param upscale: how much to multiply each number in this system
        by; set it to None to not upscale at all
    :param circuit: circuit to convert (defaults to working circuit)
    :return: the PyLSE NTA object (contains an UPPAAL NTA)
    """
    circuit = working_circuit(circuit)
    pnta = PyLSENTA(circuit=circuit, upscale_factor=upscale_factor)
    pnta.pylse2ta()
    pnta.build_nta()
    pnta.write_system(filename)
    return pnta


def generate_correctness_query(pnta, events, exact=True):
    """
    :param pnta: the PyLSE NTA object
    :param events: a map of wires to a list of their expected values
        (this should probably be the result of a simulation run)
    :param exact: whether to check for the exact value, or range;
        if True, just check +/- 1 from the expected value.
    :return: a string containing the correctness query
    """
    # get the firing automaton associated with each output
    conjs = []
    for output in sorted(pnta.circuit.outputs, key=lambda x: x.name):
        fas = []
        for ta in pnta.instances:
            # Find all of the the firing automata corresponding to an output
            # (could be multiple because of soaking factor).
            # NOTE: this is a little hacky re how some wires are referenced (name vs observed_as)
            if ta.cell_name == "FiringAuto" and (
                    ta.channel_args[1] in (output.name, output.observed_as)):
                fas.append(ta)
        if not fas:
            continue

        def global_range(t):
            up = pnta._upscale(t)
            if not exact:  # and/or check int(t) != t:
                # If there was a need to upscale, we need to careful about
                # all the rounding errors that might have accumulated as a
                # result of the upscaling everywhere else in the network.
                return f"(({up - 1} <= global) && (global <= {up + 1}))"
            else:
                return f"(global == {up})"

        pulse_times = events.get(output.observed_as) or events.get(output.name)
        if pulse_times:
            global_cond = "(" + " || ".join(global_range(t) for t in pulse_times) + ")"
            conj = "(" + " && ".join(f"({fa.instance_name}.fta_end imply {global_cond})"
                                     for fa in fas) + ")"
            conjs.append(conj)
    query = "A[] " + "(" + " && ".join(conjs) + ")"
    return query


def generate_error_reachability_query(pnta, _events, negative=False):
    """
    :param pnta: the PyLSE NTA object
    :param events: a list of events that occurred during the simulation
    :param negative: if True, generate a query asserting that errors *are* reachable
    :return: a string containing the liveness query
    """
    # NOTE: this assumes nothing
    err_names = []
    for i in pnta.instances:
        template = pnta.uppaal_nta.get_template(i.cell_name)
        for loc in template.locations:
            if 'err_' in loc.name.value:
                err_names.append(f"{i.instance_name}.{loc.name.value}")
    neg = "" if negative else "not "
    query = f"A[] {neg}(" + " || ".join(err_names) + ")"
    return query
