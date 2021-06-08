
def inspect(wire, name):
    ''' Observe a wire in the simulation, labelling it 'name' in the plotted waveform

    :param Wire wire: wire to observe
    :param str name: label for the wire in the simulation
    '''
    wire.observed_as = name
