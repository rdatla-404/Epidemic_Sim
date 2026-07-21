"""
src/world_data.py

Real-world data used by network_model.py: city coordinates and
populations (public geographic facts, not anyone's creative work), the
function that builds a land + air travel network from them, and the
disease presets. Kept separate from network_model.py so "the data" and
"the simulation engine" are two different files with two different
jobs -- same reasoning as splitting cli.py from the model files earlier
in this project.
"""

import math

from .network_model import Region, Connection, Disease


WORLD_REGIONS_RAW = [
    # id, name, lat, lon, population (millions), continent
    ("NYC", "New York", 40.7, -74.0, 8.4, "NA"),
    ("LAX", "Los Angeles", 34.0, -118.2, 4.0, "NA"),
    ("MEX", "Mexico City", 19.4, -99.1, 9.2, "NA"),
    ("YTO", "Toronto", 43.7, -79.4, 2.9, "NA"),
    ("CHI", "Chicago", 41.9, -87.6, 2.7, "NA"),
    ("YVR", "Vancouver", 49.3, -123.1, 2.6, "NA"),
    ("HNL", "Honolulu", 21.3, -157.8, 1.0, "NA"),

    ("SAO", "Sao Paulo", -23.5, -46.6, 12.3, "SA"),
    ("BUE", "Buenos Aires", -34.6, -58.4, 3.0, "SA"),
    ("BOG", "Bogota", 4.7, -74.1, 7.4, "SA"),
    ("LIM", "Lima", -12.0, -77.0, 9.7, "SA"),
    ("SCL", "Santiago", -33.4, -70.6, 5.6, "SA"),

    ("LON", "London", 51.5, -0.1, 9.0, "EU"),
    ("PAR", "Paris", 48.9, 2.3, 2.1, "EU"),
    ("BER", "Berlin", 52.5, 13.4, 3.7, "EU"),
    ("MAD", "Madrid", 40.4, -3.7, 3.3, "EU"),
    ("ROM", "Rome", 41.9, 12.5, 2.9, "EU"),
    ("MOW", "Moscow", 55.8, 37.6, 12.5, "EU"),
    ("IST", "Istanbul", 41.0, 28.9, 15.5, "EU"),
    ("REY", "Reykjavik", 64.1, -21.9, 0.2, "EU"),

    ("CAI", "Cairo", 30.0, 31.2, 20.9, "AF"),
    ("LOS", "Lagos", 6.5, 3.4, 14.9, "AF"),
    ("NBO", "Nairobi", -1.3, 36.8, 4.4, "AF"),
    ("JNB", "Johannesburg", -26.2, 28.0, 5.6, "AF"),
    ("KIN", "Kinshasa", -4.3, 15.3, 14.3, "AF"),
    ("CAS", "Casablanca", 33.6, -7.6, 3.4, "AF"),

    ("TYO", "Tokyo", 35.7, 139.7, 37.4, "AS"),
    ("BJS", "Beijing", 39.9, 116.4, 21.5, "AS"),
    ("SHA", "Shanghai", 31.2, 121.5, 27.1, "AS"),
    ("DEL", "Delhi", 28.6, 77.2, 30.3, "AS"),
    ("BOM", "Mumbai", 19.1, 72.9, 20.4, "AS"),
    ("SEL", "Seoul", 37.6, 127.0, 9.9, "AS"),
    ("BKK", "Bangkok", 13.8, 100.5, 10.5, "AS"),
    ("JKT", "Jakarta", -6.2, 106.8, 10.6, "AS"),
    ("MNL", "Manila", 14.6, 121.0, 13.9, "AS"),
    ("KHI", "Karachi", 24.9, 67.0, 16.1, "AS"),
    ("DAC", "Dhaka", 23.8, 90.4, 21.0, "AS"),
    ("HKG", "Hong Kong", 22.3, 114.2, 7.5, "AS"),
    ("SIN", "Singapore", 1.35, 103.8, 5.7, "AS"),
    ("DXB", "Dubai", 25.2, 55.3, 3.4, "AS"),
    ("THR", "Tehran", 35.7, 51.4, 9.0, "AS"),
    ("RUH", "Riyadh", 24.7, 46.7, 7.2, "AS"),

    ("SYD", "Sydney", -33.9, 151.2, 5.3, "OC"),
    ("MEL", "Melbourne", -37.8, 144.9, 5.1, "OC"),
    ("AKL", "Auckland", -36.8, 174.8, 1.7, "OC"),
]

AIR_HUB_IDS = [
    "NYC", "LON", "DXB", "TYO", "BJS", "DEL", "SIN",
    "SAO", "JNB", "MOW", "LAX", "PAR", "SYD", "MEX",
]


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometers between two lat/lon points."""
    def to_rad(deg):
        return deg * math.pi / 180

    R = 6371
    d_lat = to_rad(lat2 - lat1)
    d_lon = to_rad(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(d_lon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def build_fresh_world():
    """
    Build a brand-new set of Region objects and Connection objects with dynamic weights.
    """
    regions = [Region(row[0], row[1], row[2], row[3], row[4]) for row in WORLD_REGIONS_RAW]
    by_id = {r.id: r for r in regions}

    connections = []

    # Land connections: each region connects to its 2 nearest neighbors on the same continent
    for row in WORLD_REGIONS_RAW:
        region_id, _, lat, lon, _, continent = row
        region = by_id[region_id]
        others = []
        for other_row in WORLD_REGIONS_RAW:
            other_id, _, o_lat, o_lon, _, o_continent = other_row
            if other_id == region_id or o_continent != continent:
                continue
            distance = haversine_km(lat, lon, o_lat, o_lon)
            others.append((distance, by_id[other_id]))
        others.sort(key=lambda pair: pair[0])
        for distance, neighbor in others[:2]:
            pair_key = frozenset((region.id, neighbor.id))
            if pair_key in seen_land_pairs:
                continue
            seen_land_pairs.add(pair_key)
            weight = max(0.02, min(0.25, 400 / distance))
            connections.append(Connection(region, neighbor, "land", weight))

    # Air connections: scaled dynamically using an epidemiological Gravity Model
    hubs = [by_id[h] for h in AIR_HUB_IDS]
    for i in range(len(hubs)):
        for j in range(i + 1, len(hubs)):
            dist = haversine_km(hubs[i].lat, hubs[i].lon, hubs[j].lat, hubs[j].lon)
            # Gravity weight proportional to populations and inversely proportional to distance
            gravity_weight = (hubs[i].population * hubs[j].population) / (dist ** 0.8) * 0.08
            connections.append(Connection(hubs[i], hubs[j], "air", min(0.25, max(0.01, gravity_weight))))

    rows_by_id = {row[0]: row for row in WORLD_REGIONS_RAW}
    for row in WORLD_REGIONS_RAW:
        region_id, _, lat, lon, _, _ = row
        if region_id in AIR_HUB_IDS:
            continue
        region = by_id[region_id]
        nearest_hub = None
        nearest_dist = float("inf")
        for hub_id in AIR_HUB_IDS:
            hub_row = rows_by_id[hub_id]
            dist = haversine_km(lat, lon, hub_row[2], hub_row[3])
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_hub = by_id[hub_id]
        
        # Compute regional-to-hub flight gravity density
        gravity_weight = (region.population * nearest_hub.population) / (nearest_dist ** 0.8) * 0.12
        connections.append(Connection(region, nearest_hub, "air", min(0.20, max(0.02, gravity_weight))))

    return regions, connections


# --------------------------------------------------------------------------
# Disease presets
# --------------------------------------------------------------------------
#
# The first two are realistic human diseases. The other four are
# fiction-inspired outbreak profiles that do not reproduce any character,
# dialogue, or plot from any film or show -- they're epidemiological
# parameter sets (transmission type, how fast symptoms appear, how far
# people travel before they turn) tuned to match the well-known STYLE of
# spread each franchise is known for. The underlying simulation math is
# identical for every preset; only the numbers differ.

def build_disease_presets():
    return [
        Disease(
            name="Seasonal Flu-like",
            description="Airborne respiratory illness. Mild, spreads fast, low lethality -- like a bad flu season.",
            transmission_mode="airborne",
            beta=0.30, incubation_days=2, infectious_days=5, lethality=0.001,
            mobility_during_incubation=0.9,
            final_state_label="Recovered", infected_label="Infected",
        ),
        Disease(
            name="Severe Airborne Pandemic",
            description="Airborne respiratory illness with a longer incubation window and higher severity -- like a novel coronavirus.",
            transmission_mode="airborne",
            beta=0.50, incubation_days=5, infectious_days=10, lethality=0.01,
            mobility_during_incubation=0.9,
            final_state_label="Recovered", infected_label="Infected",
        ),
        Disease(
            name="Slow Shamblers",
            description="Inspired by slow-moving-undead fiction. Bite transmission only, very low mobility once turned, but bitten victims often hide the wound for days before turning -- long enough to catch a flight.",
            transmission_mode="bite",
            beta=0.15, incubation_days=3, infectious_days=999, lethality=0.05,
            mobility_during_incubation=0.55,
            final_state_label="Turned", infected_label="Turned (shambling)",
        ),
        Disease(
            name="Rage Outbreak",
            description='Inspired by fast-onset "rage" fiction. Extremely violent, near-instant symptom onset -- infected have almost no time to travel before turning, so this stays brutally local.',
            transmission_mode="bloodborne",
            beta=0.65, incubation_days=0.05, infectious_days=999, lethality=0.02,
            mobility_during_incubation=0.02,
            final_state_label="Turned", infected_label="Raging",
        ),
        Disease(
            name="Rapid Undead (dense-city)",
            description="Inspired by fast-zombie outbreak fiction set in dense cities and transit systems. Turns in minutes, spreads explosively in crowded spaces, minimal air travel before symptoms show.",
            transmission_mode="bite",
            beta=0.55, incubation_days=0.3, infectious_days=999, lethality=0.03,
            mobility_during_incubation=0.06,
            final_state_label="Turned", infected_label="Turned",
        ),
        Disease(
            name="Global Silent Spread",
            description="Inspired by outbreak fiction where panic and mass evacuation flights seed the virus worldwide before anyone realizes how fast it turns people.",
            transmission_mode="bite",
            beta=0.45, incubation_days=0.5, infectious_days=999, lethality=0.03,
            mobility_during_incubation=0.4,
            final_state_label="Turned", infected_label="Turned",
        ),
    ]
