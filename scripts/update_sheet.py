#!/usr/bin/env python3
"""Sync lead status fields to the Google Sheet inventory + audit log."""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sheets import sync_deploy_lead  # noqa: E402


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

    # Stagger parallel matrix jobs to avoid Sheets read bursts (60 reads/min limit).
    lead_index = int(os.environ.get("LEAD_INDEX", "0"))
    time.sleep(lead_index * 3)

    lead = load_lead()
    if os.environ.get("COPY_STATUS"):
        lead["copy_status"] = os.environ["COPY_STATUS"]
    if os.environ.get("LIVE_URL"):
        lead["live_url"] = os.environ["LIVE_URL"]

    sync_deploy_lead(lead)


if __name__ == "__main__":
    main()
