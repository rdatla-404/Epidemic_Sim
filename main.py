"""
main.py

A plain terminal entry point -- for anyone who wants to run a
simulation without installing Streamlit at all. Prints a day-by-day
summary to the console. This exists alongside app.py the same way
main.py/app.py exist as separate entry points in most real Python
projects: app.py is the website, main.py is "just run it from a
terminal."

No model logic lives here -- it only builds objects from src/ and
prints their state.

Usage:
    python main.py                         (interactive prompts)
    python main.py --model network --origin TYO --preset "Rage Outbreak" --days 30
    python main.py --model compartmental --beta 0.4 --gamma 0.1 --days 200
"""

import argparse

from src.compartmental_model import CompartmentalModel
from src.network_model import Simulation
from src.world_data import build_fresh_world, build_disease_presets


def run_network(args):
    presets = build_disease_presets()
    if args.preset:
        disease = next((d for d in presets if d.name.lower() == args.preset.lower()), None)
        if disease is None:
            print("Unknown preset. Choices: " + ", ".join(d.name for d in presets))
            return
    else:
        print("Available presets:")
        for i, d in enumerate(presets):
            print(f"  {i}: {d.name}")
        disease = presets[int(input("Pick a number: ").strip() or "0")]

    regions, connections = build_fresh_world()

    if args.origin:
        origin_id = args.origin.upper()
    else:
        print("\nSample region ids: NYC, LON, TYO, SAO, JNB, DEL, SYD ...")
        origin_id = input("Origin region id: ").strip().upper()

    days = args.days or int(input("Days to simulate [30]: ").strip() or "30")

    sim = Simulation(
        regions, connections, disease,
        vaccinated_frac=args.vaccinated_frac,
        lockdown_day=args.lockdown_day,
        lockdown_strength=args.lockdown_strength,
    )
    sim.seed_outbreak(origin_id, 5)

    print(f"\nRunning '{disease.name}' from {sim.get_region(origin_id).name} for {days} days...\n")
    for _ in range(days):
        sim.step()

    totals = sim.latest_totals()
    print(f"Day {sim.day} results:")
    print(f"  Susceptible:              {round(totals['S']):,}")
    print(f"  Exposed:                  {round(totals['E']):,}")
    print(f"  {disease.infected_label + ':':<26}{round(totals['I']):,}")
    print(f"  {disease.final_state_label + ':':<26}{round(totals['R']):,}")
    print(f"  Regions reached:          {totals['regionsReached']} / {len(regions)}")
    print("\nRecent events:")
    for line in sim.event_log[-10:]:
        print("  " + line)


def run_compartmental(args):
    model_type = args.compartmental_type or "sir"
    sigma = args.sigma
    if model_type == "seir" and sigma is None:
        sigma = 1 / float(input("Incubation period in days: ").strip() or "5")

    beta = args.beta if args.beta is not None else float(input("beta [0.4]: ").strip() or "0.4")
    gamma = args.gamma if args.gamma is not None else float(input("gamma [0.1]: ").strip() or "0.1")
    days = args.days or int(input("Days [200]: ").strip() or "200")

    model = CompartmentalModel(model_type=model_type, beta=beta, gamma=gamma, sigma=sigma)
    result = model.run(days=days, vaccinated_frac=args.vaccinated_frac)

    print(f"\nR0:                      {model.r0():.2f}")
    print(f"Herd immunity threshold: {model.herd_immunity_threshold():.1%}")
    print(f"Peak infected:           {result.peak_infected:.1%} on day {result.peak_day:.0f}")
    print(f"Final attack rate:       {result.final_attack_rate:.1%}")


def build_parser():
    p = argparse.ArgumentParser(description="Run an outbreak simulation from the terminal.")
    p.add_argument("--model", choices=["network", "compartmental"], default=None)
    p.add_argument("--preset", type=str, default=None, help="[network] disease preset name")
    p.add_argument("--origin", type=str, default=None, help="[network] origin region id, e.g. NYC")
    p.add_argument("--vaccinated-frac", type=float, default=0.0)
    p.add_argument("--lockdown-day", type=int, default=None)
    p.add_argument("--lockdown-strength", type=float, default=0.0)
    p.add_argument("--compartmental-type", choices=["sir", "seir"], default=None)
    p.add_argument("--beta", type=float, default=None)
    p.add_argument("--gamma", type=float, default=None)
    p.add_argument("--sigma", type=float, default=None)
    p.add_argument("--days", type=int, default=None)
    return p


def main():
    args = build_parser().parse_args()
    model_choice = args.model or input("Model type (network/compartmental) [network]: ").strip() or "network"
    if model_choice == "network":
        run_network(args)
    else:
        run_compartmental(args)


if __name__ == "__main__":
    main()
