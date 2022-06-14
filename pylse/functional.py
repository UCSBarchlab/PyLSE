from abc import abstractmethod
import functools
from typing import Callable, List, Dict, NamedTuple
import inspect

from .circuit import working_circuit
from .core import Element, Wire
from .pylse_exceptions import PylseError


class Functional(Element):
    @property
    def firing_delay(self) -> Dict[str, float]:
        return self._firing_delay

    @property
    def inputs(self) -> List[str]:
        return self._inputs

    @property
    def outputs(self) -> List[str]:
        return self._outputs

    @property
    def name(self) -> str:
        return self._name

    def __init__(self, func: Callable, inputs, outputs, firing_delay=0.0, dict_io=False, name=None):
        self.func = func  # for each output, value can be 1/0/True/False
        self._firing_delay = firing_delay if isinstance(firing_delay, dict) \
            else {o: firing_delay for o in outputs}
        self._inputs = inputs  # names of the inputs, for going circuit->functional framework
        self._outputs = outputs  # names of the outputs, for going functional->circuit framework
        self.dict_io = dict_io  # if True, pass a dictionary to the wrapped function
        self._name = name if name is not None else 'Functional'

    def handle_inputs(self, inputs: Dict[str, bool], time: float) -> Dict[str, List[float]]:
        firing = {}
        if self.dict_io:
            # Pass in dictionary so that inputs can be accessed by key
            res = self.func(inputs, time=time)
        else:
            sorted_inputs = [inputs[i] for i in self._inputs]
            res = self.func(*sorted_inputs, time=time)

        if not self.dict_io:
            if isinstance(res, dict):
                res = list(res.values())
            elif not isinstance(res, (list, tuple)):
                res = (res,)

        def check_output(ix, o):
            if self.dict_io:
                if o not in res:
                    raise PylseError(f"Output '{o}' is not found in dictionary "
                                     f"returned from call to functional hole: {res}.")
                return res[o]
            else:
                return res[ix]

        # firing is a dict from output str -> [float];
        # if a key is present, it means that output produces a pulse at the given float time
        firing = {}
        for ix, o in enumerate(self.outputs):
            if check_output(ix, o) == 1:
                firing[o] = [self.firing_delay[o]]
        return firing


def hole(delay, inputs, outputs, dict_io=False, name=None):
    def inner(func):
        argspec = inspect.getfullargspec(func)
        if 'time' not in argspec.args:
            raise PylseError("Hole functions must have an argument named 'time'.")

        @functools.wraps(func)
        def wrapper(*input_wires):
            # input_wires: list[Wire]
            f = Functional(func, inputs, outputs, firing_delay=delay, dict_io=dict_io, name=name)
            output_wires = [Wire() for _ in range(len(outputs))]
            working_circuit().add_node(f, inputs=list(input_wires), outputs=output_wires)
            return output_wires if len(output_wires) > 1 else output_wires[0]
        return wrapper
    return inner
