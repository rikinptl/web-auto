"""Google Sheets helpers for the lead inventory.

API efficiency: prefer upsert_leads() for multiple rows — one read + one batch
write instead of per-row requests (Google Sheets limit: ~300 requests/min).
"""

import json
import os
import re
import time

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

from maps_url import place_key, resolve_maps_url

def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def record_to_lead(row: dict) -> dict:
    return {
        "name": row.get("Business Name", ""),
        "niche": row.get("Niche", ""),
        "category": row.get("Niche", ""),
        "phone": row.get("Phone", ""),
        "city": row.get("City", ""),
        "scraped_status": row.get("Scraped Status", ""),
        "copy_status": row.get("DeepSeek Copy Status", ""),
        "live_url": row.get("Live URL", ""),
        "google_maps_url": row.get("Google Maps URL", ""),
    }


def load_inventory() -> list[dict]:
    """Read all leads currently stored in the Google Sheet."""
    worksheet = get_worksheet()
    ensure_headers(worksheet)
    records = _with_retry(worksheet.get_all_records, "get_all_records")
    leads: list[dict] = []
    for row in records:
        lead = record_to_lead(row)
        if not lead.get("name"):
            continue
        if is_mock_lead(lead):
            continue
        leads.append(lead)
    return leads


class InventorySkipIndex:
    """Fast lookups to skip businesses already present in the sheet."""

    def __init__(self, leads: list[dict]):
        self.maps_keys: set[str] = set()
        self.name_phone: set[tuple[str, str]] = set()

        for lead in leads:
            maps_key = place_key(resolve_maps_url(lead))
            if maps_key:
                self.maps_keys.add(maps_key)

            name = normalize_name(lead.get("name", ""))
            phone = normalize_phone(lead.get("phone", ""))
            if name:
                self.name_phone.add((name, phone))

    def has_maps_url(self, url: str) -> bool:
        key = place_key(url)
        return bool(key and key in self.maps_keys)

    def has_lead(self, lead: dict) -> bool:
        name = normalize_name(lead.get("name", ""))
        phone = normalize_phone(lead.get("phone", ""))
        if name and (name, phone) in self.name_phone:
            return True
        maps_key = place_key(resolve_maps_url(lead))
        return bool(maps_key and maps_key in self.maps_keys)

    def register_lead(self, lead: dict) -> None:
        """Track a newly scraped lead so later batches in the same run skip it."""
        maps_key = place_key(resolve_maps_url(lead))
        if maps_key:
            self.maps_keys.add(maps_key)
        name = normalize_name(lead.get("name", ""))
        phone = normalize_phone(lead.get("phone", ""))
        if name:
            self.name_phone.add((name, phone))

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


def is_mock_lead(lead: dict) -> bool:
    name = (lead.get("name") or "").strip().lower()
    phone = (lead.get("phone") or "").strip()
    if "joe's plumbing" in name or "joes plumbing" in name:
        return True
    if phone in {"(512) 555-0142", "512-555-0142", "5125550142"}:
        return True
    return False


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
        if is_mock_lead(lead):
            raise ValueError(f"Refusing mock lead data: {lead.get('name')}")
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
    if is_mock_lead(lead):
        raise ValueError(f"Refusing mock lead data: {lead.get('name')}")
    result = upsert_leads([lead])
    return result["updated"] + result["appended"]


def replace_inventory(leads: list[dict]) -> None:
    """Replace all sheet data rows with scraped leads (removes stale/mock rows)."""
    for lead in leads:
        if is_mock_lead(lead):
            raise ValueError(f"Refusing mock lead data: {lead.get('name')}")

    worksheet = get_worksheet()
    ensure_headers(worksheet)
    row_count = len(_with_retry(worksheet.get_all_records, "get_all_records"))

    if row_count:

        def _clear_rows():
            worksheet.batch_clear([f"A2:{LAST_COL}{row_count + 1}"])

        _with_retry(_clear_rows, "batch_clear")

    if not leads:
        print("Sheet inventory cleared (header only)")
        return

    rows = [lead_to_row(lead) for lead in leads]

    def _write_rows():
        worksheet.update(
            values=rows,
            range_name=f"A2:{LAST_COL}{len(rows) + 1}",
            value_input_option="USER_ENTERED",
        )

    _with_retry(_write_rows, "replace_inventory")
    print(f"Replaced sheet inventory with {len(rows)} real lead(s)")
