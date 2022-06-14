# This tutorial will teach you how to create a multiplexer ("mux") in PyLSE.
# In the next tutorial, we'll simulate and verify it.

# First we need to import the PyLSE library
import pylse

# To create our very own PyLSE Machine, we create a Python class which extends the
# the SFQ abstract class (a class defined in the PyLSE library).
class Mux(pylse.SFQ):

    # Let's give the class a good docblock so others know what it's all about:
    ''' Synchronous Multiplexer

    Emulates a multiplexer in SFQ, taking in four inputs (a, b, sel, and clk) and
    producing a single output (q).
    '''

    # Then we actually give it its shortname, inputs, and outputs that
    # the system will use for identifying it and its I/O.
    name = 'MUX'
    inputs = ['a', 'b', 'sel', 'clk']
    outputs = ['q']

    # Now for the meat of the class definition: the transition system.
    # Each transition is a dictionary mapping transition part names to their
    # values. Every transition *must* have the following keys:
    #   - source (a string)
    #   - dest (a string)
    #   - trigger (a string), which names the input that caused
    #     this transition to fire
    #
    # They can optionally also have
    #   - transition_time (a float), for defining how long it takes
    #     to go from the 'source' state to the 'dest' state. This
    #     defaults to 0 for each transition.
    #   - firing (a string or list of strings), for specifying the
    #     output(s) that fire as result of this transition. This
    #     defaults to an empty list for each transition.
    #   - past_constraints (a dictionary), for specifying the minimum
    #     time that must have elapsed since seeing a particular
    #     input before the current transition is allowed to legally
    #     fire. We won't be using this here, but just know that
    #     it is used in various of the other SFQ cells and its values
    #     mainly come from experiments using analog circuit designs.
    #     This defaults to an empty dict for each transition.
    #   - id (a string), which makes it a little easier for
    #     PyLSE to notify you about errors for a given transition.
    #     This defaults to an auto-generated (and not super useful)
    #     string for each transition.
    #   - priority (an int), which we can use to specify what
    #     transition to take if two inputs arrive at the same exact
    #     time (the lower the int, the higher the priority). If not given,
    #     the transitions are prioritized by their order in the list
    #     (per source state), and it's okay to given one or more transitions
    #     originating from the same source the same priority.
    #
    # Finally, at least one state must be 'idle' (meaning at least
    # one transition must have a 'source': 'idle' key-value pair).
    # Note that you don't need to specify the name of the states you'll
    # be using anywhere, besides their use in the transitions themselves
    # (meaning, use and create them as you need them!).
    #
    #
    # So now that we know what goes into a transition, let's recap how the
    # multiplexer of the CMOS world works. If input `sel` has a low voltage,
    # the value in input `a` is passed along to output `q`. Otherwise, if
    # input `sel` has a high voltage, the value in put `b` is passed along
    # to output `q`.
    #
    # In the superconducting world, however, since we're dealing with pulses,
    # we 1) need a way to remember that an input has been seen and 2) recognize
    # when a new set of inputs can arrive. For 1) we use internal states and
    # for 2) we rely on the input `clk` for letting us know when it's time
    # to start awaiting for all inputs anew. Essentially, when we see
    # a `clk` pulse, we need to check if we've seen a `sel` and `b` pulse
    # in the past interval, or if we've explicitly *not* seen a `sel` pulse but
    # have seen an `a` pulse in the past interval, and output a pulse on `q`
    # in exactly those two instances. So let's make some transitions!

    transitions = [
        # If we see an `a` pulse in the `idle` state, go to the `a_arrived` state
        # to remember we saw it. We set this and the following two to priority
        # 1 to say it doesn't matter which we handle first if both `a` and `b`
        # arrive at the same time. This is a "1" because we want the `clk` pulse
        # to have the greatest priority (set to 0 later).
        {'source': 'idle', 'trigger': 'a', 'dest': 'a_arrived', 'priority': 1},

        # If we see a `b` pulse in the `idle` state, go to the `b_arrived` state
        # to remember we saw it.
        {'source': 'idle', 'trigger': 'b', 'dest': 'b_arrived', 'priority': 1},

        # If we see a `sel` pulse in the `idle` state, go to `sel_arrived` state,
        # again to remember we saw it (and only it, so far).
        {'source': 'idle', 'trigger': 'sel', 'dest': 'sel_arrived', 'priority': 1},

        # If we see a `clk` pulse in the `idle` state, that means we didn't see
        # any other pulse since the last `clk`, so we'll go back to `idle` and
        # begin waiting for everything again.
        {'source': 'idle', 'trigger': 'clk', 'dest': 'idle', 'priority': 0},

        # Okay, now we'll start handling some logic.
        # If we've seen an `a` input and see another `a`, we should stay where we are.
        # In the real world, that probably won't happen too much, but we want our
        # transition system to be fully specified for completeness' sake.
        {'source': 'a_arrived', 'trigger': 'a', 'dest': 'a_arrived', 'priority': 1},

        # If we've seen an `a` and then see a `b`, let's remember we've seen both
        # with a new state.
        {'source': 'a_arrived', 'trigger': 'b', 'dest': 'a_and_b_arrived', 'priority': 1},

        # If we've seen an `a` and then see a `sel`, we can forget that
        # `a` arrived. Why? A `sel` coming in means we'll output whatever
        # arrives from `b`, and we haven't seen a `b` yet. So we'll go to the
        # `sel_arrived` state we also used earlier in one of the transitions
        # out of `idle, and wait for `b`.
        {'source': 'a_arrived', 'trigger': 'sel', 'dest': 'sel_arrived', 'priority': 1},

        # Finally, if we've seen an `a` and see the `clk` now, that means
        # we haven't seen a `sel`, which in turn means we should output a pulse.
        # This is in effect forwarding the `a` input through to `q` when `sel=0`,
        # which is exactly what happens in the CMOS case too (though here we need
        # the clock to tell us when to actually do the forwarding). We use
        # the 'firing' key to say this, and we can go back to idle and start listening
        # for pulses anew.
        {'source': 'a_arrived', 'trigger': 'clk', 'dest': 'idle', 'firing': 'q', 'priority': 0},

        # Now we'll handle transitions eminating from the `b_arrived` state, that is,
        # we've already seen at least one `b` input at this point.
        # If we're in `b_arrived` and see an `a`, let's remember we've seen both.
        # We can reuse the same destination state we created in the "`b` arrives while
        # in the `a_arrived` state" transition above.
        {'source': 'b_arrived', 'trigger': 'a', 'dest': 'a_and_b_arrived', 'priority': 1},

        # If we've seen a `b` and then see another `b`, just stay here.
        {'source': 'b_arrived', 'trigger': 'b', 'dest': 'b_arrived', 'priority': 1},

        # If we've seen a `b` and receive a `sel` pulse, these are the conditions
        # needed for outputing a pulse on `q`. So we go to a state to remember this, waiting
        # for `clk` to arrive.
        {'source': 'b_arrived', 'trigger': 'sel', 'dest': 'b_and_sel_arrived', 'priority': 1},

        # Finally, if we've seen a `b` and see a `clk`, this means we never saw a
        # `sel`. In CMOS terms, that means `sel=0`, and so whatever was in `a` would be
        # forwarded. We now by being in this state that we never saw `a` either, so
        # nothing (i.e. 0) is output, and we just go back to idle.
        {'source': 'b_arrived', 'trigger': 'clk', 'dest': 'idle', 'priority': 0},

        # Now we'll handle transitions starting from the 'a_and_b_arrived' state.
        # The first is straightforward, and takes advantage of shorthand by
        # by specifying the two separate input that could trigger this transition.
        {'source': 'a_and_b_arrived', 'trigger': ['a', 'b'], 'dest': 'a_and_b_arrived', 'priority': 1},

        # If we've seen both `a` and `b` and then see `sel`, this is just like
        # as if we've seen just a `b` (i.e. `b_arrived) and saw the `sel`, so
        # we also go to a state to remember this, like three transitions above.
        {'source': 'a_and_b_arrived', 'trigger': 'sel', 'dest': 'b_and_sel_arrived', 'priority': 1},

        # Finally, if we've seen both `a` and `b` and then see `clk`, this
        # means we never saw `sel` so far, and thus we behave the same as if
        # we had only seen `a` and `clk`, 7 transitions above. We can fire!
        {'source': 'a_and_b_arrived', 'trigger': 'clk', 'dest': 'idle', 'firing': 'q', 'priority': 0},

        # Now we'll handle transitions leaving `sel_arrived`.
        # When we see `a` or `sel_arrived`, we'll just stay here. Why? The `a` doesn't
        # affect what will be output when `sel=1`, so we can essentially ignore it
        # and only remember that `sel` has arrived (meaning remain in this state).
        {'source': 'sel_arrived', 'trigger': ['a', 'sel'], 'dest': 'sel_arrived', 'priority': 1},

        # Since `b` does affect what is output when `sel=1`, we go to the state to remember
        # `b` arrived.
        {'source': 'sel_arrived', 'trigger': 'b', 'dest': 'b_and_sel_arrived', 'priority': 1},

        # When `clk` comes in, we saw `sel` previously but no `b`. This is as is
        # if `b` was 0, so we would, in CMOS land, output a 0. Outputing a 0 in SCE
        # land is essentially the same thing as just not outputing any pulse for this
        # time period, so we just go back to `idle`, outputing nothing.
        {'source': 'sel_arrived', 'trigger': 'clk', 'dest': 'idle', 'priority': 0},

        # Now we'll handle transitions starting from `b_and_sel_arrived`.
        # These states mean that we've seen `a` and `sel`, and have yet to see a `clk`.
        # Seeing `a` doesn't affect us because we've seen a `sel`, meaning only `b`'s value matters.
        # Neither does seeing any other input besides `clk`.
        {'source': 'b_and_sel_arrived', 'trigger': ['a', 'b', 'sel'], 'dest': 'b_and_sel_arrived', 'priority': 1},

        # Seeing `clk` signals that it's time to output on `q`, since we've seen both `b` and `sel`
        # previously. This is similar to the CMOS world, where `sel` forwards whatever is on the `b`
        # input.
        {'source': 'b_and_sel_arrived', 'trigger': 'clk', 'dest': 'idle', 'firing': 'q', 'priority': 0}
    ]

    # We must also declare the time it takes for the output pulse
    # to appear one triggered. For that, we must have two ways
    # of proceeding: a `firing_delay` property on the class,
    # or associating each output fired in a transition with
    # a delay value (so that the delay can depend on the source
    # *and* trigger). For now, we're just going to have a class property,
    # since there's only one output anyway.
    # Right now the value is somewhat arbitrary, as in reality
    # we'd choose a value that closely matches the real world as seen
    # through experimentation in analog circuit simulators.
    firing_delay = 5.0

    # Finally, an SFQ cell must define how many JJs it uses, for
    # area and power usage estimation purposes. Like firing delay, this number
    # often comes from empirical results/paper findings (based on how
    # many JJs the analog designer needed to create their design), but
    # a fine estimate for this is 15.
    jjs = 15

# Whew, we're done with the definition!
# Hopefully it makes sense. In the next tutorial, we'll go about
# instantiating it, adding it to the circuit, and simulating it.

# Go to `tutorial2.py`...
