#!/usr/bin/env python3
"""Merge parallel niche scrape artifacts, dedupe, cap, and upsert to Google Sheet."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from maps_url import place_key, resolve_maps_url  # noqa: E402
from sheets import InventorySkipIndex, load_inventory, normalize_name, normalize_phone, upsert_leads  # noqa: E402

LEADS_FILE = ROOT / "data" / "leads.json"
SCRAPE_DIR = ROOT / "data" / "scrapes"


def collect_scrape_files() -> list[Path]:
    patterns = [
        SCRAPE_DIR.glob("scrape-*.json"),
        SCRAPE_DIR.glob("*/scrape-*.json"),
        (ROOT / "data").glob("scrape-*.json"),
    ]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(pattern)
    return sorted({path.resolve() for path in files if path.is_file()})


def dedupe_and_cap(leads: list[dict], skip_index: InventorySkipIndex, max_total: int) -> list[dict]:
    merged: list[dict] = []
    seen_maps: set[str] = set()
    seen_name_phone: set[tuple[str, str]] = set()

    for lead in leads:
        if len(merged) >= max_total:
            break

        if skip_index.has_lead(lead):
            continue

        maps_key = place_key(resolve_maps_url(lead))
        if maps_key and maps_key in seen_maps:
            continue

        name = normalize_name(lead.get("name", ""))
        phone = normalize_phone(lead.get("phone", ""))
        if name and (name, phone) in seen_name_phone:
            continue

        merged.append(lead)
        if maps_key:
            seen_maps.add(maps_key)
        if name:
            seen_name_phone.add((name, phone))
        skip_index.register_lead(lead)

    return merged


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    max_total = int(os.environ.get("MAX_RESULTS", "50"))
    files = collect_scrape_files()
    if not files:
        raise SystemExit("No scrape-*.json files found to merge")

    raw: list[dict] = []
    for path in files:
        batch = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(batch, list):
            raise SystemExit(f"{path} must contain a JSON array")
        raw.extend(batch)
        print(f"Loaded {len(batch)} lead(s) from {path.name}")

    print(f"Combined {len(raw)} raw lead(s) from {len(files)} file(s)")

    try:
        existing = load_inventory()
        skip_index = InventorySkipIndex(existing)
        print(f"Sheet inventory: {len(existing)} existing lead(s)")
    except Exception as exc:
        print(f"Sheet inventory not loaded (merge without sheet dedupe): {exc}")
        skip_index = InventorySkipIndex([])

    merged = dedupe_and_cap(raw, skip_index, max_total)
    print(f"After dedupe + cap: {len(merged)} lead(s) (max {max_total})")

    LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADS_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")

    if merged:
        try:
            stats = upsert_leads(merged)
            print(
                f"Merged into Google Sheet "
                f"(updated {stats['updated']}, appended {stats['appended']})"
            )
        except Exception as exc:
            raise SystemExit(f"Sheet upsert failed: {exc}") from exc
    elif os.environ.get("REQUIRE_LEADS", "").lower() in {"1", "true", "yes"}:
        raise SystemExit("No qualified leads after merging parallel scrapes")


if __name__ == "__main__":
    main()
