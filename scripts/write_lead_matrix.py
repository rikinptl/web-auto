#!/usr/bin/env python3
"""Write GitHub Actions matrix outputs from data/leads.json."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADS_FILE = ROOT / "data" / "leads.json"


def main() -> None:
    if not LEADS_FILE.exists():
        raise SystemExit(f"Missing {LEADS_FILE}")

    leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    if not isinstance(leads, list):
        raise SystemExit("data/leads.json must be a JSON array")

    indices = list(range(len(leads)))
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        print(json.dumps({"lead_indices": indices, "lead_count": len(leads)}))
        return

    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"lead_indices={json.dumps(indices)}\n")
        fh.write(f"lead_count={len(leads)}\n")

    print(f"Deploy matrix: {len(leads)} lead(s) → indices {indices}")


if __name__ == "__main__":
    main()
