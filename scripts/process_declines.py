#!/usr/bin/env python3
"""Process sheet rows marked Decline=Y: delete kem-llc repo, clear live URL, highlight row."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from delete_org_site import repo_slug_from_live_url, try_delete_org_repo  # noqa: E402
from deploy_org_site import repo_slug_for_lead  # noqa: E402
from sheets import (  # noqa: E402
    _get_all_records,
    _inventory_index,
    _with_retry,
    append_audit_record,
    ensure_headers,
    get_worksheet,
    highlight_declined_rows,
    record_to_lead,
)


def _header_indices(header_row: list[str], name: str) -> list[int]:
    target = name.strip().lower()
    return [i for i, header in enumerate(header_row) if str(header).strip().lower() == target]


def _cell(raw_row: list[str], index: int) -> str:
    if index < 0 or index >= len(raw_row):
        return ""
    return str(raw_row[index]).strip()


def _is_declined_row(header_row: list[str], raw_row: list[str]) -> bool:
    """True only when the Decline column itself is Y."""
    for idx in _header_indices(header_row, "Decline"):
        if _cell(raw_row, idx).upper() == "Y":
            return True
    return False


def _lead_from_raw_row(header_row: list[str], raw_row: list[str]) -> dict:
    row_dict: dict[str, str] = {}
    for i, header in enumerate(header_row):
        if not str(header).strip():
            continue
        row_dict[header] = _cell(raw_row, i)
    lead = record_to_lead(row_dict)
    live_cols = _header_indices(header_row, "Live URL")
    if live_cols:
        lead["live_url"] = _cell(raw_row, live_cols[0])
    return lead


def _col_letter(index: int) -> str:
    return chr(ord("A") + index)


def _repo_slug_for_row(lead: dict, org: str) -> str | None:
    live_url = (lead.get("live_url") or "").strip()
    if live_url.startswith("http"):
        try:
            return repo_slug_from_live_url(live_url, org)
        except SystemExit:
            pass
    slug = repo_slug_for_lead(lead)
    return slug or None


def process_declines() -> dict[str, int]:
    org = os.environ.get("DEPLOY_ORG", os.environ.get("GITHUB_ORG", "kem-llc"))
    token = os.environ.get("ORG_DEPLOY_TOKEN") or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("ORG_DEPLOY_TOKEN (or GH_TOKEN) is not set")

    worksheet = get_worksheet()
    ensure_headers(worksheet)
    all_values = _with_retry(worksheet.get_all_values, "get_all_values")
    if not all_values:
        return {"checked": 0, "deleted": 0, "skipped": 0, "errors": 0}

    header_row = all_values[0]
    records = _with_retry(lambda: _get_all_records(worksheet), "get_all_records")
    row_index, _existing_by_key = _inventory_index(records)
    live_url_cols = _header_indices(header_row, "Live URL")

    stats = {"checked": 0, "deleted": 0, "skipped": 0, "errors": 0}
    highlight_rows: list[int] = []
    live_url_clears: list[dict] = []

    for offset, raw_row in enumerate(all_values[1:], start=2):
        if not _is_declined_row(header_row, raw_row):
            continue

        lead = _lead_from_raw_row(header_row, raw_row)
        if not lead.get("name"):
            continue

        stats["checked"] += 1
        key = (lead.get("name", ""), lead.get("phone", ""))
        row_num = row_index.get(key, offset)
        highlight_rows.append(row_num)

        live_url = (lead.get("live_url") or "").strip()
        if live_url.startswith("http"):
            repo_slug = _repo_slug_for_row(lead, org)
            if repo_slug:
                deleted, status = try_delete_org_repo(org, repo_slug, token)
                if deleted:
                    stats["deleted"] += 1
                    print(f"Deleted {org}/{repo_slug} — {lead['name']}", flush=True)
                elif status == "not_found":
                    print(f"Repo already gone: {org}/{repo_slug} — {lead['name']}", flush=True)
                else:
                    stats["errors"] += 1
                    print(f"Warning: could not delete {org}/{repo_slug}: {status}", flush=True)
            else:
                stats["skipped"] += 1
                print(f"No repo slug for declined row — {lead['name']}", flush=True)

            if live_url_cols:
                col = _col_letter(live_url_cols[0])
                live_url_clears.append({"range": f"{col}{row_num}", "values": [[""]]})

            try:
                append_audit_record(
                    {**lead, "live_url": ""},
                    "site_removed_declined",
                    notes="Decline=Y in sheet",
                )
            except Exception as exc:
                print(f"Warning: audit log failed for {lead['name']}: {exc}", flush=True)
        else:
            print(f"Declined (no live URL) — {lead['name']}", flush=True)

    if live_url_clears:

        def _clear_live_urls():
            worksheet.batch_update(live_url_clears, value_input_option="USER_ENTERED")

        _with_retry(_clear_live_urls, "clear_declined_live_urls")
        print(f"Cleared Live URL on {len(live_url_clears)} declined row(s)", flush=True)

    highlight_declined_rows(worksheet, highlight_rows)
    return stats


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    stats = process_declines()
    print(
        f"Declines processed: {stats['checked']} row(s), "
        f"{stats['deleted']} repo(s) deleted, "
        f"{stats['skipped']} without slug, "
        f"{stats['errors']} error(s)",
        flush=True,
    )


if __name__ == "__main__":
    main()
