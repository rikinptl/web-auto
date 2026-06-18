#!/usr/bin/env python3
"""Output GitHub Actions matrix JSON for all configured niches."""

import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETS_FILE = ROOT / "config" / "markets.json"


def main() -> None:
    markets = json.loads(MARKETS_FILE.read_text(encoding="utf-8"))
    niche_ids = [niche["id"] for niche in markets["niches"]]
    if not niche_ids:
        raise SystemExit("No niches configured in config/markets.json")

    max_total = int(os.environ.get("MAX_RESULTS", "50"))
    # Enough headroom that productive niches can fill the global cap after merge/dedupe.
    per_niche_max = max(5, min(12, math.ceil(max_total / 6)))

    payload = {
        "niche_ids": niche_ids,
        "per_niche_max": per_niche_max,
        "niche_count": len(niche_ids),
    }
    print(json.dumps(payload))

    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(f"niche_ids={json.dumps(niche_ids)}\n")
            fh.write(f"per_niche_max={per_niche_max}\n")
            fh.write(f"niche_count={len(niche_ids)}\n")


if __name__ == "__main__":
    main()
