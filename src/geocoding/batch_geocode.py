#!/usr/bin/env python3
"""
Batch geocoding script for amusement parks, World's Largest, and NPS sites.
Uses OpenStreetMap Nominatim API for geocoding.
"""

import time
import json
from typing import Dict, List, Tuple
import requests

# Geocoded data we already have
GEOCODED_PARKS = {
    "Adventureland Iowa": {"address": "3200 Adventureland Dr, Altoona, IA 50009", "coords": (41.6544, -93.4999)},
    "Busch Gardens Tampa": {"address": "10165 N McKinley Dr, Tampa, FL 33612", "coords": (28.0379, -82.4216)},
    "Busch Gardens Williamsburg": {"address": "1 Busch Gardens Blvd, Williamsburg, VA 23185", "coords": (37.2337, -76.6440)},
    "California's Great America": {"address": "5150 Great America Pkwy, Santa Clara, CA 95054", "coords": (37.3979, -121.9743)},
    "Carowinds": {"address": "14523 Carowinds Blvd, Charlotte, NC 28273", "coords": (35.1023, -80.9414)},
    "Cedar Point": {"address": "1 Cedar Point Dr, Sandusky, OH 44870", "coords": (41.4823, -82.6835)},
    "Dollywood": {"address": "2700 Dollywood Parks Blvd, Pigeon Forge, TN 37863", "coords": (35.7951, -83.5312)},
    "Hersheypark": {"address": "100 W Hersheypark Dr, Hershey, PA 17033", "coords": (40.2888, -76.6548)},
    "Kings Island": {"address": "6300 Kings Island Dr, Mason, OH 45040", "coords": (39.3451, -84.2720)},
    "Kings Dominion": {"address": "16000 Theme Park Way, Doswell, VA 23047", "coords": (37.8398, -77.4443)},
    "Knoebels": {"address": "391 Knoebels Blvd, Elysburg, PA 17824", "coords": (40.8783, -76.4962)},
    "Silver Dollar City": {"address": "399 Silver Dollar City Pkwy, Branson, MO 65616", "coords": (36.6690, -93.3380)},
    "Six Flags Magic Mountain": {"address": "26101 Magic Mountain Pkwy, Valencia, CA 91355", "coords": (34.4244, -118.5967)},
    "Universal Islands of Adventure": {"address": "6000 Universal Blvd, Orlando, FL 32819", "coords": (28.4720, -81.4697)},
    "Universal Epic Universe": {"address": "1001 Epic Blvd, Orlando, FL 32819", "coords": (28.4400, -81.4500)},
}

# Remaining parks to geocode
REMAINING_PARKS = [
    "Dorney Park",
    "Fun Spot America Atlanta",
    "Holiday World",
    "Kemah Boardwalk",
    "Kennywood",
    "Kentucky Kingdom",
    "Knott's Berry Farm",
    "Lagoon",
    "Lake Compounce",
    "Lost Island Theme Park",
    "Michigan's Adventure",
    "Mt. Olympus Water & Theme Park",
    "SeaWorld Orlando",
    "SeaWorld San Antonio",
    "Silverwood Theme Park",
    "Six Flags Darien Lake",
    "Six Flags Discovery Kingdom",
    "Six Flags Fiesta Texas",
    "Six Flags Great Adventure",
    "Six Flags Great America",
    "Six Flags New England",
    "Six Flags Over Georgia",
    "Six Flags Over Texas",
    "Six Flags St Louis",
    "Universal Studios Florida",
    "Valleyfair!",
    "Waldameer",
    "Walt Disney World - Disney's Animal Kingdom",
    "Walt Disney World - Epcot",
    "Walt Disney World - Magic Kingdom",
    "Worlds of Fun",
]

def geocode_nominatim(query: str) -> Tuple[float, float] | None:
    """Geocode an address using OpenStreetMap Nominatim API."""
    base_url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "us",
    }
    headers = {
        "User-Agent": "TripPlanningApp/1.0"
    }

    try:
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return (lat, lon)
    except Exception as e:
        print(f"Error geocoding {query}: {e}")

    return None

def batch_geocode_parks():
    """Geocode all remaining parks."""
    results = {}

    for park in REMAINING_PARKS:
        print(f"Geocoding {park}...")
        coords = geocode_nominatim(park + " amusement park")
        if coords:
            results[park] = {
                "address": "TBD - needs manual lookup",
                "coords": coords
            }
        else:
            results[park] = {
                "address": "NOT FOUND",
                "coords": None
            }
        # Rate limiting - 1 request per second
        time.sleep(1)

    # Combine with already geocoded parks
    all_parks = {**GEOCODED_PARKS, **results}

    # Save to file
    with open("/workspace/src/geocoding/geocoded_parks.json", "w") as f:
        json.dump(all_parks, f, indent=2)

    print(f"\nGeocoded {len(results)} parks")
    print(f"Total parks: {len(all_parks)}")

    return all_parks

if __name__ == "__main__":
    batch_geocode_parks()
