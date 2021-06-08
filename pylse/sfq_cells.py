# pylint: disable=no-member
from abc import abstractmethod
from collections import namedtuple
from typing import Tuple

from .pylse_exceptions import PylseError
from .core import Wire
from .transitional import Transitional

# Notes:
# - order of transitions matters (defined priority for inputs that arrive simultaneously)
# - trigger 'a' means "a arrived", says nothing about b (apart from priority order explained above)
# - trigger ['a', 'b'] means 'a' or 'b' will cause the transition; if both occur simultaneously, the
#   left-most (here 'a') will be handled first.
# - if the transition system is underspecified, there will be an error produced *unless* you set
#   `strict=False` on the defining class.
# - transitions with the same source should be defined next to each other (id doesn't matter; it's
#   for enforcing a visual nicety on the user)
# - if 'transition_time' key's value is 'default', use transition_time defined on class,
#   otherwise set it to 0


class SFQ(Transitional):
    ''' SFQ Transitional subclass (an abstract class).

    A child of this class must define, in addition to the properties
    expected from the Transitional (and thus also Element) classes,
    the following specific to SFQ:
        * jjs (int), the number of jjs in this element

    These can be overridden in the initializer, and will otherwise
    use the defaults specified on the class.

    This class defines a useful general initializer (though some subclasses
    are probably going to need to define their own).
    '''
    @property
    @abstractmethod
    def jjs(self) -> int:
        raise NotImplementedError


################
# Asynchronous #
################
class JTL(SFQ):
    ''' Element: Josephson Transmission Line '''
    name = 'JTL'
    inputs = ['a']
    outputs = ['q']
    transitions = [
        {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': 'q'},
    ]
    jjs = 2
    firing_delay = 5.7


class C(SFQ):
    ''' Element: C-element (Coincidence junction)

    No setup time.
    '''
    name = 'C'
    inputs = ['a', 'b']
    outputs = ['q']
    transitions = [
        {'id': '0', 'source': 'idle',      'trigger': 'a', 'dest': 'a_arrived'},
        {'id': '1', 'source': 'idle',      'trigger': 'b', 'dest': 'b_arrived'},
        {'id': '2', 'source': 'a_arrived', 'trigger': 'a', 'dest': 'a_arrived'},
        {'id': '3', 'source': 'a_arrived', 'trigger': 'b', 'dest': 'idle',       'firing': 'q', 'transition_time': 8.0},  # noqa
        {'id': '4', 'source': 'b_arrived', 'trigger': 'b', 'dest': 'b_arrived'},
        {'id': '5', 'source': 'b_arrived', 'trigger': 'a', 'dest': 'idle',       'firing': 'q', 'transition_time': 8.0},  # noqa
    ]
    jjs = 5
    firing_delay = 8.0


class C_INV(SFQ):
    ''' Element: Inverted C-element '''
    name = 'C_INV'
    inputs = ['a', 'b']
    outputs = ['q']
    # NOTE: We're explicitly putting transition 2 before 3 to mean we've prioritized handling
    # 'a' if both 'a' and 'b' arrive at the exact same time; likewise, putting transition 4 before
    # 5 means we've prioritized handling 'b' if both 'a' and 'b' arrive at the exact same time.
    transitions = [
        {'id': '0', 'source': 'idle',      'trigger': 'a', 'dest': 'a_arrived', 'firing': 'q'},
        {'id': '1', 'source': 'idle',      'trigger': 'b', 'dest': 'b_arrived', 'firing': 'q'},
        {'id': '2', 'source': 'a_arrived', 'trigger': 'a', 'dest': 'a_arrived'},
        {'id': '3', 'source': 'a_arrived', 'trigger': 'b', 'dest': 'idle', 'transition_time': 9.0},  # noqa
        {'id': '4', 'source': 'b_arrived', 'trigger': 'b', 'dest': 'b_arrived'},
        {'id': '5', 'source': 'b_arrived', 'trigger': 'a', 'dest': 'idle', 'transition_time': 9.0},  # noqa
    ]
    jjs = 3
    firing_delay = 9.0


class M(SFQ):
    ''' Element: Merger (Confluence junction) '''
    name = 'M'
    inputs = ['a', 'b']
    outputs = ['q']
    transitions = [
        {'source': 'idle', 'trigger': 'a', 'firing': 'q', 'dest': 'idle', 'transition_time': 'default'},  # noqa
        {'source': 'idle', 'trigger': 'b', 'firing': 'q', 'dest': 'idle', 'transition_time': 'default'},  # noqa
    ]
    jjs = 5
    firing_delay = 4.0


class S(SFQ):
    ''' Element: Splitter '''
    name = 'S'
    inputs = ['a']
    outputs = ['l', 'r']
    transitions = [
        {'source': 'idle', 'trigger': 'a', 'dest': 'idle', 'firing': ['l', 'r']},
    ]
    jjs = 3
    firing_delay = 4.3


###############
# Flip Flops  #
###############
class DRO(SFQ):
    ''' Element: Destructive read-out (AKA DFF) '''
    name = 'DRO'
    inputs = ['a', 'clk']
    outputs = ['q']
    transitions = [
        {'id': '0', 'source': 'idle',      'trigger': 'a',   'dest': 'a_arrived', 'transition_time': 2.3},  # noqa
        {'id': '1', 'source': 'idle',      'trigger': 'clk', 'dest': 'idle', 'transition_time': 5.1},  # noqa
        {'id': '2', 'source': 'a_arrived', 'trigger': 'a',   'dest': 'a_arrived'},
        {'id': '3', 'source': 'a_arrived', 'trigger': 'clk', 'dest': 'idle', 'firing': 'q', 'transition_time': 5.1},  # noqa
    ]
    jjs = 6
    firing_delay = 5.1


# For all of these helpers, the **option dictionary argument can take the following:
# - jjs (int): number of JJs in the DRO_SR created (defaults to DRO_SR's default)
# - firing_delay (float): firing delay in the DRO_SR created (defaults to DRO_SR's default)
# - error_transitions (set[str]): ds of the transitions which should be considered erroneous


def jtl(in0: Wire, name=None, **overrides):
    ''' Create and connect a JTL

    :param Wire in0: input wire
    :param str name: Name to give the output wire
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    '''
    from .circuit import working_circuit
    out = Wire(name)
    working_circuit().add_node(JTL(**overrides), [in0], [out])
    return out


def c(in0: Wire, in1: Wire, name=None, **overrides):
    ''' Create and connect an C element

    :param Wire in0: first input
    :param Wire in1: second input
    :param str name: Name to give the output wire
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    '''
    from .circuit import working_circuit
    out = Wire(name)
    working_circuit().add_node(C(**overrides), [in0, in1], [out])
    return out


def c_inv(in0: Wire, in1: Wire, name=None, **overrides):
    ''' Create and connect an C_INV element

    :param Wire in0: first input
    :param Wire in1: second input
    :param str name: Name to give the output wire
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    '''
    from .circuit import working_circuit
    out = Wire(name)
    working_circuit().add_node(C_INV(**overrides), [in0, in1], [out])
    return out


def m(in0: Wire, in1: Wire, name=None, **overrides):
    ''' Create and connect an M element
    :param Wire in0: first input
    :param Wire in1: second input
    :param str name: Name to give the output wire
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    '''
    from .circuit import working_circuit
    out = Wire(name)
    working_circuit().add_node(M(**overrides), [in0, in1], [out])
    return out


def s(in0: Wire, left_name=None, right_name=None, **overrides):
    ''' Create and connect a single splitter element

    :param Wire in0: wire to split
    :param str left_name: Name to give the left output wire
    :param str right_name: Name to give the right output wire
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    :return namedtuple: a tuple for accessing the outputs, .left and .right
    '''
    from .circuit import working_circuit
    S_out = namedtuple('S_out', ['out1', 'out2'])
    out1, out2 = Wire(left_name), Wire(right_name)
    working_circuit().add_node(S(**overrides), [in0], [out1, out2])
    return S_out(out1=out1, out2=out2)


def dro(in0: Wire, clk: Wire, name=None, **overrides):
    ''' Create and connect a DRO

    :param Wire in0: input wire
    :param Wire clk: input wire traditionally corresponding to a clock signal
    :param str name: Name to give the output wire
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    :return: output wire from the DRO element
    '''
    from .circuit import working_circuit
    out = Wire(name)
    working_circuit().add_node(DRO(**overrides), [in0, clk], [out])
    return out


def split(w, n=2, names=None, **overrides) -> Tuple[Wire, ...]:
    ''' Split a wire n ways, by creating n-1 splitter elements in a binary tree

    :param Wire w: wire to split
    :param int n: number of wires to return
    :param Union[list[str], str] names: list of names to give each output wire; if given,
        must be equal in length to n. Can also be a string of whitespace-separated names.
        The order of the names is left-to-right order of the resulting splitter tree.
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    :return: n new wires originating from w
    '''
    if names:
        if isinstance(names, str):
            names = names.split(' ')
        if len(names) != n:
            raise PylseError("Number of names given does not equal number of "
                             "output wires produced.")
    else:
        names = [None] * n

    def f(w, n, names):
        if n == 1:
            return (w,)
        else:
            ln = n // 2
            rn = n - ln
            assert(len(names) >= 2)
            left_name = names[0] if ln == 1 else None
            right_name = names[1] if rn == 1 else None
            w1, w2 = s(w, left_name=left_name, right_name=right_name, **overrides)
            return f(w1, ln, names[:ln]) + f(w2, rn, names[ln:])

    return f(w, n, names)


def jtl_chain(w, n, names=[], **overrides) -> Wire:
    ''' Create a chain of n JTL elements

    :param Wire w: wire to enter the first JTL in the chain
    :param int n: number of JTLs in the chain
    :param Union[list[str], str] names: names for each wire resulting from
        the last len(names) JTLs in the chain. If names is a string, it's assumed that each
        individual name is separated by whitespace; thus, you can do names='foo' to give the
        last wire a name 'foo'.
    :param dict overrides: keyword arguments for overriding defaults of the element,
        such as: jjs, firing_delay, transition_time, error_transitions.
    :return: wire coming out of the final JTL
    '''
    if names:
        if isinstance(names, str):
            names = names.split(' ')
        if len(names) > n:
            raise PylseError("Too many names given for jtl_chain wires.")

    names = [None] * (n - len(names)) + names
    for ix in range(n):
        w = jtl(w, names[ix], **overrides)
    return w
