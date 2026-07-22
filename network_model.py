"""
src/network_model.py

The geographic half of this project: real cities, connected by a
simplified land + air travel network, each running its own local
SEIR-style dynamics and exchanging exposure with its neighbors. Each
Region is a discrete interacting unit connected to others via a graph --
that's the "agent-based / network model" layer, with regions (not
individual people) as the agents. See compartmental_model.py for the
other half: one global population, no geography.

Plain classes only: __init__ plus methods, no dataclasses, no advanced
typing.

Layout:
  1. Region      -- one city, tracks S / E / I / R for its own population
  2. Connection   -- a travel link between two regions (land or air)
  3. Disease      -- the parameters that define an outbreak
  4. Simulation   -- owns the whole world, advances it day by day,
                     supports vaccination and a lockdown intervention
"""


class Region:
    def __init__(self, region_id, name, lat, lon, population):
        self.id = region_id
        self.name = name
        self.lat = lat
        self.lon = lon
        self.population = population

        self.S = population
        self.E = 0.0
        self.I = 0.0
        self.R = 0.0

        self.ever_infected = False

    def total_affected(self):
        return self.E + self.I + self.R

    def infected_fraction(self):
        return self.I / self.population if self.population > 0 else 0.0


class Connection:
    def __init__(self, region_a, region_b, conn_type, weight):
        self.region_a = region_a
        self.region_b = region_b
        self.type = conn_type  # "land" or "air"
        self.weight = weight


class Disease:
    def __init__(self, name, description, transmission_mode, beta,
                 incubation_days, infectious_days, lethality,
                 mobility_during_incubation, final_state_label="Recovered",
                 infected_label="Infected"):
        self.name = name
        self.description = description
        self.transmission_mode = transmission_mode
        self.beta = beta
        self.incubation_days = incubation_days
        self.infectious_days = infectious_days
        self.lethality = lethality
        self.mobility_during_incubation = mobility_during_incubation
        self.final_state_label = final_state_label
        self.infected_label = infected_label


class Simulation:
    """
    vaccinated_frac:    fraction of EVERY region's population moved
                        straight to Removed before day 0 (a simple,
                        uniform vaccination campaign -- not targeted at
                        specific cities)
    lockdown_day:       day travel restrictions kick in (None = no lockdown)
    lockdown_strength:  0 to 1, fraction of cross-region travel suppressed
                        once lockdown is active
    """

    def __init__(self, regions, connections, disease,
                 vaccinated_frac=0.0, lockdown_day=None, lockdown_strength=0.0):
        self.regions = regions
        self.connections = connections
        self.disease = disease
        self.vaccinated_frac = vaccinated_frac
        self.lockdown_day = lockdown_day
        self.lockdown_strength = lockdown_strength
        self.day = 0
        self.history = []
        self.event_log = []

        if vaccinated_frac > 0:
            self._apply_vaccination()

        self._record_history()

    def _apply_vaccination(self):
        for region in self.regions:
            moved = region.S * self.vaccinated_frac
            region.S -= moved
            region.R += moved
        self.event_log.append(
            "Day 0: " + str(round(self.vaccinated_frac * 100)) + "% of every region vaccinated before the outbreak begins."
        )

    def get_region(self, region_id):
        for region in self.regions:
            if region.id == region_id:
                return region
        return None

    def seed_outbreak(self, region_id, initial_cases=5):
        region = self.get_region(region_id)
        if region is None:
            return
        cases = min(initial_cases, region.S)
        region.S -= cases
        region.I += cases
        region.ever_infected = True
        self.event_log.append("Day 0: Outbreak begins in " + region.name + ".")

    def _travel_multiplier(self):
        """1.0 normally; drops once lockdown starts, per lockdown_strength."""
        if self.lockdown_day is not None and self.day >= self.lockdown_day:
            return 1 - self.lockdown_strength
        return 1.0

    def step(self):
        self.day += 1
        d = self.disease

        if self.lockdown_day is not None and self.day == self.lockdown_day:
            self.event_log.append(
                "Day " + str(self.day) + ": lockdown begins (" +
                str(round(self.lockdown_strength * 100)) + "% travel reduction)."
            )

        # --- Step 1: local spread + disease progression within each region ---
        local_changes = []
        for region in self.regions:
            N = region.population
            if N <= 0:
                local_changes.append((region, 0.0, 0.0, 0.0, 0.0))
                continue

            newly_exposed = min(region.S, (d.beta * region.S * region.I) / N)
            incubation_rate = 1 / d.incubation_days
            recovery_rate = 1 / d.infectious_days

            # Cap each flow at what's actually in the source bucket --
            # without this, a disease with incubation/infectious_days
            # under 1 day produces a daily rate greater than 1, which
            # would try to move more people than the bucket contains
            # and silently invent population. (This is the exact bug
            # that showed up during testing before this cap was added.)
            e_to_i = min(region.E, region.E * incubation_rate)
            i_to_removed = min(region.I, region.I * recovery_rate)

            d_s = -newly_exposed
            d_e = newly_exposed - e_to_i
            d_i = e_to_i - i_to_removed
            d_r = i_to_removed
            local_changes.append((region, d_s, d_e, d_i, d_r))

        # --- Step 2: cross-region spread along connections ---
        # EXPOSED travelers move mostly through AIR connections (still
        # look healthy). INFECTED travelers only move through LAND
        # connections, much more slowly. Lockdown scales both down.
        travel_mult = self._travel_multiplier()
        imported_exposure = {}

        def add_import(region_id, amount):
            imported_exposure[region_id] = imported_exposure.get(region_id, 0.0) + amount

        for conn in self.connections:
            a, b = conn.region_a, conn.region_b
            weight = conn.weight * travel_mult
            if conn.type == "air":
                add_import(b.id, a.E * d.mobility_during_incubation * weight)
                add_import(a.id, b.E * d.mobility_during_incubation * weight)
            else:
                add_import(b.id, a.I * weight * 0.5 + a.E * weight * 0.3)
                add_import(a.id, b.I * weight * 0.5 + b.E * weight * 0.3)

        # --- Step 3: apply everything ---
        newly_reached = []
        for region, d_s, d_e, d_i, d_r in local_changes:
            was_affected = region.ever_infected

            region.S += d_s
            region.E += d_e
            region.I += d_i
            region.R += d_r

            imported = min(region.S, imported_exposure.get(region.id, 0.0))
            region.S -= imported
            region.E += imported

            region.S = max(0.0, region.S)
            region.E = max(0.0, region.E)
            region.I = max(0.0, region.I)
            region.R = max(0.0, region.R)

            if not was_affected and region.total_affected() > 0.01:
                region.ever_infected = True
                newly_reached.append(region.name)

        for name in newly_reached:
            self.event_log.append("Day " + str(self.day) + ": outbreak reaches " + name + ".")

        self._record_history()

    def _record_history(self):
        total_s = sum(r.S for r in self.regions)
        total_e = sum(r.E for r in self.regions)
        total_i = sum(r.I for r in self.regions)
        total_r = sum(r.R for r in self.regions)
        regions_reached = sum(1 for r in self.regions if r.ever_infected)
        self.history.append({
            "day": self.day, "S": total_s, "E": total_e, "I": total_i, "R": total_r,
            "regionsReached": regions_reached,
        })

    def is_over(self):
        return all(r.E < 0.5 and r.I < 0.5 for r in self.regions)

    def latest_totals(self):
        return self.history[-1]
