"""
geocode.py
Turns a city name like "Austin, TX" into (lat, lon) using Nominatim
(OpenStreetMap's free geocoder). No API key needed.

Nominatim's usage policy requires:
  - A descriptive User-Agent header (not a browser-spoofing one)
  - Max 1 request/second
  - Results cached so you don't re-geocode the same city every run

Docs: https://nominatim.org/release-docs/latest/api/Search/
Usage policy: https://operations.osmfoundation.org/policies/nominatim/
"""

import os
import json
import time
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LeadGenAutomation/1.0 (personal project, contact: set-your-email-here)"
CACHE_PATH = "city_coords_cache.json"


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def geocode_city(city: str, country: str) -> tuple:
    """
    Returns (lat, lon) for a city, using a local cache to avoid repeat lookups.
    Raises RuntimeError if the city can't be found.
    """
    cache = _load_cache()
    cache_key = f"{city}|{country}"

    if cache_key in cache:
        return tuple(cache[cache_key])

    params = {
        "q": f"{city}, {country}",
        "format": "json",
        "limit": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
    time.sleep(1.1)  # respect Nominatim's 1 req/sec policy

    if resp.status_code != 200 or not resp.json():
        raise RuntimeError(f"Could not geocode '{city}, {country}'")

    result = resp.json()[0]
    lat, lon = float(result["lat"]), float(result["lon"])

    cache[cache_key] = [lat, lon]
    _save_cache(cache)

    return lat, lon
