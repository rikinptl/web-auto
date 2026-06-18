#!/usr/bin/env python3
"""Write sheet rows that still need sites into data/leads.json for deploy matrix."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sheets import load_pending_deploy_leads  # noqa: E402

LEADS_FILE = ROOT / "data" / "leads.json"


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    pending = load_pending_deploy_leads()
    if not pending:
        raise SystemExit("No pending leads in sheet (all rows have copy Done + live URL).")

    LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADS_FILE.write_text(json.dumps(pending, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(pending)} pending lead(s) from Google Sheet → {LEADS_FILE}")


if __name__ == "__main__":
    main()
