"""
overpass_search.py
Free replacement for Google Places — queries OpenStreetMap business data
via the Overpass API. No API key, no billing, no cost, ever.

Docs: https://wiki.openstreetmap.org/wiki/Overpass_API
Public endpoint has a shared rate limit, so we keep requests modest and
add a small delay between calls to be a good citizen.
"""

import time
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def build_query(tag_pairs: list, lat: float, lon: float, radius_meters: int) -> str:
    """
    tag_pairs: list like [["amenity","restaurant"], ["amenity","cafe"]]
    Builds an Overpass QL query matching nodes/ways with ANY of those tags
    within radius_meters of (lat, lon).
    """
    clauses = []
    for key, value in tag_pairs:
        clauses.append(f'  node["{key}"="{value}"](around:{radius_meters},{lat},{lon});')
        clauses.append(f'  way["{key}"="{value}"](around:{radius_meters},{lat},{lon});')

    body = "\n".join(clauses)
    return f"""
[out:json][timeout:25];
(
{body}
);
out center tags 60;
"""


def search_businesses(tag_pairs: list, lat: float, lon: float, radius_meters: int) -> list:
    """
    Returns a list of normalized business dicts:
      { name, phone, website, address, osm_id }
    """
    query = build_query(tag_pairs, lat, lon, radius_meters)

    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=40)
    except requests.exceptions.RequestException as e:
        print(f"  [!] Overpass request failed: {e}")
        return []

    time.sleep(1.5)  # be polite to the shared free endpoint

    if resp.status_code != 200:
        print(f"  [!] Overpass API error {resp.status_code}: {resp.text[:300]}")
        return []

    try:
        data = resp.json()
    except ValueError:
        print("  [!] Overpass returned non-JSON response")
        return []

    businesses = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue  # skip unnamed entries, not useful as leads

        # Build a rough address from whatever OSM address tags exist
        addr_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:city", ""),
            tags.get("addr:state", ""),
            tags.get("addr:postcode", ""),
        ]
        address = " ".join(p for p in addr_parts if p)

        website = tags.get("website") or tags.get("contact:website") or ""
        phone = tags.get("phone") or tags.get("contact:phone") or ""

        businesses.append({
            "osm_id": f"{el.get('type')}/{el.get('id')}",
            "name": name,
            "phone": phone,
            "website": website,
            "address": address,
        })

    return businesses
