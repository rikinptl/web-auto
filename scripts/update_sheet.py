#!/usr/bin/env python3
"""Sync lead status fields to the Google Sheet inventory + audit log."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sheets import append_audit_record, find_lead_in_inventory, upsert_lead, utc_now_str  # noqa: E402


def load_lead() -> dict:
    import json

    leads = json.loads((ROOT / "data" / "leads.json").read_text(encoding="utf-8"))
    index = int(os.environ.get("LEAD_INDEX", "0"))
    return leads[index]


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    lead = load_lead()
    existing = find_lead_in_inventory(lead.get("name", ""), lead.get("phone", ""))
    had_live = bool((existing or {}).get("Live URL", "").strip().startswith("http"))
    had_created = bool((existing or {}).get("Site Created", "").strip())

    if os.environ.get("COPY_STATUS"):
        lead["copy_status"] = os.environ["COPY_STATUS"]
    if os.environ.get("LIVE_URL"):
        lead["live_url"] = os.environ["LIVE_URL"]
    if os.environ.get("DEPLOY_DURATION_SEC"):
        lead["deploy_duration_sec"] = os.environ["DEPLOY_DURATION_SEC"]

    if lead.get("live_url", "").strip().startswith("http"):
        if had_created and existing:
            lead["site_created_at"] = existing.get("Site Created", "")
        elif not lead.get("site_created_at"):
            lead["site_created_at"] = utc_now_str()

        event = "site_redeployed" if had_live else "site_deployed"
        append_audit_record(lead, event)

    upsert_lead(lead)


if __name__ == "__main__":
    main()
