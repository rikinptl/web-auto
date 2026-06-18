"""Google Sheets helpers for the lead inventory.

API efficiency: prefer upsert_leads() for multiple rows — one read + one batch
write instead of per-row requests (Google Sheets limit: ~300 requests/min).
"""

import json
import os
import time

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

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

LAST_COL = chr(64 + len(HEADERS))
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 2.0


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


def _with_retry(action, label: str):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return action()
        except APIError as exc:
            if attempt == MAX_RETRIES or getattr(exc, "response", None) is None:
                raise
            status = exc.response.status_code
            if status not in {429, 500, 503}:
                raise
            wait = RETRY_BACKOFF_SEC * attempt
            print(f"Sheets API {status} during {label}; retrying in {wait:.1f}s...")
            time.sleep(wait)


def ensure_headers(worksheet) -> None:
    first_row = worksheet.row_values(1)
    if first_row == HEADERS:
        return

    def _update_headers():
        worksheet.update(values=[HEADERS], range_name="A1", value_input_option="USER_ENTERED")
        worksheet.format(f"A1:{LAST_COL}1", {"textFormat": {"bold": True}})

    _with_retry(_update_headers, "ensure_headers")


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


def _load_row_index(worksheet) -> dict[tuple[str, str], int]:
    records = _with_retry(worksheet.get_all_records, "get_all_records")
    index: dict[tuple[str, str], int] = {}
    for row_number, row in enumerate(records, start=2):
        key = (row.get("Business Name", ""), row.get("Phone", ""))
        index[key] = row_number
    return index


def upsert_leads(leads: list[dict]) -> dict[str, int]:
    """Batch upsert leads using minimal Sheets API calls."""
    if not leads:
        return {"updated": 0, "appended": 0}

    worksheet = get_worksheet()
    ensure_headers(worksheet)
    row_index = _load_row_index(worksheet)

    batch_updates = []
    rows_to_append = []

    for lead in leads:
        key = (lead.get("name", ""), lead.get("phone", ""))
        values = lead_to_row(lead)
        existing_row = row_index.get(key)
        if existing_row:
            batch_updates.append(
                {"range": f"A{existing_row}:{LAST_COL}{existing_row}", "values": [values]}
            )
        else:
            rows_to_append.append(values)

    if batch_updates:

        def _batch_update():
            worksheet.batch_update(batch_updates, value_input_option="USER_ENTERED")

        _with_retry(_batch_update, "batch_update")
        print(f"Batch updated {len(batch_updates)} row(s)")

    if rows_to_append:

        def _append_rows():
            worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

        _with_retry(_append_rows, "append_rows")
        print(f"Batch appended {len(rows_to_append)} row(s)")

    return {"updated": len(batch_updates), "appended": len(rows_to_append)}


def upsert_lead(lead: dict) -> int:
    """Upsert a single lead (wraps batch upsert for pipeline steps)."""
    result = upsert_leads([lead])
    return result["updated"] + result["appended"]
