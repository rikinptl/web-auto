#!/usr/bin/env python3
"""Process sheet rows marked Decline=Y: delete kem-llc repo, clear live URL, highlight cell."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from delete_org_site import repo_slug_from_live_url, try_delete_org_repo  # noqa: E402
from deploy_org_site import repo_slug_for_lead  # noqa: E402
from sheets import (  # noqa: E402
    HEADERS,
    LAST_COL,
    _get_all_records,
    _inventory_index,
    _merge_existing_fields,
    _with_retry,
    append_audit_record,
    ensure_headers,
    get_worksheet,
    highlight_decline_cells,
    lead_to_row,
    record_to_lead,
)


def _header_indices(header_row: list[str], name: str) -> list[int]:
    target = name.strip().lower()
    return [i for i, header in enumerate(header_row) if str(header).strip().lower() == target]


def _cell(raw_row: list[str], index: int) -> str:
    if index < 0 or index >= len(raw_row):
        return ""
    return str(raw_row[index]).strip()


def _row_decline_info(header_row: list[str], raw_row: list[str]) -> tuple[bool, list[int]]:
    decline_cols = _header_indices(header_row, "Decline")
    matched = [idx for idx in decline_cols if _cell(raw_row, idx).upper() == "Y"]
    if matched:
        return True, matched

    decline_values = [_cell(raw_row, idx) for idx in decline_cols]
    if decline_cols and any(decline_values):
        return False, []

    # Out-of-band Y when Decline column(s) are empty (shifted manual sheets).
    last_named = max((i for i, header in enumerate(header_row) if str(header).strip()), default=-1)
    for idx in range(last_named + 1, len(raw_row)):
        if _cell(raw_row, idx).upper() == "Y":
            matched.append(idx)

    return bool(matched), matched


def _lead_from_raw_row(header_row: list[str], raw_row: list[str]) -> dict:
    row_dict: dict[str, str] = {}
    for i, header in enumerate(header_row):
        if not str(header).strip():
            continue
        row_dict[header] = _cell(raw_row, i)
    lead = record_to_lead(row_dict)
    declined, _ = _row_decline_info(header_row, raw_row)
    if declined:
        lead["decline"] = "Y"
    live_cols = _header_indices(header_row, "Live URL")
    if live_cols:
        lead["live_url"] = _cell(raw_row, live_cols[0])
    return lead


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
    row_index, existing_by_key = _inventory_index(records)

    stats = {"checked": 0, "deleted": 0, "skipped": 0, "errors": 0}
    highlight_rows: list[int] = []
    highlight_cols: set[int] = set()
    batch_updates = []

    for offset, raw_row in enumerate(all_values[1:], start=2):
        lead = _lead_from_raw_row(header_row, raw_row)
        declined, decline_cols = _row_decline_info(header_row, raw_row)
        if not lead.get("name") or not declined:
            continue

        stats["checked"] += 1
        key = (lead.get("name", ""), lead.get("phone", ""))
        row_num = row_index.get(key, offset)
        highlight_rows.append(row_num)
        highlight_cols.update(decline_cols)

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

            existing = existing_by_key.get(key, {})
            updated = _merge_existing_fields({**lead, "live_url": ""}, existing)
            updated["decline"] = "Y"
            batch_updates.append(
                {"range": f"A{row_num}:{LAST_COL}{row_num}", "values": [lead_to_row(updated)]}
            )

            try:
                append_audit_record(updated, "site_removed_declined", notes="Decline=Y in sheet")
            except Exception as exc:
                print(f"Warning: audit log failed for {lead['name']}: {exc}", flush=True)
        else:
            print(f"Declined (no live URL to delete) — {lead['name']}", flush=True)

    if batch_updates:

        def _batch_update():
            worksheet.batch_update(batch_updates, value_input_option="USER_ENTERED")

        _with_retry(_batch_update, "process_declines_update")
        print(f"Cleared Live URL on {len(batch_updates)} declined row(s)", flush=True)

    highlight_decline_cells(worksheet, highlight_rows, sorted(highlight_cols))
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
