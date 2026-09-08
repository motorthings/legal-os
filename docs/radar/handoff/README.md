# Streams visualization — handoff

## What's here

- **PROMPT.md** — paste this into Claude Code. It carries the reasoning, the 10 requirements, and page-layout notes.
- **streams-chart.js** — dependency-free reference implementation (ES module). Layout math + render + hover tracing. Exports `STREAMS`, `PREDICTIONS`, `layout()`, `renderStreamsChart(mount, opts)`.
- **streams-chart.html** — standalone page that renders it. Open this first: it is the visual target.
- **target.png** — screenshot of the finished chart, in case you want it in the prompt as an image.

## Run it

ES modules need a server, not `file://`:

    cd handoff && python3 -m http.server 8000
    # open http://localhost:8000/streams-chart.html

## The one-line rationale

Items and a 0-10 queue score can't chain through one flow honestly. So: items stay a flow on the left, queue becomes a ranked bar on the right, and corroboration is carried by the bar's internal composition - one colour means one stream agrees, four colours means the engine is sure.
