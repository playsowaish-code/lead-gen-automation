"""
sheets_writer.py
Writes new leads to a Google Sheet, and keeps a "Seen IDs" tab so the same
business never gets added twice across daily runs.

Setup required (see README.md):
  1. Create a Google Cloud service account, download its JSON key.
  2. Share your target Google Sheet with the service account's email
     (looks like xxxx@xxxx.iam.gserviceaccount.com) as an Editor.
  3. Put the JSON key contents in the GOOGLE_SERVICE_ACCOUNT_JSON secret/env var.
"""

import json
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LEADS_HEADER = [
    "Date Added", "Business Name", "Category", "City", "Country",
    "Phone", "Email", "Website", "Lead Type", "Reasons", "Address", "Place ID",
]


def get_client(service_account_json_str: str):
    info = json.loads(service_account_json_str)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet(sheet, title: str, header: list):
    try:
        ws = sheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=1000, cols=len(header) + 2)
        ws.append_row(header)
    return ws


def load_seen_ids(seen_ws) -> set:
    values = seen_ws.col_values(1)
    return set(values[1:])


def write_leads(sheet_id: str, service_account_json_str: str, new_leads: list, run_date: str):
    """
    new_leads: list of dicts with keys matching LEADS_HEADER (lowercase_with_underscores)
    Returns the count actually written (after dedupe).
    """
    client = get_client(service_account_json_str)
    sheet = client.open_by_key(sheet_id)

    leads_ws = get_or_create_worksheet(sheet, "Leads", LEADS_HEADER)
    seen_ws = get_or_create_worksheet(sheet, "Seen IDs", ["Place ID"])

    seen_ids = load_seen_ids(seen_ws)

    rows_to_append = []
    seen_rows_to_append = []
    written = 0

    for lead in new_leads:
        place_id = lead["place_id"]
        if place_id in seen_ids:
            continue

        rows_to_append.append([
            run_date,
            lead["business_name"],
            lead["category"],
            lead["city"],
            lead["country"],
            lead["phone"],
            lead.get("email", ""),
            lead["website"],
            lead["lead_type"],
            lead["reasons"],
            lead["address"],
            place_id,
        ])
        seen_rows_to_append.append([place_id])
        seen_ids.add(place_id)
        written += 1

    if rows_to_append:
        leads_ws.append_rows(rows_to_append, value_input_option="RAW")
        seen_ws.append_rows(seen_rows_to_append, value_input_option="RAW")
    return written
