"""
tests/test_compartmental_model.py

Run with: pytest  (from the project root)

Each test checks a specific claim about model behavior, not just that
the code runs.
"""

from src.compartmental_model import CompartmentalModel


def test_r0_below_one_dies_out():
    model = CompartmentalModel(model_type="sir", beta=0.09, gamma=0.1)
    result = model.run(days=200)
    assert model.r0() < 1
    assert result.final_attack_rate < 0.05


def test_herd_immunity_threshold_matches_formula():
    model = CompartmentalModel(beta=0.25, gamma=0.1)  # R0 = 2.5
    assert abs(model.herd_immunity_threshold() - 0.6) < 1e-9

    contained = CompartmentalModel(beta=0.08, gamma=0.1)  # R0 = 0.8
    assert contained.herd_immunity_threshold() == 0.0


def test_vaccination_past_herd_immunity_collapses_epidemic():
    model = CompartmentalModel(beta=0.25, gamma=0.1)  # threshold = 60%
    below = model.run(days=300, vaccinated_frac=0.4)
    above = model.run(days=300, vaccinated_frac=0.65)
    assert above.final_attack_rate < below.final_attack_rate
    assert above.final_attack_rate < 0.05


def test_seir_delays_and_flattens_peak_vs_sir():
    sir = CompartmentalModel(model_type="sir", beta=0.4, gamma=0.1).run(days=200)
    seir = CompartmentalModel(model_type="seir", beta=0.4, gamma=0.1, sigma=1/14).run(days=200)
    assert seir.peak_day > sir.peak_day
    assert seir.peak_infected < sir.peak_infected


def test_mass_conserved():
    model = CompartmentalModel(model_type="seir", beta=0.3, gamma=0.1, sigma=0.2)
    result = model.run(days=200)
    for i in range(len(result.t)):
        total = result.S[i] + result.E[i] + result.I[i] + result.R[i]
        assert abs(total - 1.0) < 1e-6
