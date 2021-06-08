from collections import namedtuple, defaultdict
from typing import List, Dict, NamedTuple, Set, Union, Optional
from abc import abstractmethod
import itertools

from .pylse_exceptions import PylseError
from .core import Element


class NormalizedTransition(NamedTuple):
    id: str
    source: str
    destination: str
    trigger: str
    transition_time: float = 0.0
    transition_ignore: List[str] = []
    firing: List[str] = []  # not set in case specifying priority order to fire matters someday
    firing_delay: Optional[Dict[str, float]] = None
    is_error: bool = False


Transitioning = namedtuple(
    'Transitioning', field_names=['start_time', 'transition', 'previously_ignored_inputs']
)


class FSM:
    ''' A finite-state machine '''

    def __init__(self, inputs, outputs, transitions):
        ''' Create a finite state machine represented by a series of transitions.

        :param list[str] inputs: list of inputs
        :param list[str] outputs: list of outputs
        :param list[NormalizedTransition] transitions: list of normalized transitions objects
        '''
        self.curr_state: Union[str, Transitioning] = 'idle'
        self.inputs = inputs
        self.outputs = outputs
        self.transitions = transitions

    def reset(self):
        self.curr_state = 'idle'

    def step(self, input: str, curr_time: float, strict=True) -> Dict[str, List[float]]:
        ''' Step the FSM by passing in the name of the input that is high, along
        with the current time (needed for checking constraints related to Transitional states)

        :param str input: the name of the input that is high
        :param float curr_time: the current time
        :param bool strict: if True, produce error if no matching transition is found

        Returns a mapping from output index -> delay.

        Because some elements (i.e. InpGen) return multiple pulses, each output
        index is mapped to a list of floats (i.e. delays).
        '''
        curr_state = self.curr_state
        if isinstance(curr_state, Transitioning):
            min_legal_time = curr_state.start_time + curr_state.transition.transition_time
            if curr_time >= min_legal_time:
                curr_state = curr_state.transition.destination
            else:
                if input in curr_state.transition.transition_ignore:
                    self.curr_state = Transitioning(curr_time, curr_state.transition,
                                                    curr_state.previously_ignored_inputs + [input])
                    return {}
                else:
                    prev_inputs = self.curr_state.previously_ignored_inputs
                    window_extended = \
                        (" Note that this transition window was extended by having seen the "
                         f"ignored inputs {str(prev_inputs)} during the transition "
                         "previously.") if prev_inputs else ""
                    raise PylseError(
                        f"Transition time violation. Received input '{input}' at {curr_time} while "
                        f"still transitioning from {curr_state.transition.source} to "
                        f"{curr_state.transition.destination} on '{curr_state.transition.trigger}' "
                        f"(transition id '{curr_state.transition.id}'). The earliest it is legal "
                        f"to transition is at time {min_legal_time}.{window_extended}"
                    )

        transition = get_matching_transition(curr_state, input, self.transitions, strict=strict)

        if transition is None:
            assert not strict
            print("Warning: no next state found; staying in current state.")
            return dict()
        elif transition.is_error:
            raise PylseError(f"Triggered erroneous transition id '{transition.id}'")
        else:
            if transition.transition_time > 0:
                self.curr_state = Transitioning(curr_time, transition, [])
            else:
                self.curr_state = transition.destination
            # Return name and output delay of the outputs that are firing;
            # simulator will correlate with actual wires. Iterate over transition.firing
            # because it may be empty (in which transition.firing_delay is None).
            return {o: [transition.firing_delay[o]] for o in transition.firing}

    def sorted_high_inputs(self, inputs: Dict[str, bool]) -> List[str]:
        ''' Return the high inputs, in the deterministic order that they should
        be handled given the current state.
        '''
        s = self.curr_state.transition.destination if isinstance(self.curr_state, Transitioning)\
            else self.curr_state
        ordered_inputs = []
        for ts in get_transitions_from_source(s, self.transitions):
            ordered_inputs.append(ts.trigger)
        high_inputs = [i for i, high in inputs.items() if high]
        return sorted(high_inputs, key=lambda i: ordered_inputs.index(i))


class Transitional(Element):
    ''' Basic properties and methods necessary for any element that uses an internal FSM '''

    @property
    @abstractmethod
    def transitions(self) -> List[Dict[str, Union[int, float, str]]]:
        raise NotImplementedError

    # time it takes for an output pulse to appear after a 'firing' transition occurs.
    firing_delay = 0.0

    # set of transition ids which should be considered erroneous.
    # each transition can specify this individually.
    error_transitions: Set[str] = set()

    # time it takes to go from current to next transition;
    # each transition can specify this individually, and can be used to represent things
    # like 'reset_time' and 'setup_time'.
    transition_time: float = 0.0

    # if True, error if no matching transition is found on a given input from the current state,
    # or if an input pulse arrives during the period between transitions
    strict = True

    def __init__(self, **overrides):
        self.overrides = overrides
        self._set_transition_ids()
        self._sanity_check()
        self._store_fsm_overrides()
        self._store_transitions()
        self.fsm = FSM(self.inputs, self.outputs, self.normalized_transitions)

    def _store_fsm_overrides(self):
        # On the FSM, currently recognize:
        # - error_transitions
        # - jjs
        for prop in ['jjs', 'error_transitions']:
            if prop in self.overrides:
                setattr(self, prop, self.overrides[prop])

    def handle_inputs(self, inputs: Dict[str, bool], time: float) -> Dict[str, List[float]]:
        ''' Handle incoming input pulses.

        :param dict[str, bool] inputs: map from input names to a boolean indicating if they
            are high at this time. If multiple are high, that means they are simultaneous,
            and will be passed to the FSM's step function one at a time, in the priority
            order as defined on the FSM.
        :param float time: current time
        :return: a map from output name to list of pulses to be produced on that output wire
        '''
        outputs = defaultdict(list)
        for input in self.fsm.sorted_high_inputs(inputs):
            output_dict = self.fsm.step(input, time, self.strict)
            for o, vs in output_dict.items():
                outputs[o].extend(vs)
        return outputs

    def get_transition_by_id(self, tid):
        try:
            return next(trans for trans in self.normalized_transitions if trans.id == str(tid))
        except StopIteration:
            raise PylseError(
                f"Cannot find transition by {tid}; "
                f"available tids are {[t.id for t in self.normalized_transitions]}."
            )

    def _sanity_check(self):
        from .circuit import _Source, _Sink
        if isinstance(self, (_Source, _Sink)):
            return

        valid_types = {
            'jjs': (int,),
            'firing_delay': (float, int, dict),
            'transition_time': (float, int, dict),
            'error_transitions': (list, set)
        }
        for override_name, value in self.overrides.items():
            if override_name not in valid_types:
                raise PylseError(
                    f"Unexpected override key. Got {override_name}, "
                    f"expected one of: {','.join(valid_types.keys())}"
                )
            if not isinstance(value, valid_types[override_name]):
                raise PylseError(
                    f"Invalid type for override {override_name}. "
                    f"Got {type(value).__name__}, expected one of: "
                    f"{','.join([t.__name__ for t in valid_types[override_name]])}."
                )

        idle_found = False
        ids = defaultdict(list)
        for t in self.transitions:
            if 'source' not in t:
                raise PylseError("The given FSM is missing a 'source' key in a transition.")

            if 'trigger' not in t:
                raise PylseError("The given FSM is missing a 'trigger' key in a transition.")

            if 'dest' not in t:
                raise PylseError("The given FSM is missing a 'dest' key in a transition.")

            if t['source'] == 'idle':
                idle_found = True

            if 'id' in t:
                ids[t['id']].append(t)

            # Valid input/trigger name
            tlist = key_to_list(t, 'trigger')
            for tr in tlist:
                if tr not in self.inputs:
                    raise PylseError(
                        f"Input trigger '{t['trigger']}' from transitions was not "
                        "found in list of inputs."
                    )
                if tlist.count(tr) > 1:
                    raise PylseError(
                        f"Input trigger '{tr}' is found multiple times in trigger field '{tlist}'."
                    )

            # Valid output name
            flist = key_to_list(t, 'firing')
            for f in flist:
                if f not in self.outputs:
                    raise PylseError(
                        f"Output '{t['firing']}' from transitions was not "
                        "found in list of outputs."
                    )
                if flist.count(f) > 1:
                    raise PylseError(
                        f"Output '{f}' is found multiple times in firing field '{tlist}'."
                    )

            # Valid transition time
            ttime = t.get('transition_time', 0)
            if ttime != 'default' and type(ttime) not in (int, float):
                raise PylseError(
                    "Transition time must be a number, "
                    f"got type {type(t['transition_time']).__name__}."
                )

            # Valid inputs in transition_ignore
            ilist = key_to_list(t, 'transition_ignore')
            for i in ilist:
                if i not in self.inputs:
                    raise PylseError(
                        f"Ignored input '{t['transition_ignore']}' from transitions was not "
                        "found in list of inputs."
                    )
                if ilist.count(i) > 1:
                    raise PylseError(
                        f"Input trigger '{i}' is found multiple times in 'transition_ignore' "
                        f"field '{ilist}'."
                    )

            # Firing delay
            fd = t.get('firing_delay', 0)
            if type(fd) not in (int, float):  # don't want bools
                if not isinstance(fd, dict):
                    raise PylseError(
                        "Firing delay must be a number, or a dictionary "
                        f"from output name to a number; got {type(fd).__name__}."
                    )
                for d in fd.values():
                    if type(d) not in (int, float):
                        raise PylseError(
                            "Firing delay dictionary values must be numbers; "
                            f"got {type(d).__name__}."
                        )
                invalid_keys = set(fd.keys()).difference(set(flist))
                if invalid_keys:
                    raise PylseError(
                        "The following keys of a firing delay dictionary are not firing "
                        f"outputs for this transition: {','.join(invalid_keys)}."
                    )

            if 'setup_time' in t or 'reset_time' in t:
                raise PylseError(
                    "When giving times for specific transitions, use the key 'transition_time'. "
                )

        grouped_by_source = defaultdict(list)
        for ix, t in enumerate(self.transitions):
            grouped_by_source[t['source']].append((ix, t))

        inputs = set(self.inputs)
        for source, group in grouped_by_source.items():
            # All transitions with same source are defined next to each other
            indices = [g[0] for g in group]
            lower = indices[0]
            upper = indices[-1]
            if tuple(range(lower, upper+1)) != tuple(indices):
                raise PylseError(
                    "All transitions from the same source must be defined consecutively, "
                    "which isn't the case for transitions from %s." % source
                )

            # No two transitions in the same group with the same trigger
            working_group = group
            while working_group:
                top, working_group = working_group[0], working_group[1:]
                _top_ix, top_transition = top
                tt_trigger = set(key_to_list(top_transition, 'trigger'))
                for transition in working_group:
                    _ix, t = transition
                    ambiguous = tt_trigger.intersection(set(key_to_list(t, 'trigger')))
                    if ambiguous:
                        raise PylseError(
                            f"Ambiguous triggers '{','.join(ambiguous)}' found on transitions:\n"
                            f"1) {top_transition}\n"
                            f"2) {t}."
                        )

            # A transition for every input trigger going out of this state
            if self.strict:
                for _, t in group:
                    inputs.difference_update(set(key_to_list(t, 'trigger')))
                if inputs:
                    raise PylseError(
                        "No transitions specified for inputs '%s' from state '%s'." %
                        (str(','.join(inputs)), source)
                    )

        if not idle_found:
            raise PylseError("The given FSM does not have an 'idle' source state.")

        for tid, transitions in ids.items():
            if len(transitions) > 1:
                output = f"Multiple transitions with the same id '{tid}' found:\n"
                output += "\n".join(f"{ix + 1}) {transition}"
                                    for ix, transition in enumerate(transitions))
                raise PylseError(output)

        if not len(self.outputs):
            raise PylseError("There must be at least one output; found none.")

        # For every output, there exists at least one transition that fires it
        for o in self.outputs:
            if all(o not in key_to_list(t, 'firing') for t in self.transitions):
                raise PylseError(
                    f"There must be at least one transition that fires output '{str(o)}'."
                )

        # Error transition ids given are valid
        all_tids = set(t['id'] for t in self.transitions)
        unrecognized = self.error_transitions.difference(all_tids)
        if unrecognized:
            raise PylseError(f"Error transition id(s) {unrecognized} do(es) not "
                             "match any given transition.")

    def _set_transition_ids(self):
        """ Assigns every transition an ID (if it doesn't have one already) """

        def next_available_id():
            tids = set(t['id'] for t in self.transitions if 'id' in t)
            next_id = 0

            def inner() -> str:
                nonlocal next_id
                while next_id in tids:
                    next_id += 1
                res = next_id
                next_id += 1
                return str(res)
            return inner
        next_id = next_available_id()

        for t in self.transitions:
            if 'id' not in t:
                t['id'] = next_id()

    def _store_transitions(self):
        ''' Normalize and store transitions, by making sure output delays are
        associated with each firing transition, and that all triggers are fully
        expanded.

        Each transition in self.transitions is a dictionary, and which must have
        at least 'id', 'source', 'dest', and 'trigger' keys
        '''

        self.normalized_transitions = []
        for transition in self.transitions:

            transition_time = self.overrides.get('transition_time')
            if isinstance(transition_time, (int, float)):
                # Don't use the override if the transition didn't
                # have a transition_time to begin with, or it did
                # but had a non-'default' value.
                if ('transition_time' not in transition) or \
                   (transition.get('transition_time') != 'default'):
                    transition_time = 0
            elif isinstance(transition_time, dict):
                transition_time = transition_time.get(transition['id'])
            if transition_time is None:
                transition_time = transition.get('transition_time', 0)
            if transition_time == 'default':
                transition_time = self.transition_time

            transition_ignore = transition.get('transition_ignore', [])

            firing = key_to_list(transition, 'firing')
            if firing:
                # For each firing transition, each firing output has an associated delay, which is
                # 1) the override delay given by user calling the cell function (e.g. m())
                # 2) the specified delay for the particular output on the transition, if given, else
                # 3) the specified delay for all outputs on the transition, if given, else
                # 4) the default firing delay defined on the class
                firing_delay = self.overrides.get('firing_delay')
                if firing_delay is None:
                    firing_delay = transition.get('firing_delay', self.firing_delay)

                if isinstance(firing_delay, dict):
                    for f in firing:
                        firing_delay.setdefault(f, self.firing_delay)
                else:
                    firing_delay = {f: firing_delay for f in firing}
            else:
                firing_delay = None

            is_error = transition['error'] if 'error' in transition else \
                (transition['id'] in self.error_transitions)
            triggers = key_to_list(transition, 'trigger')

            for trigger in triggers:
                self.normalized_transitions.append(
                    NormalizedTransition(
                        id=transition['id'],
                        source=transition['source'],
                        destination=transition['dest'],
                        trigger=trigger,
                        firing=firing,
                        transition_time=transition_time,
                        transition_ignore=transition_ignore,
                        firing_delay=firing_delay,
                        is_error=is_error,
                    )
                )


def key_to_list(raw_transition: Dict, key: str):
    ''' Converts something like ['clk', {'a', 'b'}] to ['clk', 'a', 'b'],
    or 'a' to ['a'].

    If the key doesn't exist in the transition, returns an empty list.

    NOTE: this is useful right now as it's still in flux which keys we allow
    to have multiple values, vs which must be singletons.
    '''
    value = raw_transition.get(key, [])

    def unwrap(ws):
        if isinstance(ws, (list, set)):
            ls = [unwrap(el) for el in ws]
            return list(itertools.chain(*ls))
        else:
            return [ws]
    return unwrap(value)


def get_transitions_from_source(source_state: str,
                                transitions: List[Union[dict, NormalizedTransition]]):
    s = []
    for t in transitions:
        if isinstance(t, dict):
            source = t['source']
        else:
            source = t.source
        if source == source_state:
            s.append(t)
    return s


def get_matching_transition(source_state: str, input: str,
                            transitions: List[NormalizedTransition], strict=True):
    ''' Find the transition that matches the current state and inputs.

    :param str source_state: state we're starting from
    :param str input: name of the input that is high currently
    :param List[NormalizedTransition] transitions: list of transitions to search
    :param bool strict: if True, raise an error if no matching transition is found;
        if False, just print a warning in such cases
    :return: the matching Normalized transition, or None if strict is False and none was found
    '''
    ts = get_transitions_from_source(source_state, transitions)
    try:
        return next(t for t in ts if input == t.trigger)
    except StopIteration:
        if strict:
            raise PylseError("No matching transition found from state "
                             f"'{source_state}' on input '{input}'.")
        return None
