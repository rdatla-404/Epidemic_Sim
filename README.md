# Outbreak Tracker

A world map where you pick where an outbreak starts, pick a "disease"
(two realistic ones, four fiction-inspired ones), and watch it spread
day by day across 45 real cities connected by a simplified land + air
travel network. Also includes a separate global compartmental model
(SIR/SEIR, no geography) for quick R0 / herd immunity intuition.

Two model types, two ways to run it -- see below.

## Quickstart

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

venv\Scripts\python.exe -m streamlit run app.py     # the website
venv\Scripts\python.exe main.py                     # or the terminal version
venv\Scripts\python.exe -m pytest                    # run the tests
```

## What's what

| | |
|---|---|
| `app.py` | The website. `streamlit run app.py` opens it in your browser. Real world map (Plotly, actual country borders), click-free origin picker, play/step/reset, vaccination and lockdown sliders. |
| `main.py` | Same simulations, plain terminal output, no Streamlit required. |
| `src/compartmental_model.py` | Global SIR/SEIR ODE model -- one population, no map. |
| `src/network_model.py` | The map model -- real cities on a travel graph, each with its own S/E/I/R state. |
| `src/world_data.py` | City coordinates, the travel-network builder, and the six disease presets. |
| `tests/` | 11 pytest tests covering both models, including a regression test for a real mass-conservation bug found during development. |

Full breakdown of the folder structure and design decisions in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## The six classes, in one line each

- `Region` -- one city. Tracks its own population split into
  Susceptible / Exposed / Infected / Removed.
- `Connection` -- a travel link between two regions (land or air).
- `Disease` -- the parameters that define an outbreak.
- `Simulation` -- owns all regions + connections + one disease, knows
  how to advance the whole world by one day (`.step()`), and supports
  vaccination + lockdown interventions.
- `CompartmentalModel` -- the global, no-geography SIR/SEIR version.
- `CompartmentalResult` -- plain container for what `.run()` returns.

Every one is a `class` keyword, an `__init__` that sets `self.something`,
and methods that read or change that state. No inheritance, no design
patterns.

## How the "realism of spread" works

The biggest lever in the network model is `Disease.incubation_days`
combined with `Disease.mobility_during_incubation`:

- People who are **Exposed** (infected but not yet showing symptoms)
  still look completely normal, so they travel mostly through **air**
  connections.
- People who are **Infected** (visibly sick, or "turned") only spread
  through **land** connections, much more slowly.

That's why the two realistic airborne presets reach dozens of cities
within a couple weeks, while the fast-onset fictional presets (turning
measured in minutes) barely leave their city of origin -- even though
they're devastating once they arrive. That contrast falls out of the
same simulation math for every preset; nothing is hardcoded per-preset
beyond the numbers themselves.

## About the fiction-inspired presets

Four presets are labeled "inspired by" a well-known style of outbreak
fiction. They don't reproduce any character, dialogue, or plot -- they're
epidemiological parameter sets tuned to match the general spread pattern
each style is known for. The underlying simulation is identical math to
the two realistic disease presets.

## What this does not model

Simplified teaching tool, not a predictive one. Real travel networks,
population density, quarantine measures, and seasonal effects aren't
represented. 45 cities and a hub-and-spoke air network is a rough
approximation of global connectivity, not a precise one.
