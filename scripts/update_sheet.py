#!/usr/bin/env python3
"""Sync lead status fields to the Google Sheet inventory."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sheets import upsert_lead  # noqa: E402


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
    if os.environ.get("COPY_STATUS"):
        lead["copy_status"] = os.environ["COPY_STATUS"]
    if os.environ.get("LIVE_URL"):
        lead["live_url"] = os.environ["LIVE_URL"]
    if os.environ.get("DEPLOY_DURATION_SEC"):
        lead["deploy_duration_sec"] = os.environ["DEPLOY_DURATION_SEC"]

    upsert_lead(lead)


if __name__ == "__main__":
    main()
