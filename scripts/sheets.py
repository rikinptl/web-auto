"""Google Sheets helpers for the lead inventory."""

import json
import os

import gspread
from google.oauth2.service_account import Credentials

from maps_url import resolve_maps_url

HEADERS = [
    "Business Name",
    "Niche",
    "Phone",
    "City",
    "Scraped Status",
    "DeepSeek Copy Status",
    "Live URL",
    "Google Maps URL",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_credentials() -> Credentials:
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        return Credentials.from_service_account_info(json.loads(raw_json), scopes=SCOPES)

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise ValueError(
            "Set GOOGLE_APPLICATION_CREDENTIALS (local) or GOOGLE_SERVICE_ACCOUNT_JSON (CI)"
        )
    return Credentials.from_service_account_file(creds_path, scopes=SCOPES)


def get_worksheet():
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")

    client = gspread.authorize(get_credentials())
    return client.open_by_key(spreadsheet_id).sheet1


def ensure_headers(worksheet) -> None:
    first_row = worksheet.row_values(1)
    if first_row == HEADERS:
        return
    worksheet.update(values=[HEADERS], range_name="A1", value_input_option="USER_ENTERED")
    worksheet.format(f"A1:{chr(64 + len(HEADERS))}1", {"textFormat": {"bold": True}})


def lead_to_row(lead: dict) -> list:
    return [
        lead.get("name", ""),
        lead.get("niche") or lead.get("category", ""),
        lead.get("phone", ""),
        lead.get("city", ""),
        lead.get("scraped_status", "Done"),
        lead.get("copy_status", "Pending"),
        lead.get("live_url", ""),
        resolve_maps_url(lead),
    ]


def find_row_index(worksheet, name: str, phone: str) -> int | None:
    records = worksheet.get_all_records()
    for index, row in enumerate(records, start=2):
        if row.get("Business Name") == name and row.get("Phone") == phone:
            return index
    return None


def upsert_lead(lead: dict) -> int:
    worksheet = get_worksheet()
    ensure_headers(worksheet)

    name = lead.get("name", "")
    phone = lead.get("phone", "")
    values = lead_to_row(lead)
    row_index = find_row_index(worksheet, name, phone)

    if row_index:
        worksheet.update(
            values=[values],
            range_name=f"A{row_index}:H{row_index}",
            value_input_option="USER_ENTERED",
        )
        print(f"Updated sheet row {row_index} for {name}")
        return row_index

    worksheet.append_row(values, value_input_option="USER_ENTERED")
    new_row = len(worksheet.get_all_records()) + 1
    print(f"Appended sheet row {new_row} for {name}")
    return new_row
