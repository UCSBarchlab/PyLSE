from collections import namedtuple, defaultdict
from typing import List, Dict, NamedTuple, Set, Union, OrderedDict
from abc import abstractmethod
import itertools

from .pylse_exceptions import PylseError
from .core import Element


class NormalizedTransition(NamedTuple):
    """ NormalizedTransition is a Transition that has been checked and filled out
    properly, i.e. sanitized for use in the internals of PyLSE simulation.

    Constructor arguments:
    :param (str) id: an arbitrary identifier for this transition
    :param (str) source: the source state
    :param (str) destination: the destination state
    :param (str) trigger: the name of the input the causes this transition to fire
    :param (float) transition_time: the amount of time it takes to transition from source to
        destination, i.e. how long the machine is **unstable** and during which time receiving
        input triggers may be an error
    :param (Dict[str, float]) illegal_priors: the dictionary of ('input', 'value') entries, which
        allows you to express: "if, upon starting receiving the trigger for this transition at time
        'curr_time', any 'input' was seen in the past 'value' time units (i.e. between
        'curr_time-value' and 'curr_time'), this is an error.
    :param (List[str]) firing: list of names of outputs that are fired during this transition.
        They will be fired in the order listed (though that doesn't affect anything in the
        semantics, yet...)
    :param (dict) firing_delay: a dictionary mapping each output wire to the time it takes for an
        output pulse to appear on it; the set of keys must match the list of names in firing.
    :param (bool) is_error: whether this transition, if triggered, is considered an error. The
        simulation will stop immediately after this transition is triggered.
    """
    id: str
    source: str
    destination: str
    trigger: str
    priority: int  # priority wrt other transitions originating from same source
    transition_time: float = 0.0
    past_constraints: Dict[str, float] = dict()  # keys: triggers or '*'; values: time
    firing: Dict[str, float] = OrderedDict()  # show that order may matter someday
    is_error: bool = False


Transitioning = namedtuple(
    'Transitioning',
    field_names=['start_time', 'transition']
)


class FSM:
    ''' A finite-state machine.

        While the Transitional class is used for defining the transitions,
        the FSM class is used for tracking the current state, i.e. it's an
        instance of the transition system that has state/can be manipulated.
    '''

    def __init__(self, name, inputs, outputs, transitions):
        ''' Create a finite state machine represented by a series of transitions.

        :param str: the name of the FSM (i.e. the name of the element given the class)
        :param list[str] inputs: list of inputs
        :param list[str] outputs: list of outputs
        :param list[NormalizedTransition] transitions: list of normalized transitions objects
        '''
        self.curr_state: Union[str, Transitioning] = 'idle'
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.transitions = transitions
        self._last_seen: Dict[str, Union[None, float]] = {i: None for i in inputs}

    def reset(self):
        self.curr_state = 'idle'
        self._last_seen = {i: None for i in self.inputs}

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
        inp_last_seen = self._last_seen[input]
        self._last_seen[input] = curr_time

        if isinstance(curr_state, Transitioning):
            min_legal_time = curr_state.start_time + curr_state.transition.transition_time
            if curr_time >= min_legal_time:
                curr_state = curr_state.transition.destination
            else:
                raise PylseError(
                    f"Transition time violation on FSM '{self.name}'. Received input '{input}' "
                    f"at {curr_time} while "
                    f"still transitioning from {curr_state.transition.source} to "
                    f"{curr_state.transition.destination} on '{curr_state.transition.trigger}' "
                    f"(transition id '{curr_state.transition.id}'). The earliest it is legal "
                    f"to transition is at time {min_legal_time}."
                )

        transition = get_matching_transition(curr_state, input, self.transitions, strict=strict)

        if transition is None:
            assert not strict
            print("Warning: no next state found; staying in current state.")
            return dict()
        elif transition.is_error:
            raise PylseError(f"Triggered erroneous transition id '{transition.id}'")
        else:
            for inp, min_distance in transition.past_constraints.items():
                if inp is input:
                    # To avoid getting the current time for the input that triggered us
                    last_seen = inp_last_seen
                else:
                    last_seen = self._last_seen[inp]

                if last_seen is not None:  # None would be if it hasn't been seen yet
                    if (actual_dist := (curr_time - last_seen)) < min_distance:
                        raise PylseError(
                            f"Prior input violation on FSM '{self.name}'. A constraint on "
                            f"transition '{transition.id}', triggered at time {curr_time}, "
                            f"given via the 'past_constraints' field says it is an error to "
                            f"trigger this transition if input '{inp}' was seen as recently as "
                            f"{min_distance} time units ago. It was last seen at {last_seen}, "
                            f"which is {min_distance - actual_dist} time units to soon."
                        )

            if transition.transition_time > 0:
                self.curr_state = Transitioning(curr_time, transition)
            else:
                self.curr_state = transition.destination
            # Return name and output delay of the outputs that are firing;
            # simulator will correlate with actual wires. Iterate over `transition.firing`
            # because it may be empty (in which `transition.firing_delay` is empty too).
            return {o: [t] for o, t in transition.firing.items()}

    def sorted_high_inputs(self, inputs: Dict[str, bool]) -> List[str]:
        ''' Return the high inputs, in the deterministic order that they should
        be handled given the current state.
        '''
        s = self.curr_state.transition.destination if isinstance(self.curr_state, Transitioning)\
            else self.curr_state
        ordered_inputs = [ts.trigger for ts in get_transitions_from_source(s, self.transitions)]
        high_inputs = [i for i, high in inputs.items() if high]
        return sorted(high_inputs, key=lambda i: ordered_inputs.index(i))


class Transitional(Element):
    ''' Basic properties and methods necessary for any element that uses an internal FSM '''

    # Dev note: this is an abstractmethod to force the subclasses to define it.
    # Leaving it as an undefined property makes the error message in those cases less clear.
    @property
    @abstractmethod
    def transitions(self) -> List[Dict[str, Union[int, float, str]]]:
        raise NotImplementedError

    # time it takes for an output pulse to appear after a 'firing' transition occurs.
    # each output can specify this individually on each transition on which it is fired.
    firing_delay: float = 0.0

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
        # An absent key, or a key with a None value means to use default
        self._overrides = {k: v for k, v in overrides.items() if v is not None}
        self._set_transition_ids()
        self._sanity_check()
        self._store_fsm_overrides()
        # After this, self.transitions is of type List[NormalizedTransition]
        self._orig_transitions = self.transitions
        self.transitions = self._normalize_transitions()
        self._fsm = FSM(self.name, self.inputs, self.outputs, self.transitions)

    @transitions.setter
    def transitions(self, ts):
        if any(not isinstance(t, NormalizedTransition) for t in ts):
            raise PylseError(
                "Can only set the .transitions propert with only "
                "NormalizedTransitions outside of top-level class definition."
            )
        self._transitions = ts

    @property
    def fsm(self):
        return self._fsm

    def _store_fsm_overrides(self):
        ''' Store certain overrides as class attributes, rather than on transition '''
        # On the FSM, currently recognize:
        # - error_transitions
        # - jjs
        for prop in ['jjs', 'error_transitions']:
            if prop in self._overrides:
                setattr(self, prop, self._overrides[prop])

    def handle_inputs(self, inputs: Dict[str, bool], time: float) -> Dict[str, List[float]]:
        ''' Handle incoming input pulses.

        :param dict[str, bool] inputs: map from input names to a boolean indicating if they
            are high at this time. If multiple are high, that means they are simultaneous,
            and will be passed to the FSM's step function one at a time, **in the priority
            order as defined on the FSM**.
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
            return next(trans for trans in self.transitions if trans.id == str(tid))
        except StopIteration:
            raise PylseError(
                f"Cannot find transition by {tid}; "
                f"available tids are {[t.id for t in self.transitions]}."
            )

    def _sanity_check(self):
        # _These two are special
        from .circuit import _Source, _Sink
        if isinstance(self, (_Source, _Sink)):
            return

        valid_types = {
            'jjs': (int,),
            'firing_delay': (float, int, dict),
            'transition_time': (float, int, dict),
            'error_transitions': (list, set),
            'past_constraints': (float, int, dict),
        }
        for override_name, value in self._overrides.items():
            if value is None:  # Means use default
                pass
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
            if all(k not in t for k in ['source', 'src']):
                raise PylseError(
                    "The given FSM is missing a 'source' (or 'src') key in a transition."
                )
            if all(k in t for k in ['source', 'src']):
                raise PylseError(
                    "Must supply either the 'source' or 'src' key, "
                    "but not both (they are equivalent)."
                )

            if 'trigger' not in t:
                raise PylseError(
                    "The given FSM is missing a 'trigger' key in a transition."
                )

            if all(k not in t for k in ['destination', 'dest']):
                raise PylseError(
                    "The given FSM is missing a 'destination' (or 'dest') key in a transition."
                )

            if all(k in t for k in ['destination', 'dest']):
                raise PylseError(
                    "Must supply either the 'destination' or 'dest' key, "
                    "but not both (they are equivalent)."
                )

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
            flist = t.get('firing', [])
            if isinstance(flist, str):
                flist = [flist]
            if isinstance(flist, dict):
                flist = list(flist.keys())
            for f in flist:
                if f not in self.outputs:
                    raise PylseError(
                        f"Output '{f}' from transition was not "
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
            if isinstance(ttime, (int, float)) and ttime < 0:
                raise PylseError(
                    f"Transition time must be a non-negative number, got {ttime}."
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
                    elif d < 0:
                        raise PylseError(
                            f"Firing delay must be a non-negative number, got {d}."
                        )

                invalid_keys = set(fd.keys()).difference(set(flist))
                if invalid_keys:
                    raise PylseError(
                        "The following keys of a firing delay dictionary are not firing "
                        f"outputs for this transition: {','.join(invalid_keys)}."
                    )
            elif fd < 0:
                raise PylseError(
                    f"Firing delay must be a non-negative number, got {fd}."
                )

            if 'setup_time' in t or 'reset_time' in t:
                raise PylseError(
                    "When giving times for specific transitions, use the key 'transition_time'. "
                )

            illegal_priors = t.get('illegal_priors', dict())
            for k, v in illegal_priors.items():
                if k != '*' and k not in self.inputs:
                    raise PylseError(
                        f"Unrecognized key for 'illegal_priors' dictionary: {k}. "
                        "Must use valid inputs to this machine."
                    )
                if type(v) not in (int, float) or v < 0:
                    raise PylseError(
                        f"Value for an illegal_prior mapping must be non-negative number, got {v} "
                        f"in transition {t['id']}."
                    )

        grouped_by_source = defaultdict(list)
        for ix, t in enumerate(self.transitions):
            grouped_by_source[t['source']].append((ix, t))

        inputs = set(self.inputs)
        for source, group in grouped_by_source.items():
            assert len(group) >= 1
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
                inputs = set(self.inputs)
                for _, t in group:
                    inputs.difference_update(set(key_to_list(t, 'trigger')))
                if inputs:
                    raise PylseError(
                        "No transitions specified for inputs '%s' from state '%s'." %
                        (str(','.join(inputs)), source)
                    )

            # Either all of the transitions in this group have a priority, or none of them do
            priorities = [t.get('priority') for _, t in group if t.get('priority') is not None]
            if len(priorities) > 0 and len(priorities) < len(group):
                raise PylseError(
                    f"Given a set of transitions originating from the same source ('{source}'), "
                    "either all of them must have a priority field, or none of them "
                    "must (in which case the priority is determined by the order in "
                    "which they were given in the transition list)."
                )

            next_legal_priority = 0
            for priority in sorted(priorities):
                if priority > next_legal_priority + 1:
                    raise PylseError(
                        "Given a set of transitions originating from the same source ('idle'), "
                        "set of priorites for that group must be consecutive (i.e. if transitions "
                        "A and C have priority 0, transition B can have priority 0 or 1, but not "
                        "2, since priority 1 hasn't been used yet)."
                    )
                next_legal_priority = priority

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

        all_fired_outputs = set()
        for t in self.transitions:
            firing = t.get('firing', set())
            if isinstance(firing, str):
                firing = [firing]
            if isinstance(firing, dict):
                firing = set(firing.keys())
            all_fired_outputs.update(set(firing))

        # For every output, there exists at least one transition that fires it
        for o in self.outputs:
            if o not in all_fired_outputs:
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
                while str(next_id) in tids:
                    next_id += 1
                res = next_id
                next_id += 1
                return str(res)
            return inner
        next_id = next_available_id()

        for t in self.transitions:
            if 'id' not in t:
                t['id'] = next_id()

    def _normalize_transitions(self):
        ''' Normalize and store transitions, by making sure output delays are
        associated with each firing transition, and that all triggers are fully
        expanded.

        Each transition in self.transitions is a dictionary, and which must have
        at least 'id', 'source', 'dest', and 'trigger' keys
        '''

        _normalized_transitions = []

        # For ultimately getting the priorities
        pix = 0
        prev_source = None

        for transition in self.transitions:

            transition_time = self._overrides.get('transition_time')
            if isinstance(transition_time, (int, float)) and 'transition_time' not in transition:
                # Don't use the overall override if the transition didn't
                # have a transition_time to begin with.
                transition_time = 0
            elif isinstance(transition_time, dict):
                transition_time = transition_time.get(transition['id'])
            if transition_time is None:
                transition_time = transition.get('transition_time', 0)
            if transition_time == 'default':
                transition_time = self.transition_time

            past_constraints = None
            if 'past_constraints' in transition:
                past_constraints = self._overrides.get('past_constraints')
                if isinstance(past_constraints, (int, float)):
                    # For all of those that have past_constraints
                    past_constraints = {'*': past_constraints}
                elif isinstance(past_constraints, dict):
                    past_constraints = past_constraints.get(transition['id'])
                else:
                    past_constraints = transition.get('past_constraints')
            if past_constraints is None:
                past_constraints = dict()
            assert isinstance(past_constraints, dict)
            asterisk_constraint = past_constraints.get('*', 0)
            for i in self.inputs:
                # If i is present in constraint map, use its value.
                # Otherwise use the '*' constraint, if present, otherwise 0.
                past_constraints[i] = past_constraints.get(i, asterisk_constraint)
            try:
                del past_constraints['*']
            except KeyError:
                pass

            firing = transition.get('firing')
            if firing:
                # For each firing transition, each firing output has an associated delay, which is
                # 1) the override delay given by user calling the cell function (e.g. m())
                # 2) the specified delay for the particular output on the transition, if given, else
                # 3) the specified delay for all outputs on the transition, if given, else
                # 4) the default firing delay defined on the class (if any)
                firing_delay = self._overrides.get('firing_delay')
                if firing_delay is None and hasattr(self, 'firing_delay'):
                    firing_delay = self.firing_delay
                if isinstance(firing, str):
                    firing = [firing]
                if isinstance(firing, list):
                    if firing_delay is None:
                        raise PylseError(
                            "Firing delay must specified in class, overrides, "
                            "or via a firing dictionary."
                        )
                    firing = {o: firing_delay for o in firing}
                else:
                    assert isinstance(firing, dict)
                    asterisk_delay = firing.get('*', 0)
                    for o in firing:
                        firing[o] = firing.get(o, asterisk_delay)
            else:
                firing = dict()

            is_error = transition['error'] if 'error' in transition else \
                (transition['id'] in self.error_transitions)
            triggers = key_to_list(transition, 'trigger')

            source = transition.get('source', transition.get('src'))
            destination = transition.get('destination', transition.get('dest'))

            # Lowest number is highest priority (so first defined if no 'priority' field)
            # These transitions are already grouped by source, so this is fine
            if prev_source != transition['source']:
                pix = 0
                prev_source = transition['source']
            priority = transition.get('priority', pix)
            pix += 1

            # If '*' is given, all inputs that aren't explicitly listed
            # are given the min_distance time associated with '*'.
            illegal_priors = transition.get('illegal_priors', dict())
            if (min_distance := illegal_priors.get('*')) is not None:
                illegal_priors = {i: illegal_priors.get(i, min_distance) for i in self.inputs}

            for trigger in triggers:
                _normalized_transitions.append(
                    NormalizedTransition(
                        id=transition['id'],
                        source=source,
                        destination=destination,
                        trigger=trigger,
                        firing=firing,
                        transition_time=transition_time,
                        priority=priority,
                        past_constraints=past_constraints,
                        is_error=is_error,
                    )
                )

        return _normalized_transitions


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
    """ Returns the transitions in priority order.

    In the user-defined Transitional class, the priority is determined by the order
    of the transitions in the list, or the priority field. In NormalizedTransitions,
    this has all already been normalized, so we just check the priority field.
    """
    s = []
    for t in transitions:
        if isinstance(t, dict):
            source = t['source']
        else:
            source = t.source
        if source == source_state:
            s.append(t)
    s = sorted(s, key=lambda t: t.priority)
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
