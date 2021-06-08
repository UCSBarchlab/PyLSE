import matplotlib.pyplot as plt
import collections


def plot(events_to_plot, until=None, segment_size=5, save=False):
    if until is None:
        until = 0
        for times in events_to_plot.values():
            until = max(max(times) if times else 0, until)
    # There may be other pulses that were created extending a little beyond
    until += 1
    od = collections.OrderedDict(sorted(events_to_plot.items()))
    variables = list(od.keys())
    data = list(od.values())
    _fig, ax = plt.subplots()
    plt.eventplot(data, orientation='horizontal', color='red', linelengths=0.5)
    ax.set_xlabel('Time (ps)')
    ax.set_xlim(-1, until)
    ax.set_xticks([x for x in range(until+1) if (x % segment_size == 0)])
    ax.set_ylabel('Simulation Variables')
    ax.set_ylim(-1, len(variables))
    ax.set_yticks([(i) for i in range(len(variables))])
    ax.set_yticklabels(variables)
    ax.invert_yaxis()
    ax.grid(True)
    plt.subplots_adjust(left=0.15, right=0.92)
    # save the waveform plot if desired
    if save:
        plt.savefig("sim_results.png")
    plt.show()
    return
