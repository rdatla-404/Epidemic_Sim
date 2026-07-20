# Architecture

## Folder layout

```
outbreak-tracker/
├── .devcontainer/      VS Code container config (optional convenience)
├── .streamlit/         Streamlit theme config
├── data/               reserved for exported run data (empty for now)
├── docs/                this file
├── logs/                reserved for run logs (empty for now)
├── scripts/             small helper scripts (run_tests.sh)
├── src/                 all model logic -- the actual OOP core
│   ├── compartmental_model.py
│   ├── network_model.py
│   └── world_data.py
├── tests/                pytest suite, one file per model
├── app.py                the website (Streamlit)
├── main.py               plain terminal entry point
├── requirements.txt
├── LICENSE
└── README.md
```

`data/` and `logs/` are genuinely empty right now -- they're here
because the project is shaped to grow into them (e.g. an "export this
run to CSV" button would write into `data/`), not because they already
hold something.

## Two models, one shared shape

**`src/compartmental_model.py`** -- `CompartmentalModel` / `CompartmentalResult`.
One global population, no geography, solved as an ODE with RK4. Answers
"what does transmission look like in aggregate" (R0, herd immunity
threshold, how incubation length reshapes the curve). Cannot represent
*where* an outbreak is.

**`src/network_model.py`** -- `Region` / `Connection` / `Disease` /
`Simulation`. Real cities connected by a travel graph, each running its
own local dynamics and exchanging exposure with neighbors along
`Connection` edges. Each `Region` is a discrete interacting unit on a
graph -- that's the "agent-based / network" layer, with **regions**
(not individual people) as the agents. This is the model that drives
the map.

Both files are pure logic: no `import streamlit`, no `print()` calls
except where explicitly building CLI output in `main.py`. Neither file
knows anything about how its results get displayed.

## Two front ends, one shared engine

**`app.py`** -- the website. Run with `streamlit run app.py`. Builds a
Plotly map (real country borders, Plotly's own built-in geography data)
from whatever `Simulation` currently lives in `st.session_state`. Every
number displayed comes from calling a method already defined in `src/`
-- this file never recomputes any epidemiological math itself.

**`main.py`** -- a plain terminal entry point for anyone who doesn't
want to install Streamlit. Same rule: it only builds objects from `src/`
and prints their state.

Streamlit apps are conventionally written as a script that re-runs
top-to-bottom on every interaction, not as a deep class hierarchy --
that's normal for Streamlit, not a shortcut taken here. The actual OOP
(the interesting part) lives entirely in `src/`.

## Why the network model isn't a "true" per-agent ABM

An earlier version of this project (see conversation history, if you
have it) included a genuine per-*person* stochastic agent-based model --
individual `Agent` objects on a contact graph, each with their own state,
simulated one person at a time. `network_model.py` here is different: it
treats each *region* as the unit that has state (S/E/I/R counts), not
each person. That's a **metapopulation** model, a real and commonly-used
category of epidemic model, but it's worth being precise about the
distinction rather than calling it a per-agent simulation it isn't.
Regions are the "agents" here; people within a region are handled in
aggregate (the same S/E/I/R math as the compartmental model, just run
once per region and coupled to its neighbors).

## The mass-conservation fix (worth knowing about)

`Simulation.step()` caps `e_to_i` and `i_to_removed` at whatever is
actually sitting in the `E` and `I` buckets that day. Without that cap,
any disease with `incubation_days` or `infectious_days` under 1 (true
for several of the fiction-inspired presets, where "incubation" is
minutes) produces a daily transition rate greater than 1 -- which tries
to move more people out of a bucket than it contains. That's not a
rounding error; it silently invents population, and it compounds fast
once regions start exchanging inflated numbers with each other. A test
in `tests/test_network_model.py` guards against this regressing.

## Fiction-inspired presets

Four of the six disease presets in `world_data.py` are labeled
"inspired by" a well-known style of outbreak fiction. They reproduce no
character, dialogue, or plot -- they're epidemiological parameter sets
(transmission type, incubation length, how far people travel before
symptoms show) tuned to match the general spread pattern each style is
known for. The simulation math is identical to the two realistic
disease presets; only the numbers differ.
