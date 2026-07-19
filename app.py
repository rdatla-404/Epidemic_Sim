"""
app.py

The website. Run it with:
    streamlit run app.py

This file draws things and reads button clicks -- it never recomputes
any outbreak math itself. Every number on the page comes from calling
methods that already exist on the classes in src/compartmental_model.py
and src/network_model.py.

The world map uses Plotly's built-in geography (real country borders,
not hand-drawn shapes) -- Plotly ships its own basemap data, so this
needs no additional map files or API keys.

Streamlit apps are usually written as a script that runs top-to-bottom
on every interaction, not as a big class hierarchy -- that's normal for
Streamlit, not a shortcut. The OOP still lives in src/, same as always;
this file is the "wiring," like cli.py or app.js were in earlier
versions of this project.
"""

import streamlit as st
import plotly.graph_objects as go

from src.compartmental_model import CompartmentalModel
from src.network_model import Simulation
from src.world_data import build_fresh_world, build_disease_presets


st.set_page_config(page_title="Outbreak Tracker", layout="wide", page_icon="\U0001F310")


# --------------------------------------------------------------------------
# Styling -- dark "control room" theme, matching earlier versions of this project
# --------------------------------------------------------------------------

st.markdown("""
<style>
    .stApp { background-color: #05080c; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3, p, label, .stMarkdown { color: #d9e6ec !important; }
    [data-testid="stSidebar"] { background-color: #0c131a; }
    .stat-box {
        background: #111a22; border: 1px solid #1e2a34; border-radius: 6px;
        padding: 10px 14px; margin-bottom: 8px;
    }
    .stat-value { font-family: monospace; font-size: 22px; font-weight: 700; }
    .stat-label { font-size: 11px; color: #6c8494; text-transform: uppercase; letter-spacing: 0.05em; }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Session state -- Streamlit re-runs this whole script on every
# interaction, so anything that needs to persist between reruns (the
# running Simulation, which day we're on, etc) has to live in
# st.session_state instead of a plain variable.
# --------------------------------------------------------------------------

if "sim" not in st.session_state:
    st.session_state.sim = None
if "origin_id" not in st.session_state:
    st.session_state.origin_id = None
if "playing" not in st.session_state:
    st.session_state.playing = False

PRESETS = build_disease_presets()


def start_network_simulation(disease, origin_id, vaccinated_frac, lockdown_day, lockdown_strength):
    regions, connections = build_fresh_world()
    sim = Simulation(
        regions, connections, disease,
        vaccinated_frac=vaccinated_frac,
        lockdown_day=lockdown_day if lockdown_day > 0 else None,
        lockdown_strength=lockdown_strength,
    )
    sim.seed_outbreak(origin_id, 5)
    st.session_state.sim = sim
    st.session_state.origin_id = origin_id


# --------------------------------------------------------------------------
# Sidebar controls
# --------------------------------------------------------------------------

st.sidebar.title("\U0001F9A0 Outbreak Tracker")
model_choice = st.sidebar.radio("Model type", ["Network (map)", "Compartmental (global, no map)"])

st.sidebar.markdown("---")
preset_names = [d.name for d in PRESETS]
preset_name = st.sidebar.selectbox("Scenario", preset_names)
disease = next(d for d in PRESETS if d.name == preset_name)
st.sidebar.caption(disease.description)

incubation_display = (
    f"{round(disease.incubation_days * 24 * 60)} min"
    if disease.incubation_days < 1 else f"{disease.incubation_days} days"
)
st.sidebar.markdown(
    f"**Transmission:** {disease.transmission_mode}  \n"
    f"**Incubation:** {incubation_display}  \n"
    f"**Lethality:** {disease.lethality * 100:.1f}%"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Interventions")
vaccinated_frac = st.sidebar.slider("Vaccinated before outbreak (%)", 0, 90, 0) / 100
lockdown_enabled = st.sidebar.checkbox("Enable lockdown")
lockdown_day = st.sidebar.slider("Lockdown starts on day", 1, 60, 14) if lockdown_enabled else 0
lockdown_strength = st.sidebar.slider("Lockdown travel reduction (%)", 0, 100, 70) / 100 if lockdown_enabled else 0.0


# --------------------------------------------------------------------------
# NETWORK MODEL VIEW
# --------------------------------------------------------------------------

if model_choice == "Network (map)":
    st.sidebar.markdown("---")
    st.sidebar.subheader("Origin")
    regions_for_list, _ = build_fresh_world()
    region_options = {r.name: r.id for r in sorted(regions_for_list, key=lambda r: r.name)}
    origin_name = st.sidebar.selectbox("Where does it start?", list(region_options.keys()))
    origin_id = region_options[origin_name]

    col_start, col_reset = st.sidebar.columns(2)
    if col_start.button("Start / Restart", width="stretch"):
        start_network_simulation(disease, origin_id, vaccinated_frac, lockdown_day, lockdown_strength)
        st.session_state.playing = False
    if col_reset.button("Reset", width="stretch"):
        st.session_state.sim = None
        st.session_state.playing = False

    sim = st.session_state.sim

    col_step, col_play = st.sidebar.columns(2)
    step_clicked = col_step.button("Step +1 day", disabled=sim is None, width="stretch")
    play_label = "Pause" if st.session_state.playing else "Play"
    if col_play.button(play_label, disabled=sim is None, width="stretch"):
        st.session_state.playing = not st.session_state.playing

    if sim is not None and step_clicked:
        sim.step()

    if sim is not None and st.session_state.playing:
        sim.step()
        if sim.is_over():
            st.session_state.playing = False

    st.title("World Outbreak Map")

    if sim is None:
        st.info("Pick an origin city in the sidebar, then click **Start / Restart**.")
    else:
        totals = sim.latest_totals()

        stat_cols = st.columns(4)
        stat_cols[0].markdown(f'<div class="stat-box"><div class="stat-value" style="color:#6f93a8">{round(totals["S"]):,}</div><div class="stat-label">Susceptible</div></div>', unsafe_allow_html=True)
        stat_cols[1].markdown(f'<div class="stat-box"><div class="stat-value" style="color:#e8b64a">{round(totals["E"]):,}</div><div class="stat-label">Exposed</div></div>', unsafe_allow_html=True)
        stat_cols[2].markdown(f'<div class="stat-box"><div class="stat-value" style="color:#e0483c">{round(totals["I"]):,}</div><div class="stat-label">{disease.infected_label}</div></div>', unsafe_allow_html=True)
        stat_cols[3].markdown(f'<div class="stat-box"><div class="stat-value" style="color:#46c9a0">{round(totals["R"]):,}</div><div class="stat-label">{disease.final_state_label}</div></div>', unsafe_allow_html=True)

        st.caption(f"Day {sim.day}  \u2014  {totals['regionsReached']} / {len(sim.regions)} regions reached")

        # --- map ---
        fig = go.Figure()

        # connections, drawn first so they sit behind the region markers
        for conn in sim.connections:
            fig.add_trace(go.Scattergeo(
                lon=[conn.region_a.lon, conn.region_b.lon],
                lat=[conn.region_a.lat, conn.region_b.lat],
                mode="lines",
                line=dict(
                    width=0.5 if conn.type == "air" else 0.8,
                    color="rgba(232,182,74,0.10)" if conn.type == "air" else "rgba(108,132,148,0.18)",
                ),
                hoverinfo="skip",
                showlegend=False,
            ))

        # region dots, colored by whichever compartment currently
        # dominates that region's population
        lats, lons, colors, sizes, texts = [], [], [], [], []
        for r in sim.regions:
            N = r.population
            fractions = {"S": r.S / N, "E": r.E / N, "I": r.I / N, "R": r.R / N} if N > 0 else {"S": 1, "E": 0, "I": 0, "R": 0}
            dominant = max(fractions, key=fractions.get)
            color = {"S": "#3a5566", "E": "#e8b64a", "I": "#e0483c", "R": "#46c9a0"}[dominant]

            lats.append(r.lat)
            lons.append(r.lon)
            colors.append(color)
            sizes.append(6 + (r.total_affected() / N if N > 0 else 0) * 22 + N ** 0.5)
            texts.append(
                f"{r.name}<br>S: {round(r.S):,}  E: {round(r.E):,}  "
                f"{disease.infected_label}: {round(r.I):,}  {disease.final_state_label}: {round(r.R):,}"
            )

        fig.add_trace(go.Scattergeo(
            lon=lons, lat=lats, mode="markers",
            marker=dict(size=sizes, color=colors, opacity=0.9, line=dict(width=0)),
            text=texts, hoverinfo="text", showlegend=False,
        ))

        # highlight the origin
        origin_region = sim.get_region(st.session_state.origin_id)
        if origin_region:
            fig.add_trace(go.Scattergeo(
                lon=[origin_region.lon], lat=[origin_region.lat], mode="markers",
                marker=dict(size=16, color="rgba(0,0,0,0)", line=dict(width=2, color="white")),
                hoverinfo="skip", showlegend=False,
            ))

        fig.update_geos(
            projection_type="natural earth",
            showland=True, landcolor="#16232c",
            showocean=True, oceancolor="#0f1922",
            showcountries=True, countrycolor="#223040",
            showcoastlines=True, coastlinecolor="#2c3d4a",
            bgcolor="#05080c",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), height=560,
            paper_bgcolor="#05080c", plot_bgcolor="#05080c",
        )
        st.plotly_chart(fig, width="stretch")

        # --- chart of totals over time ---
        st.subheader("Spread over time")
        chart_fig = go.Figure()
        days = [h["day"] for h in sim.history]
        chart_fig.add_trace(go.Scatter(x=days, y=[h["E"] for h in sim.history], name="Exposed", line=dict(color="#e8b64a")))
        chart_fig.add_trace(go.Scatter(x=days, y=[h["I"] for h in sim.history], name=disease.infected_label, line=dict(color="#e0483c")))
        chart_fig.add_trace(go.Scatter(x=days, y=[h["R"] for h in sim.history], name=disease.final_state_label, line=dict(color="#46c9a0")))
        chart_fig.update_layout(
            height=260, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="#0c131a", plot_bgcolor="#0c131a",
            font=dict(color="#d9e6ec"),
            xaxis=dict(gridcolor="#1e2a34", title="Day"),
            yaxis=dict(gridcolor="#1e2a34", title="People"),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(chart_fig, width="stretch")

        # --- event log ---
        with st.expander("Event log", expanded=False):
            for line in reversed(sim.event_log):
                st.text(line)

        if st.session_state.playing:
            st.rerun()


# --------------------------------------------------------------------------
# COMPARTMENTAL MODEL VIEW
# --------------------------------------------------------------------------

else:
    st.title("Global Compartmental Model")
    st.caption("One population, no geography -- for quick R0 / herd immunity intuition, not for watching a map.")

    model_type = "seir" if disease.incubation_days >= 0.5 else "sir"
    if model_type == "sir":
        st.info("This scenario's incubation window is very short, so it's shown as an SIR model (no separate Exposed stage).")

    model = CompartmentalModel(
        model_type=model_type, beta=disease.beta, gamma=1 / disease.infectious_days if disease.infectious_days < 900 else 0.1,
        sigma=1 / disease.incubation_days if model_type == "seir" else None,
    )
    result = model.run(days=200, vaccinated_frac=vaccinated_frac)

    stat_cols = st.columns(4)
    stat_cols[0].markdown(f'<div class="stat-box"><div class="stat-value">{model.r0():.2f}</div><div class="stat-label">R0</div></div>', unsafe_allow_html=True)
    stat_cols[1].markdown(f'<div class="stat-box"><div class="stat-value">{model.herd_immunity_threshold():.0%}</div><div class="stat-label">Herd immunity threshold</div></div>', unsafe_allow_html=True)
    stat_cols[2].markdown(f'<div class="stat-box"><div class="stat-value">{result.peak_infected:.1%}</div><div class="stat-label">Peak infected (day {result.peak_day:.0f})</div></div>', unsafe_allow_html=True)
    stat_cols[3].markdown(f'<div class="stat-box"><div class="stat-value">{result.final_attack_rate:.1%}</div><div class="stat-label">Final attack rate</div></div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result.t, y=result.S, name="Susceptible", line=dict(color="#3a5566")))
    if result.E is not None:
        fig.add_trace(go.Scatter(x=result.t, y=result.E, name="Exposed", line=dict(color="#e8b64a")))
    fig.add_trace(go.Scatter(x=result.t, y=result.I, name=disease.infected_label, line=dict(color="#e0483c")))
    fig.add_trace(go.Scatter(x=result.t, y=result.R, name=disease.final_state_label, line=dict(color="#46c9a0")))
    fig.update_layout(
        height=420, margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="#0c131a", plot_bgcolor="#0c131a",
        font=dict(color="#d9e6ec"),
        xaxis=dict(gridcolor="#1e2a34", title="Day"),
        yaxis=dict(gridcolor="#1e2a34", title="Fraction of population"),
        legend=dict(orientation="h"),
    )
    st.plotly_chart(fig, width="stretch")


st.markdown("---")
st.caption(
    "Educational simulation only. Fictional scenario names describe generic transmission "
    "styles (contact type, incubation length, mobility) -- not any film's plot, characters, or dialogue."
)
