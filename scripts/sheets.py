"""Google Sheets helpers for the lead inventory.

API efficiency: prefer upsert_leads() for multiple rows — one read + one batch
write instead of per-row requests (Google Sheets limit: ~300 requests/min).

Sheet1 = lead inventory. Audit Log = append-only metadata for auditing.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, WorksheetNotFound

from maps_url import place_key, resolve_maps_url

from text_clean import clean_phone, strip_icon_glyphs

def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def record_to_lead(row: dict) -> dict:
    return {
        "name": strip_icon_glyphs(row.get("Business Name", "")),
        "niche": row.get("Niche", ""),
        "category": row.get("Niche", ""),
        "phone": clean_phone(row.get("Phone", "")),
        "city": row.get("City", ""),
        "address": strip_icon_glyphs(row.get("Address", "")),
        "scraped_status": row.get("Scraped Status", ""),
        "copy_status": row.get("DeepSeek Copy Status", ""),
        "live_url": row.get("Live URL", ""),
        "google_maps_url": row.get("Google Maps URL", ""),
        "site_created_at": row.get("Site Created", ""),
        "rating": row.get("Rating", ""),
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


def load_pending_deploy_leads() -> list[dict]:
    """Leads in the sheet that still need copy and/or a live site URL."""
    pending: list[dict] = []
    for lead in load_inventory():
        copy_done = (lead.get("copy_status") or "").strip().lower() == "done"
        has_live = (lead.get("live_url") or "").strip().startswith("http")
        if not copy_done or not has_live:
            pending.append(lead)
    return pending


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
    "Address",
    "Scraped Status",
    "DeepSeek Copy Status",
    "Live URL",
    "Google Maps URL",
    "Site Created",
    "Rating",
]

AUDIT_SHEET_NAME = "Audit Log"
AUDIT_HEADERS = [
    "Timestamp UTC",
    "Event",
    "Business Name",
    "Phone",
    "Niche",
    "City",
    "Google Maps URL",
    "Live URL",
    "Deploy Repo",
    "Site Created",
    "GitHub Run ID",
    "Rating",
    "Review Snippets",
    "Address",
    "Est AI Cost USD",
    "Notes",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LAST_COL = chr(64 + len(HEADERS))
AUDIT_LAST_COL = chr(64 + len(AUDIT_HEADERS))
MAX_RETRIES = 8
RETRY_BACKOFF_SEC = 5.0


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


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


def get_spreadsheet():
    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_SPREADSHEET_ID is not set")

    client = gspread.authorize(get_credentials())
    return client.open_by_key(spreadsheet_id)


def get_worksheet():
    return get_spreadsheet().sheet1


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


def ensure_audit_headers(worksheet) -> None:
    first_row = worksheet.row_values(1)
    if first_row == AUDIT_HEADERS:
        return

    def _update_headers():
        worksheet.update(values=[AUDIT_HEADERS], range_name="A1", value_input_option="USER_ENTERED")
        worksheet.format(f"A1:{AUDIT_LAST_COL}1", {"textFormat": {"bold": True}})

    _with_retry(_update_headers, "ensure_audit_headers")


def get_audit_worksheet():
    spreadsheet = get_spreadsheet()
    try:
        worksheet = spreadsheet.worksheet(AUDIT_SHEET_NAME)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=AUDIT_SHEET_NAME,
            rows=2000,
            cols=len(AUDIT_HEADERS),
        )
    ensure_audit_headers(worksheet)
    return worksheet


def is_mock_lead(lead: dict) -> bool:
    name = (lead.get("name") or "").strip().lower()
    phone = (lead.get("phone") or "").strip()
    if "joe's plumbing" in name or "joes plumbing" in name:
        return True
    if phone in {"(512) 555-0142", "512-555-0142", "5125550142"}:
        return True
    return False


def _sheet_rating(lead: dict) -> str:
    val = lead.get("rating")
    if val is None or val == "":
        return ""
    try:
        return str(float(val))
    except (TypeError, ValueError):
        return str(val).strip()


def _audit_review_snippets(lead: dict) -> str:
    snippets = lead.get("review_snippets") or []
    if isinstance(snippets, list) and snippets:
        return str(len(snippets))
    reviews = lead.get("reviews")
    if reviews not in (None, ""):
        try:
            count = int(float(reviews))
            return str(count) if count > 0 else ""
        except (TypeError, ValueError):
            pass
    return ""


def _deploy_repo_slug(lead: dict, event: str) -> str:
    if event not in {"site_deployed", "site_redeployed"}:
        return ""
    explicit = os.environ.get("DEPLOY_REPO", "").strip()
    if explicit:
        return explicit
    try:
        from deploy_org_site import repo_slug_for_lead

        return repo_slug_for_lead(lead)
    except Exception:
        return ""


def enrich_lead_for_audit(lead: dict) -> dict:
    """Fill audit fields from the sheet when the lead payload is partial (e.g. deploy-pending export)."""
    enriched = {**lead}
    if not str(enriched.get("google_maps_url") or "").strip():
        enriched["google_maps_url"] = resolve_maps_url(enriched)

    try:
        existing = find_lead_in_inventory(enriched.get("name", ""), enriched.get("phone", ""))
    except Exception:
        existing = None

    if existing:
        for sheet_key, lead_key in (
            ("Live URL", "live_url"),
            ("Google Maps URL", "google_maps_url"),
            ("Site Created", "site_created_at"),
            ("Rating", "rating"),
            ("Niche", "niche"),
            ("City", "city"),
            ("Address", "address"),
        ):
            if not str(enriched.get(lead_key) or "").strip():
                enriched[lead_key] = existing.get(sheet_key, "")

    return enriched


def _audit_notes(lead: dict, event: str, notes: str) -> str:
    parts = [notes.strip()] if notes and notes.strip() else []
    if event == "lead_scraped":
        reviews = lead.get("reviews")
        if reviews not in (None, ""):
            try:
                parts.append(f"{int(float(reviews))} Google reviews")
            except (TypeError, ValueError):
                pass
    return "; ".join(part for part in parts if part)


def audit_row_from_lead(lead: dict, event: str, notes: str = "") -> list:
    lead = enrich_lead_for_audit(lead)
    est_cost = ""
    if event in {"site_deployed", "site_redeployed"}:
        est_cost = os.environ.get("EST_AI_COST_USD", os.environ.get("DEEPSEEK_EST_COST_PER_SITE", "0.03"))

    live_url = lead.get("live_url", "") if event in {"site_deployed", "site_redeployed"} else ""
    site_created = lead.get("site_created_at", "") if event in {"site_deployed", "site_redeployed"} else ""

    return [
        utc_now_str(),
        event,
        strip_icon_glyphs(lead.get("name", "")),
        clean_phone(lead.get("phone", "")),
        lead.get("niche") or lead.get("category", ""),
        lead.get("city", ""),
        resolve_maps_url(lead),
        live_url,
        _deploy_repo_slug(lead, event),
        site_created,
        os.environ.get("GITHUB_RUN_ID", ""),
        _sheet_rating(lead),
        _audit_review_snippets(lead),
        strip_icon_glyphs(lead.get("address", "")),
        est_cost,
        _audit_notes(lead, event, notes),
    ]


def lead_to_row(lead: dict) -> list:
    return [
        strip_icon_glyphs(lead.get("name", "")),
        lead.get("niche") or lead.get("category", ""),
        clean_phone(lead.get("phone", "")),
        lead.get("city", ""),
        strip_icon_glyphs(lead.get("address", "")),
        lead.get("scraped_status", "Done"),
        lead.get("copy_status", "Pending"),
        lead.get("live_url", ""),
        resolve_maps_url(lead),
        lead.get("site_created_at", ""),
        _sheet_rating(lead),
    ]


def _merge_existing_fields(lead: dict, existing: dict | None) -> dict:
    """Preserve inventory fields not present on incoming lead payloads (e.g. scrape-only updates)."""
    if not existing:
        return lead
    merged = dict(lead)
    for sheet_key, lead_key in (
        ("Live URL", "live_url"),
        ("DeepSeek Copy Status", "copy_status"),
        ("Site Created", "site_created_at"),
        ("Google Maps URL", "google_maps_url"),
        ("Rating", "rating"),
        ("Address", "address"),
    ):
        if not str(merged.get(lead_key) or "").strip():
            merged[lead_key] = existing.get(sheet_key, "")
    return merged


def append_audit_record(lead: dict, event: str, notes: str = "") -> None:
    """Append one row to the Audit Log sheet (never overwrites history)."""
    append_audit_records_batch([(lead, event, notes)])


def append_audit_records_batch(
    events: list[tuple[dict, str, str]],
) -> None:
    """Append multiple audit rows in one Sheets API call."""
    if not events:
        return

    worksheet = get_audit_worksheet()
    rows = [audit_row_from_lead(lead, event, notes=notes) for lead, event, notes in events]

    def _append():
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")

    _with_retry(_append, "append_audit_records_batch")
    for lead, event, _ in events:
        print(f"Audit log: {event} — {lead.get('name', '')}", flush=True)


def find_lead_in_inventory(name: str, phone: str) -> dict | None:
    """Return existing sheet row as dict keyed by header names."""
    worksheet = get_worksheet()
    ensure_headers(worksheet)
    records = _with_retry(worksheet.get_all_records, "get_all_records")
    name_norm = strip_icon_glyphs(name)
    phone_norm = clean_phone(phone)
    for row in records:
        if (
            strip_icon_glyphs(row.get("Business Name", "")) == name_norm
            and clean_phone(row.get("Phone", "")) == phone_norm
        ):
            return row
    return None


def _inventory_index(records: list[dict]) -> tuple[dict[tuple[str, str], int], dict[tuple[str, str], dict]]:
    row_index: dict[tuple[str, str], int] = {}
    existing_by_key: dict[tuple[str, str], dict] = {}
    for row_number, row in enumerate(records, start=2):
        key = (
            strip_icon_glyphs(row.get("Business Name", "")),
            clean_phone(row.get("Phone", "")),
        )
        row_index[key] = row_number
        existing_by_key[key] = row
    return row_index, existing_by_key


def upsert_leads(leads: list[dict]) -> dict[str, int]:
    """Batch upsert leads using minimal Sheets API calls."""
    if not leads:
        return {"updated": 0, "appended": 0}

    worksheet = get_worksheet()
    ensure_headers(worksheet)
    existing_records = _with_retry(worksheet.get_all_records, "get_all_records")
    row_index, existing_by_key = _inventory_index(existing_records)

    batch_updates = []
    rows_to_append = []
    audit_events: list[tuple[dict, str]] = []

    for lead in leads:
        if is_mock_lead(lead):
            raise ValueError(f"Refusing mock lead data: {lead.get('name')}")
        phone = clean_phone(lead.get("phone", ""))
        lead = {**lead, "phone": phone, "name": strip_icon_glyphs(lead.get("name", ""))}
        key = (lead.get("name", ""), phone)
        existing = existing_by_key.get(key)
        lead = _merge_existing_fields(lead, existing)
        values = lead_to_row(lead)
        existing_row = row_index.get(key)
        if existing_row:
            batch_updates.append(
                {"range": f"A{existing_row}:{LAST_COL}{existing_row}", "values": [values]}
            )
        else:
            rows_to_append.append(values)
            if os.environ.get("AUDIT_SCRAPE", "true").lower() in {"1", "true", "yes"}:
                audit_events.append((lead, "lead_scraped"))

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

    if audit_events:
        try:
            append_audit_records_batch(
                [(lead, event, "New lead added to inventory") for lead, event in audit_events]
            )
        except Exception as exc:
            print(
                f"Warning: audit log write failed after sheet upsert ({exc}); "
                "inventory rows were saved.",
                flush=True,
            )

    return {"updated": len(batch_updates), "appended": len(rows_to_append)}


def upsert_lead(lead: dict) -> int:
    """Upsert a single lead (wraps batch upsert for pipeline steps)."""
    if is_mock_lead(lead):
        raise ValueError(f"Refusing mock lead data: {lead.get('name')}")
    result = upsert_leads([lead])
    return result["updated"] + result["appended"]


def sync_deploy_lead(lead: dict) -> None:
    """Write deploy results to inventory with one sheet read + one row write."""
    if is_mock_lead(lead):
        raise ValueError(f"Refusing mock lead data: {lead.get('name')}")

    phone = clean_phone(lead.get("phone", ""))
    lead = {**lead, "phone": phone, "name": strip_icon_glyphs(lead.get("name", ""))}
    key = (lead.get("name", ""), phone)

    worksheet = get_worksheet()
    ensure_headers(worksheet)
    existing_records = _with_retry(worksheet.get_all_records, "get_all_records")
    row_index, existing_by_key = _inventory_index(existing_records)
    existing = existing_by_key.get(key)

    had_live = bool((existing or {}).get("Live URL", "").strip().startswith("http"))
    had_created = bool((existing or {}).get("Site Created", "").strip())
    lead = _merge_existing_fields(lead, existing)

    if lead.get("live_url", "").strip().startswith("http"):
        if had_created and existing:
            lead["site_created_at"] = existing.get("Site Created", "")
        elif not lead.get("site_created_at"):
            lead["site_created_at"] = utc_now_str()

        event = "site_redeployed" if had_live else "site_deployed"
        try:
            append_audit_record(lead, event)
        except Exception as exc:
            print(f"Warning: audit log failed ({exc}); inventory row will still update.", flush=True)

    values = lead_to_row(lead)
    existing_row = row_index.get(key)
    if existing_row:

        def _update_row():
            worksheet.batch_update(
                [{"range": f"A{existing_row}:{LAST_COL}{existing_row}", "values": [values]}],
                value_input_option="USER_ENTERED",
            )

        _with_retry(_update_row, "sync_deploy_lead")
        print(f"Updated deploy fields for {lead.get('name', '')} (row {existing_row})")
    else:

        def _append_row():
            worksheet.append_row(values, value_input_option="USER_ENTERED")

        _with_retry(_append_row, "sync_deploy_lead_append")
        print(f"Appended deploy fields for {lead.get('name', '')}")


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
