"""
tests/test_network_model.py

Run with: pytest  (from the project root)

Stochastic behavior doesn't apply here (this model is deterministic
given its inputs, unlike a true per-agent ABM), so single runs are
sufficient -- but each test still checks a specific claim, not just that
the code runs.
"""

from src.network_model import Simulation
from src.world_data import build_fresh_world, build_disease_presets


def get_disease(name):
    return next(d for d in build_disease_presets() if d.name == name)


def test_world_data_builds_correctly():
    regions, connections = build_fresh_world()
    assert len(regions) == 45
    assert len(connections) == 180
    assert len([c for c in connections if c.type == "air"]) == 122
    assert len([c for c in connections if c.type == "land"]) == 90


def test_airborne_disease_reaches_far_more_regions_than_fast_onset_disease():
    # This is the core "realism of spread types" claim: long incubation +
    # high mobility during incubation (airborne) reaches many regions;
    # near-instant onset (Rage Outbreak) stays almost entirely local.
    regions_air, conns_air = build_fresh_world()
    sim_air = Simulation(regions_air, conns_air, get_disease("Severe Airborne Pandemic"))
    sim_air.seed_outbreak("NYC", 5)
    for _ in range(14):
        sim_air.step()

    regions_rage, conns_rage = build_fresh_world()
    sim_rage = Simulation(regions_rage, conns_rage, get_disease("Rage Outbreak"))
    sim_rage.seed_outbreak("NYC", 5)
    for _ in range(14):
        sim_rage.step()

    assert sim_air.latest_totals()["regionsReached"] > sim_rage.latest_totals()["regionsReached"]


def test_mass_conservation_holds_for_every_preset_including_fast_onset():
    # The exact bug this guards against: a daily transition rate faster
    # than 1 (true for several fast-onset presets, e.g. incubation_days
    # under 1) tries to move more people than a bucket actually contains,
    # which -- without the cap in Simulation.step() -- silently invents
    # population out of nowhere. This test would have caught that bug.
    for disease in build_disease_presets():
        regions, connections = build_fresh_world()
        sim = Simulation(regions, connections, disease)
        sim.seed_outbreak("TYO", 5)
        for _ in range(90):
            sim.step()
        for region in regions:
            total = region.S + region.E + region.I + region.R
            over_pct = (total - region.population) / region.population
            assert over_pct < 0.01, f"{disease.name} / {region.name}: {over_pct:.4%} over population"
            assert region.S >= -0.001
            assert region.E >= -0.001
            assert region.I >= -0.001
            assert region.R >= -0.001


def test_vaccination_reduces_final_spread():
    disease = get_disease("Severe Airborne Pandemic")

    regions_a, conns_a = build_fresh_world()
    sim_no_vacc = Simulation(regions_a, conns_a, disease, vaccinated_frac=0.0)
    sim_no_vacc.seed_outbreak("NYC", 5)

    regions_b, conns_b = build_fresh_world()
    sim_vacc = Simulation(regions_b, conns_b, disease, vaccinated_frac=0.7)
    sim_vacc.seed_outbreak("NYC", 5)

    for _ in range(60):
        sim_no_vacc.step()
        sim_vacc.step()

    no_vacc_affected = sim_no_vacc.latest_totals()["E"] + sim_no_vacc.latest_totals()["I"] + sim_no_vacc.latest_totals()["R"]
    vacc_affected = sim_vacc.latest_totals()["E"] + sim_vacc.latest_totals()["I"] + sim_vacc.latest_totals()["R"]
    assert vacc_affected < no_vacc_affected


def test_lockdown_reduces_regions_reached():
    disease = get_disease("Severe Airborne Pandemic")

    regions_a, conns_a = build_fresh_world()
    sim_no_lockdown = Simulation(regions_a, conns_a, disease)
    sim_no_lockdown.seed_outbreak("NYC", 5)

    regions_b, conns_b = build_fresh_world()
    sim_lockdown = Simulation(regions_b, conns_b, disease, lockdown_day=3, lockdown_strength=0.9)
    sim_lockdown.seed_outbreak("NYC", 5)

    for _ in range(20):
        sim_no_lockdown.step()
        sim_lockdown.step()

    assert sim_lockdown.latest_totals()["regionsReached"] <= sim_no_lockdown.latest_totals()["regionsReached"]


def test_seed_outbreak_marks_region_as_ever_infected():
    regions, connections = build_fresh_world()
    sim = Simulation(regions, connections, get_disease("Seasonal Flu-like"))
    sim.seed_outbreak("LON", 5)
    london = sim.get_region("LON")
    assert london.ever_infected is True
    assert london.I == 5
