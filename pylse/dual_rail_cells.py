from collections import namedtuple

from .core import Wire
from .circuit import working_circuit
from .sfq_cells import SFQ


# The current restriction on SFQ is that there is a single firing delay,
# rather than allow it to be specified for each transition/output pair,
# which this currently meets. UPPAAL converter would have to be changed
# to allow more than that.
class TWOBYTWOJOIN(SFQ):
    ''' Element: 2x2 Join - dual rail logic '''
    name = 'TWOBYTWOJOIN'
    inputs = ['a_t', 'a_f', 'b_t', 'b_f']
    outputs = ['q00', 'q01', 'q10', 'q11']
    transitions = [
        {'source': 'idle',        'trigger': 'a_f', 'dest': 'a_f_arrived'},
        {'source': 'idle',        'trigger': 'a_t', 'dest': 'a_t_arrived'},
        {'source': 'idle',        'trigger': 'b_f', 'dest': 'b_f_arrived'},
        {'source': 'idle',        'trigger': 'b_t', 'dest': 'b_t_arrived'},

        {'source': 'a_f_arrived', 'trigger': 'b_f', 'dest': 'idle', 'firing': 'q00'},
        {'source': 'a_f_arrived', 'trigger': 'b_t', 'dest': 'idle', 'firing': 'q01'},
        {'source': 'a_f_arrived', 'trigger': 'a_f', 'dest': 'a_f_arrived', 'error': True},
        {'source': 'a_f_arrived', 'trigger': 'a_t', 'dest': 'a_f_arrived', 'error': True},

        {'source': 'a_t_arrived', 'trigger': 'b_f', 'dest': 'idle', 'firing': 'q10'},
        {'source': 'a_t_arrived', 'trigger': 'b_t', 'dest': 'idle', 'firing': 'q11'},
        {'source': 'a_t_arrived', 'trigger': 'a_t', 'dest': 'a_t_arrived', 'error': True},
        {'source': 'a_t_arrived', 'trigger': 'a_f', 'dest': 'a_t_arrived', 'error': True},

        {'source': 'b_f_arrived', 'trigger': 'a_f', 'dest': 'idle', 'firing': 'q00'},
        {'source': 'b_f_arrived', 'trigger': 'a_t', 'dest': 'idle', 'firing': 'q10'},
        {'source': 'b_f_arrived', 'trigger': 'b_f', 'dest': 'b_f_arrived', 'error': True},
        {'source': 'b_f_arrived', 'trigger': 'b_t', 'dest': 'b_f_arrived', 'error': True},

        {'source': 'b_t_arrived', 'trigger': 'a_f', 'dest': 'idle', 'firing': 'q01'},
        {'source': 'b_t_arrived', 'trigger': 'a_t', 'dest': 'idle', 'firing': 'q11'},
        {'source': 'b_t_arrived', 'trigger': 'b_f', 'dest': 'b_t_arrived', 'error': True},
        {'source': 'b_t_arrived', 'trigger': 'b_t', 'dest': 'b_t_arrived', 'error': True},
    ]
    jjs = 0
    firing_delay = 2.0


def join(in0: Wire, in1: Wire, in2: Wire, in3: Wire,
         name_q00=None, name_q01=None, name_q10=None, name_q11=None,
         **overrides):
    Join_out = namedtuple('Join_out', ['q00', 'q01', 'q10', 'q11'])
    q00, q01, q10, q11 = Wire(name_q00), Wire(name_q01), Wire(name_q10), Wire(name_q11)
    working_circuit().add_node(
        TWOBYTWOJOIN(**overrides),
        [in0, in1, in2, in3], [q00, q01, q10, q11]
    )
    return Join_out(q00=q00, q01=q01, q10=q10, q11=q11)
