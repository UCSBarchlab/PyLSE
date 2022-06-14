# In this tutorial, we'll instantiate, simulate, and verify the multiplexer from tutorial 1.

# First, let's import pylse again
import pylse

# And then let's import the Mux element we just created
from tutorial1 import Mux

# To create a Mux element, we first need to create wires
# connect to its input and output ports.
w1, w2, w3, w4, w5 = pylse.Wire(), pylse.Wire(), pylse.Wire(), pylse.Wire(), pylse.Wire()

# Then we create a Mux instance...
muxCell = Mux()

# Add add it and those wires to the working_circuit()'s `add_node` method.
# The working_circuit is a global object holding our entire workspace,
# making it easier to add wires and cells to your design. It will
# take care of associating the given wires with the inputs and outputs
# of the cell (the order in which they are connected is the order in which we
# declared the inputs and outputs on the class, e.g. ['a', 'b', 'clk'] and ['q'], respectively).
pylse.working_circuit().add_node(muxCell, [w1, w2, w3, w4], [w5])

# However, this is a painful way to add things to your circuit.
# Let's instead make a helper function that allows us to treat the creation
# and connection to this cell easier, essentially making something akin to a new
# operator in our PyLSE DSL. We do something similar for all the basic SFQ cells
# at the bottom of the `pylse/sfq_cells.py` file.

def mux_s(a: pylse.Wire, b: pylse.Wire, sel: pylse.Wire, clk: pylse.Wire):
    out = pylse.Wire()
    pylse.working_circuit().add_node(Mux(), [a, b, sel, clk], [out])
    return out

# We're nearly ready to use this new function in creating and simulating a mux!
# Before we do, let's make sure to get rid of the mux we added to the circuit previously:
pylse.working_circuit().reset()

# Now for simulation, let's create four circuit-level input wires.
# We'll also specify **when** we want pulses to be produced on each input.

# We'll make a clock pulse occur once every 50 time units (lets call them picoseconds),
# from 50 ns to 600 ns.
clk = pylse.inp_at(*(i*50 for i in range(1, 12)), name='clk')

# Input a will produce a pulse at 115ns, 165ns, 315ns, and 375ns.
a = pylse.inp_at(115, 165, 315, 375, name='a')

# Input b will produce a pulse at 65, 165ns, 265, and 375ns.
b = pylse.inp_at(65, 165, 265, 375, name='b')

# Input sel will produce a pulse at 215, 265ns, 315, and 365ns.
sel = pylse.inp_at(215, 265, 315, 365, name='sel')

# Passing them to our helper function, we get a wire out...
out = mux_s(a, b, sel, clk)
# ...which we'll give a name by `inspect`ing it.
pylse.inspect(out, 'out')

# Note that the following time plot shows essentially what we're doing
# (time progresses as we go to the right):
#
# clk    50   100   150   200   250   300   350   400   450   500    550
# sel  -    -     -      -    215   265   315   365    -     -
#   a  -    -    115(1) 165(2) -     -    315   375    -     -
#   b  -    65    -     165    -    265(3) -    375(4) -     -
# out  -    -     -     (1)   (2)    -    (3)   -     (4)    -

# We've also put (1) - (4) on the output line to indicate what we expect.
# For example, we expect a pulse to be output at time (1) (between 150 and 200 ns)
# because the mux saw an `a` input (at 155 ns) and no `sel` (e.g. sel=0).

# Let's try it and out see if it produces what we expect!
# First create a simulation object...
sim = pylse.Simulation()
# ...then simulate...
events = sim.simulate()
# ...and finally plot it!
sim.plot(wires_to_display=['clk', 'sel', 'a', 'b', 'out'])

# Finally, we can write some quick tests to validate its correctness.
# We'll use the `events` object, returned from `sim.simulate()`, which
# is a dictionary mapping each named wire to the list of times pulses
# were produced for it.

# For example, from the plot above, we know that there should be four output pulses on `out`:
assert len(events['out']) == 4

# We also know that we set the firing delay for our mux to be 5.0 (see the bottom of tutorial1.py).
# So we can check that output pulse appears that many ns after the appropriate clock, for all
# the ones we expect.
assert events['out'][0] == events['clk'][2] + 5.0
assert events['out'][1] == events['clk'][3] + 5.0
assert events['out'][2] == events['clk'][5] + 5.0
assert events['out'][3] == events['clk'][7] + 5.0

# To check these, run this file like so:
#
#   $ python3.8 tutorial2.py

# Finally, let's verify some of it in UPPAAL.
# To do so, we'll convert the design into UPPAAL-flavored Timed Automata and then run some queries on it.
ta = pylse.export_to_uppaal("mux.xml")

# `ta` is a Timed Automata which stores information about its locations, transitions, and channels.
# We can use it, along with events we generated from simulation, to automatically
# create a correctness query that UPPAAL will run for us. The query will essentially say that given
# the starting pulses, we will always produce the given output. This really serves as an effective
# sanity check that our Timed Automata translation works, allowing us to use it for more complicated
# queries if wanted later.
query1 = pylse.generate_correctness_query(ta, events, exact=True)
with open("mux_correctness.q", "w") as f:
    f.write(query1)

# We can view the query in `mux_correctness.q`. We wrote it to a file
# in order to use it with the UPPAAL binary. Before doing that, though,
# let's generate one more query. This time, a reachability query,
# which says that it's impossible for the Timed Automata to reach an error state.
query2 = pylse.generate_error_reachability_query(ta, events)
with open("mux_reachability.q", "w") as f:
    f.write(query2)

# Finally, let's check the queries. We can do this in the shell ourselves,
# by running the following commands:
#
#   $ verifyta -u -q mux.xml mux_correctness.q
#   $ verifyta -u -q mux.xml mux_reachability.q

print("Run this! `verifyta -u -q mux.xml mux_correctness.q`")
print("Run this! `verifyta -u -q mux.xml mux_reachability.q`")

# If everything works out, we should see, embedded in the UPPAAL output,
# a line reading "Formula is satisfied". If so, congratulations, we've successfully
# created, simulated, and verified our first PyLSE Machine.

# Go to `tutorial3.py`...
