#!/usr/bin/env python3
"""
Find sites with bad geocodes by checking if their coordinates match their stated location.
"""
import sys
sys.path.insert(0, '/workspace/src/routing')

import math
from nps_data_loader import NPSDataLoader

# Known state centroids for sanity checking
STATE_CENTROIDS = {
    'Alabama': (32.806671, -86.791130),
    'Arizona': (34.048927, -111.093735),
    'Arkansas': (34.969704, -92.373123),
    'California': (36.778259, -119.417931),
    'Colorado': (39.550053, -105.782066),
    'Connecticut': (41.603221, -73.087749),
    'Delaware': (38.910832, -75.527670),
    'Florida': (27.994402, -81.760254),
    'Georgia': (33.040619, -83.643074),
    'Idaho': (44.068203, -114.742043),
    'Illinois': (40.633125, -89.398529),
    'Indiana': (40.267194, -86.134902),
    'Iowa': (41.878003, -93.097702),
    'Kansas': (39.011902, -98.484246),
    'Kentucky': (37.839333, -84.270020),
    'Louisiana': (30.984298, -91.962333),
    'Maine': (45.253783, -69.445469),
    'Maryland': (39.045753, -76.641273),
    'Massachusetts': (42.407211, -71.382437),
    'Michigan': (44.314844, -85.602364),
    'Minnesota': (46.729553, -94.685899),
    'Mississippi': (32.354668, -89.398528),
    'Missouri': (37.964253, -91.831833),
    'Montana': (46.879682, -110.362566),
    'Nebraska': (41.492537, -99.901813),
    'Nevada': (38.802610, -116.419389),
    'New Hampshire': (43.193852, -71.572395),
    'New Jersey': (40.058324, -74.405661),
    'New Mexico': (34.519940, -105.870090),
    'New York': (42.165726, -74.948051),
    'North Carolina': (35.759573, -79.019300),
    'North Dakota': (47.551493, -101.002012),
    'Ohio': (40.417287, -82.907123),
    'Oklahoma': (35.007752, -97.092877),
    'Oregon': (43.804133, -120.554201),
    'Pennsylvania': (41.203322, -77.194525),
    'Rhode Island': (41.580095, -71.477429),
    'South Carolina': (33.836081, -81.163725),
    'South Dakota': (43.969515, -99.901813),
    'Tennessee': (35.517491, -86.580447),
    'Texas': (31.968599, -99.901813),
    'Utah': (39.320980, -111.093731),
    'Vermont': (44.558803, -72.577841),
    'Virginia': (37.431573, -78.656894),
    'Washington': (47.751076, -120.740135),
    'West Virginia': (38.597626, -80.454903),
    'Wisconsin': (43.784440, -88.787868),
    'Wyoming': (43.075970, -107.290283),
    'DC': (38.907192, -77.036873),
    'District of Columbia': (38.907192, -77.036873),
}

def haversine(lat1, lon1, lat2, lon2):
    """Distance in miles"""
    R = 3959
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def main():
    loader = NPSDataLoader()
    all_sites = loader.load_all_sites()

    print("=" * 80)
    print("GEOCODE VERIFICATION")
    print("=" * 80)

    bad_geocodes = []

    for name, site in all_sites.items():
        state = site.state

        # Skip if state looks like a zip code
        if state.isdigit():
            print(f"\nBAD STATE (zip code): {name}")
            print(f"  State field: {state}")
            print(f"  City: {site.city}")
            print(f"  Coords: ({site.lat}, {site.lon})")
            bad_geocodes.append({
                'name': name,
                'issue': 'state_is_zipcode',
                'state': state,
                'city': site.city,
                'lat': site.lat,
                'lon': site.lon
            })
            continue

        # Check if state is in our list
        if state not in STATE_CENTROIDS:
            # Try partial match
            matched = False
            for known_state in STATE_CENTROIDS:
                if state in known_state or known_state in state:
                    state = known_state
                    matched = True
                    break
            if not matched:
                print(f"\nUNKNOWN STATE: {name}")
                print(f"  State: {state}")
                bad_geocodes.append({
                    'name': name,
                    'issue': 'unknown_state',
                    'state': state,
                    'city': site.city,
                    'lat': site.lat,
                    'lon': site.lon
                })
                continue

        # Check distance from state centroid
        state_lat, state_lon = STATE_CENTROIDS[state]
        dist = haversine(site.lat, site.lon, state_lat, state_lon)

        # Sites should generally be within 400 miles of state center
        # (exception for large states like Texas, California)
        max_dist = 600 if state in ['Texas', 'California', 'Montana', 'Alaska'] else 400

        if dist > max_dist:
            print(f"\nBAD GEOCODE: {name}")
            print(f"  Stated state: {state}")
            print(f"  Coords: ({site.lat}, {site.lon})")
            print(f"  Distance from {state} center: {dist:.0f} miles")
            bad_geocodes.append({
                'name': name,
                'issue': 'wrong_location',
                'state': state,
                'city': site.city,
                'lat': site.lat,
                'lon': site.lon,
                'dist_from_state': dist
            })

    print("\n" + "=" * 80)
    print(f"SUMMARY: Found {len(bad_geocodes)} sites with potential geocode issues")
    print("=" * 80)

    for bg in bad_geocodes:
        print(f"  - {bg['name']}: {bg['issue']}")

    return bad_geocodes


if __name__ == "__main__":
    main()
