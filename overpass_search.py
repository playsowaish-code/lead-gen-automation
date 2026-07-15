"""
overpass_search.py
Free replacement for Google Places — queries OpenStreetMap business data
via the Overpass API. No API key, no billing, no cost, ever.

Docs: https://wiki.openstreetmap.org/wiki/Overpass_API

NOTE (2026): the main overpass-api.de endpoint has been aggressively
rate-limiting/blocking requests that look "bot-like" (missing a real
User-Agent/Accept headers) due to a wave of AI-scraper traffic. We send
proper headers, and if a server still rejects us (406/429/5xx), we
automatically fall back to a list of alternate public Overpass mirrors.
"""

import time
import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

HEADERS = {
    "User-Agent": "LeadGenAutomation/1.0 (personal project; contact: set-your-email-here)",
    "Accept": "application/json",
    "Accept-Language": "en",
    "Content-Type": "application/x-www-form-urlencoded",
}


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


def _query_endpoint(url: str, query: str):
    """Tries one endpoint. Returns parsed JSON dict on success, None on failure."""
    try:
        resp = requests.post(url, data={"data": query}, headers=HEADERS, timeout=40)
    except requests.exceptions.RequestException as e:
        print(f"  [!] {url} request failed: {e}")
        return None

    if resp.status_code != 200:
        print(f"  [!] {url} returned {resp.status_code}: {resp.text[:150]}")
        return None

    try:
        return resp.json()
    except ValueError:
        print(f"  [!] {url} returned non-JSON response")
        return None


def search_businesses(tag_pairs: list, lat: float, lon: float, radius_meters: int) -> list:
    """
    Returns a list of normalized business dicts:
      { name, phone, website, address, osm_id }
    Tries each Overpass mirror in order until one responds successfully.
    """
    query = build_query(tag_pairs, lat, lon, radius_meters)

    data = None
    for endpoint in OVERPASS_ENDPOINTS:
        data = _query_endpoint(endpoint, query)
        time.sleep(1.5)
        if data is not None:
            break

    if data is None:
        print("  [!] All Overpass endpoints failed for this query — skipping")
        return []

    businesses = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

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
