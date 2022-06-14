# We've now seen how to create and instantiate our own PyLSE Machines
# and how to connect them with input and output wires in the circuit
# for simulation. We've also seen how to verify some queries about them
# in UPPAAL.

# To finish this set of tutorials, we'll discuss how to create
# Functional holes. A "hole" is an element in a design which doesn't
# have a straightforward transition-system based implementation.
# A classic example of this is memory. In order to simulate systems
# involving such blocks, we need a way to emulate how a memory
# would interact with a pulse-based system.

# To do so, PyLSE provides the Functional abstract class. This
# class is essentially a way to wrap a Python function behind
# a pulse-based I/O interface. As it allows any Python expression
# to be used, we lose the ability to verify it in UPPAAL (since there
# is no PyLSE machine representation), but we gain the added
# productivity of being able to use arbitrary Python functions directly.
# As usual, we first import pylse.
import pylse

# For this example, we'll create function that multiplies two 2-bit numbers together.
# As part of the pulse-based interface, we need to remember if each bit of each number
# has arrived since our last clock. We do that via simple Python variables. A zero
# means it hasn't arrived yet.
a = 0
b = 0

# Now to start the actual hole, we create a pylse.hole decorator, which specifies
# information about the delay outputs take to fire, once triggered, and the ordered
# list of inputs and output wires. We specify "2-bit" because for now, PyLSE operates
# on 1-bit wires at a time, so each 2-bit number will require two wires.
@pylse.hole(delay=5.0, inputs=['a1', 'a0', 'b1', 'b0', 'clk'], outputs=['o3', 'o2', 'o1', 'o0'])

# Next we define the actual multiplication function. This should be fairly
# straightforward; we just need to unmarshall the input data, perform the operation
# and marshall the output data. It's important to note that the order of inputs
# in the decorator's inputs list needs to match the order of the formal parameters below.
# Also, PyLSE automatically adds a `time` parameter, which is the time at which
# a particular input pulse arrives. For this example, we won't use it, but it's helpful
# for debugging, adding metalogical checks, etc.
#
# Note that *all* of these inputs besides time are boolean valued (i.e. they will always be
# either 0 or 1). This function will be called by the PyLSE simulator **every** time
# at least one of the inputs has a pulse incoming.
def multiply(a1, a0, b1, b0, clk, time):

    # Let's refer to the variables we track for remembering
    global a, b

    # Since we have 2 1-bit wires for each number, we'll store
    # what's been seen by doing an appropriate shift (or just *2 in this case for bit 1).
    # This works because when inputs are 0, the |= (in-place or) keeps it high if it was
    # high previously, while when inputs are 1, the |= sets the bit high
    a |= a1 * 2 + a0
    b |= b1 * 2 + b0

    # When clk is high, it's time to output something.
    # We output the result of multiplying a * b, which have been set
    # to whatever we've seen since the last clk pulse.
    if clk:
        assert a <= 3
        assert b <= 3
        value = a * b
        # Finally, after seeing a clock, we must set all the variables
        # we use for remembering back to zero, since we're starting a new cycle.
        a = b = 0
    else:
        value = 0

    # Now marshall the output data into 4 separate bits, one to go on each wire,
    # form most-significant to least-significant.
    return ((value >> 3) & 1), ((value >> 2) & 1), ((value >> 1) & 1), value & 1

# And that's the hole!
# Now we can instantiate it, like we did for a mux in tutorial 2.
# Though before doing so, let's create some input wires connect to it.

a1 = pylse.inp_at(125, 175, 225, 325, name='a1')
a0 = pylse.inp_at(75, 175, 225, 275, 375, name='a0')
b1 = pylse.inp_at(75, 175, 225, 325, 375, name='b1')
b0 = pylse.inp_at(25, 75, 125, 175, 275, name='b0')
clk = pylse.inp(start=50, period=50, n=8, name='clk')

# What we're essentially doing is creating a series of pulses like the following graph
# (time moves to the right):
#
#   clk         50      100       150       200       250       300      350     400
#   a[1:0] 0b00    0b01      0b10      0b11      0b11      0b01     0b10    0b01
#    a1                        |         |         |                  |       |
#    a0              |                   |         |         |                |
#   b[3:0] 0b01    0b11      0b01      0b11      0b10      0b01     0b10    0b10
#    b1              |                   |         |                  |       |
#    b0      |       |         |         |                   |
#   q[3:0] 0b0000  0b0011    0b0010    0b1001    0b0110    0b0001   0b0100  0b0010
#    q3                                       |
#    q2                                                 |                  |
#    q1                   |         |                   |                          |
#    q0                   |                   |                   |

# For example, it shows that between the clock pulse at 100 and the clock pulse
# at 150, a pulse on a1 arrives and a pulse on arrives on b0. This corresponds to
# a=0b10 (i.e. 2) and b=0b01 (i.e. 1). Since 2*1 = 2, we expect to see q=0b0010, i.e.
# a pulse on q1, some time after the next clock pulse at 150, and no clock pulses
# on the other output wires during that clock interval.

# So now we'll create and instantiate the multiply functional block ("hole"),
# passing in these input wires and getting some wires as a result.
q3, q2, q1, q0 = multiply(a1, a0, b1, b0, clk)

# We inspect them to be able to seem them in the plot.
pylse.inspect(q3, 'q3')
pylse.inspect(q2, 'q2')
pylse.inspect(q1, 'q1')
pylse.inspect(q0, 'q0')

# Let's simulate.
sim = pylse.Simulation()
events = sim.simulate()
# We specify the wires explicitly to set the order in which they appear.
# Now we can very easily compare them to what we expect above.
sim.plot(wires_to_display=['clk', 'a1', 'a0', 'b1', 'b0', 'q3', 'q2', 'q1', 'q0'])

# Finally, we can write some quick tests to validate its correctness.
# We'll use the `events` object, returned from `sim.simulate()`, which
# is a dictionary mapping each named wire to the list of times pulses
# were produced for it.

# For example, from the plot above, we know there the values produced
# on output wires, when concatenated together from q3 to q0, should be:
# 0, 3, 2, 9, 6, 1, 4, 2

# Let's create a quick function for converting these 4 1-bit output wires
# into a single value, based on the starting clock interval:
def concat_wires(clock_start):
    def get(xs):
        for event in xs:
            if clock_start <= event <= clock_start + 50:
                return 1
        return 0
    
    q3 = get(events['q3'])
    q2 = get(events['q2'])
    q1 = get(events['q1'])
    q0 = get(events['q0'])
    return q3 * 8 + q2 * 4 + q1 * 2 + q0

# Using that, we can validate our multiplier.
assert concat_wires(50) == 0
assert concat_wires(100) == 3
assert concat_wires(150) == 2

# For example, the output wires between 200 and 250 ns,
# q3=1 q2=0 q1=0 q0=1, concatenated together, creates
# 0b1001, which is equal to 9! Notice that in the previous
# cycle, a1=1 a0=1 (3) and b1=1 b0=1 (3), so 3*3 = 9.
assert concat_wires(200) == 9
assert concat_wires(250) == 6
assert concat_wires(300) == 1
assert concat_wires(350) == 4
assert concat_wires(400) == 2

# To check these, run this file like so:
#
#   $ python3.8 tutorial3.py

# And we're done! We've now been introduced to the basics of PyLSE, how to create our own PyLSE machine,
# simulate and verify it, and create and simulate a functional "hole".
