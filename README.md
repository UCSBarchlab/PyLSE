# PyLSE
A **Py**thon embedded **L**anguage for **S**uperconductor **E**lectronics.

PyLSE provides classes for the Pulse-Transfer Level design, simulation, and verification of
superconductor electronics (SCE). SCE are an attractive alternative to CMOS because of SCE's
low power dissipation and ultra-high switching speed, but unfortunately they are difficult to
design for due to their pulse-based information encoding and stateful nature. The purpose of
PyLSE is to make it easier to create precise and composable models of the basic SCE cells (i.e. gates),
use these models to create larger systems, quickly get up and running in the built-in simulation
framework, and finally prove various properties about these cells and systems using a state-of-the-art
model checker.

## Installation
To install PyLSE, do the following:

1. First install some useful programs using your OS's package manger

    a. If on Ubuntu

       apt-get install -y libgraphviz-dev
       apt-get install -y graphviz

    b. If on Mac

       brew install graphviz

2. If you want to use the UPPAAL model checker, install it as well.

    a. Download UPPAAL from [their website](https://www.it.uu.se/research/group/darts/uppaal/download/registration.php?id=0&subid=13)
       (it is currently free for non-commercial use).  We have tested our code using version 4.1.26.

    b. Unzip the file somewhere in your system

       unzip uppaal64-4.1.26.zip

    c. Update the system path to include the path to these new binaries

       export PATH=/path/to/uppaal64-4.1.26/bin-Linux:$PATH 
       # OR
       export PATH=/path/to/uppaal64-4.1.26/bin-Darwin:$PATH 

2. Then install the Python package requirements:

       pip3 install -r requirements.txt

3. Finally install the PyLSE package to your system via **one** of the following:

    a. Normal installation:

       pip3 install .

    b. Editable installation (i.e. you plan on making changes to PyLSE itself):

       pip3 install -e .

The above commands have been tested to work with Python 3.8 and Python 3.9. If you have one or both of those installed, you may need to replace the `pip3` commands above with `pip3.8` or `pip3.9`, respectively, for a more targeted installation.

## A Small Tutorial

We've provided a small tutorial on how to create your own cell, simulate it as part of a circuit, write some
tests for it, and generate and verify the circuit using UPPAAL. We'll also show you how to create and
simulate your own functional "hole".

To access the tutorial, cd into `tutorial` and open the tutorials one by one, in order.

    cd tutorial

    vim tutorial1.py
    python3.8 tutorial1.py

    vim tutorial2.py
    python3.8 tutorial2.py

    vim tutorial3.py
    python3.8 tutorial2.py


## Implementation Details

Our code is found in the `pylse/` directory.
We've divided the implementation into the following files:

   * `analysis.py` contains helper functions for doing analysis on
      paths and path delays.
   * `circuit.py` contains the Circuit class, which holds information
      about the circuit being constructed (i.e. nodes, wires, sources, and sinks).
   * `core.py` contains the Wire and Element classes; the former is the base of
      things that can react to input and produce output.
   * `dual_rail_cells.py` defines the `join` element, a base cell of dual-rail logic
   * `functional.py` contains the Functional element class, which allows normal
      Python functions to be wrapped using the @hole decorator to interact with
      other elements.
   * `helper_funcs.py` holds helper functions, the only of which is currently
      inspect(), for tracking arbitrary wires for the output waveform.
   * `io.py` contain functions for importing and running normal HDL code (specifically
      PyRTL code) that has been sufficiently transformed into an XSFQ-like netlist.
      The eventual purpose of this file will be to interact with BLIF and other formats as well.
   * `pylse_exceptions.py` is for defining exceptions used throughout the code.
   * `sfq_cells.py` contain the definitions of the basic elements of RSFQ, defined as
      transition systems in classes that extend the SFQ (and in turn Transitional) base classes.
   * `simulation.py` contains the simulation code used for running your circuit.
   * `transitional.py` contains the Transitional class, which extends the notion of the Element
      class to one which uses an internal finite state machine/transitions for interacting
      with time-based inputs and producing outputs at certain times.
   * `uppaal.py` contains our code for producing UPPAAL-flavored timed automata and queries
      compatible with the UPPAAL model checkers from our internal PyLSE machines.
   * `visual.py` contains the code for generating the waveforms we produce after simulation.

# Paper

More details can be found in the accompanying PLDI paper:

["PyLSE: A Pulse-Transfer Level Language for Superconductor Electronics"](https://doi.org/10.1145/3519939.3523438)
Michael Christensen, Georgios Tzimpragos, Harlan Kringen, Jennifer Volk, Timothy Sherwood, Ben Hardekopf.
Proceedings of the 43rd ACM SIGPLAN International Conference on Programming Language Design and Implementation (PLDI), June 2022. San Diego, CA, USA.

# Licensing

The license for the pyuppaal code is found in third-party/pyuppaal/LICENSE.
All other code is licensed under the license found in the present directory, `LICENSE` (BSD 3-Clause License).

## Contact
For general questions, feel free to reach out to [Archlab @ UCSB](https://www.arch.cs.ucsb.edu/).

For immediate help with PyLSE, contact Michael (mchristensen@ucsb.edu) and George (gtzimpragos@ucsb.edu).
