from abc import ABC, abstractmethod
from typing import Dict, List, ClassVar
from dataclasses import dataclass, field

from .pylse_exceptions import PylseError


def is_temporary_wire_name(name):
    return Wire.is_temporary_wire_name(name)


class Wire():
    # Class attributes
    next_wire_id = 0
    prefix = "_"

    def __init__(self, name=None):
        from .circuit import working_circuit
        self.name = name if name else Wire._new_wire_name()
        self.observed_as = self.name if not is_temporary_wire_name(self.name) else None
        working_circuit().add_wire(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        from .circuit import working_circuit
        circuit = working_circuit()
        existing_wire = circuit.get_wire_by_name(new_name)
        if existing_wire:
            print(f"Warning: a wire with the name {new_name} already exists "
                  "and will be given a new internal name.")
            # Will cause this to be called recursively, but recursion should stop immediately
            existing_wire.name = Wire._new_wire_name()
        circuit._wire_by_name[new_name] = self
        self._name = new_name
        if not Wire.is_temporary_wire_name(self._name):
            self.observed_as = self._name

    @classmethod
    def _new_wire_name(cls) -> str:
        n = f"{Wire.prefix}{Wire.next_wire_id}"
        cls.next_wire_id += 1
        return n

    @classmethod
    def _reset_wire_id(cls):
        cls.next_wire_id = 0

    @staticmethod
    def is_temporary_wire_name(name: str) -> bool:
        return name.startswith(Wire.prefix)

    def __lt__(self, other):
        return self.name < other.name

    # w <<= ...
    def __ilshift__(self, other):
        # Connect self <- other directionally
        from .circuit import _connect, working_circuit
        if self in working_circuit()._src_map:
            raise PylseError(f"Wire '{self.name}' is already connected to a node.")
        if other in working_circuit()._dst_map:
            raise PylseError(f"Wire '{other.name}' is already connected to a node.")
        _connect(other, self)
        return self


class Element(ABC):
    ''' Something that can react to input.

        A child of this class must define:
            * name: str
            * inputs: List[str]
            * outputs: List[str]
            * handle_inputs: Callable[[Dict[str, bool]], float] -> Dict[str, List[float]]
    '''
    @property
    @abstractmethod
    def inputs(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def outputs(self) -> List[str]:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def handle_inputs(self, inputs: Dict[str, bool], time: float) -> Dict[str, List[float]]:
        raise NotImplementedError

    # Expected that subclasses would override these when needed
    @property
    def blif_gate_name(self) -> str:
        return self.name

    @property
    def blif_input_names(self) -> List[str]:
        return self.inputs

    @property
    def blif_output_names(self) -> List[str]:
        return self.outputs


@dataclass(frozen=True)
class Node:
    _next_node_id: ClassVar[int] = 0

    node_id: int = field(init=False, compare=True)
    element: Element = field(compare=False)
    input_wires: List[Wire] = field(compare=False)
    output_wires: List[Wire] = field(compare=False)

    def __post_init__(self):
        object.__setattr__(self, 'node_id', Node._get_next_node_id())

    @classmethod
    def _get_next_node_id(cls):
        nid = cls._next_node_id
        cls._next_node_id += 1
        return nid

    @classmethod
    def _reset_node_id(cls):
        cls._next_node_id = 0

    def get_output_wire(self, name):
        """ Get the Wire object associated with the output name.
        :param name: name of the output on the Element.

        E.g. if you have an Element with outputs ['l', 'r'],
        and a n=Node(..., output_wires[Wire('_1'), Wire('_2')]),
        calling n.get_output_wire('l') will return the object that
        was created with Wire('_1').
        """
        ix = self.element.outputs.index(name)
        return self.output_wires[ix]
