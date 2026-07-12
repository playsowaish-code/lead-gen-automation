"""
main.py — daily lead generation run. 100% FREE — no API keys for the data
source (OpenStreetMap), only a free Google service account for writing to
Sheets (Sheets API itself has no cost, no billing account required).

What it does, in order:
  1. Loads config.yaml (countries/cities/categories/target).
  2. Loads state.json to know which (category, city) combo to start from today,
     so every run rotates forward instead of re-scanning the same businesses.
  3. For each combo: geocodes the city (cached), queries OpenStreetMap via
     Overpass for matching businesses, checks each one's website, and keeps
     the ones with no website or a poor website as "leads".
  4. Stops once daily_lead_target new leads are collected (or combos run out).
  5. Writes new leads to the Google Sheet (deduped against everything seen before).
  6. Saves updated state.json so tomorrow's run continues from where it left off.

Run with:
    python main.py
Requires env vars: GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_ID
(No Google Maps / Places API key needed — this uses free OpenStreetMap data.)
"""

import os
import json
import yaml
from datetime import date

from geocode import geocode_city
from overpass_search import search_businesses
from website_checker import check_website
from sheets_writer import write_leads

CONFIG_PATH = "config.yaml"
STATE_PATH = "state.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {"combo_index": 0}


def save_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)


def build_combo_list(config):
    """Flat list of (country, city, category_name, tag_pairs) tuples."""
    combos = []
    for country in config["countries"]:
        for city in config["cities"].get(country, []):
            for category_name, tag_pairs in config["categories"].items():
                combos.append((country, city, category_name, tag_pairs))
    return combos


def main():
    service_account_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]

    config = load_config()
    state = load_state()
    combos = build_combo_list(config)

    target = config["daily_lead_target"]
    radius = config["radius_meters"]

    start_index = state["combo_index"] % len(combos)
    collected = []
    combos_tried = 0

    print(f"Starting run. Target: {target} leads. Starting at combo #{start_index}. "
          f"Total combos available: {len(combos)}.")

    idx = start_index
    while len(collected) < target and combos_tried < len(combos):
        country, city, category_name, tag_pairs = combos[idx]
        print(f"[{combos_tried+1}/{len(combos)}] Searching: '{category_name}' in '{city}, {country}'")

        try:
            lat, lon = geocode_city(city, country)
        except RuntimeError as e:
            print(f"  [!] {e} — skipping this combo")
            idx = (idx + 1) % len(combos)
            combos_tried += 1
            continue

        businesses = search_businesses(tag_pairs, lat, lon, radius)

        for biz in businesses:
            result = check_website(biz["website"], config)

            if result["status"] in ("no_website", "poor_website"):
                collected.append({
                    "place_id": biz["osm_id"],
                    "business_name": biz["name"],
                    "category": category_name,
                    "city": city,
                    "country": country,
                    "phone": biz["phone"],
                    "website": biz["website"] or "(none)",
                    "lead_type": result["status"],
                    "reasons": "; ".join(result["reasons"]),
                    "address": biz["address"],
                })

            if len(collected) >= target:
                break

        idx = (idx + 1) % len(combos)
        combos_tried += 1

    state["combo_index"] = idx
    save_state(state)

    run_date = date.today().isoformat()
    written = write_leads(sheet_id, service_account_json, collected, run_date)

    print(f"Done. Found {len(collected)} candidate leads this run, "
          f"{written} were new and written to the sheet "
          f"({len(collected) - written} were duplicates already in the sheet).")

    if len(collected) < target:
        print(f"[note] Only found {len(collected)} leads (target was {target}). "
              f"This is normal with free OSM data in some cities — consider adding "
              f"more cities/categories to config.yaml, or widening radius_meters.")


if __name__ == "__main__":
    main()
