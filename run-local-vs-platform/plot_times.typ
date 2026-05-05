#import "@preview/lilaq:0.6.0" as lq

#set page(width: auto, height: auto, margin: 1em)

#let labels = ("EchoSched", "fbd1", "hitori", "ihtc")
#let local-times = (40.6, 73.5, 74.3, 202.3)
#let local-errs  = (6.2, 4.7, 2.8, 45.4)
#let platform-times = (40.2, 73.0, 73.2, 205.7)
#let platform-errs  = (3.0, 1.3, 1.1, 21.8)

#figure(
  lq.diagram(
    width: 10cm,
    height: 6cm,
    title: [Solve Time: Local vs.\ Platform (cp-sat, 8 cores, 3 reps)],
    ylabel: [Solve time (s)],
    xlabel: [Problem],
    legend: (position: (100% + .5em, 0%)),
    xaxis: (
      ticks: labels.enumerate(),
      subticks: none,
    ),

    lq.bar(
      range(labels.len()), local-times,
      offset: -0.2, width: 0.4,
      fill: blue.lighten(30%),
      label: [local],
    ),
    lq.bar(
      range(labels.len()), platform-times,
      offset: 0.2, width: 0.4,
      fill: orange.lighten(30%),
      label: [platform],
    ),
    lq.plot(
      range(labels.len()).map(x => x - 0.2), local-times,
      yerr: local-errs,
      color: black, stroke: none,
    ),
    lq.plot(
      range(labels.len()).map(x => x + 0.2), platform-times,
      yerr: platform-errs,
      color: black, stroke: none,
    ),
  ),
  caption: [
    Mean solve time (cp-sat, 8 cores, 3 repetitions) for the same instances run
    locally in Docker versus on the PSP platform. Error bars span min/max across
    the three repetitions. Instances: EchoSched = EchoSched/14-10-0-2_3; fbd1 = fbd1/FBDk07; hitori = hitori/h14-1; ihtc = ihtc-2024-kletzander/test03.
  ],
)
