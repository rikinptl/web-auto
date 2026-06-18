#!/usr/bin/env python3
"""Scrape all configured niches in one runner — one Playwright install, parallel contexts."""

import asyncio
import json
import math
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_search import build_search_query, find_niche, load_markets  # noqa: E402
from scrap import (  # noqa: E402
    HEADLESS,
    SLOW_MO,
    scrape_maps_leads,
)
from sheets import InventorySkipIndex, load_inventory  # noqa: E402

NICHE_CONCURRENCY = int(os.environ.get("NICHE_CONCURRENCY", "5"))
MAX_CHECK_LISTINGS = int(os.environ.get("MAX_CHECK_LISTINGS", "60"))


def per_niche_max(max_total: int, niche_count: int) -> int:
    return max(5, min(12, math.ceil(max_total / 6)))


async def scrape_one(
    browser,
    semaphore: asyncio.Semaphore,
    niche_id: str,
    city_id: str,
    per_niche_cap: int,
    skip_index: InventorySkipIndex,
    index_lock: asyncio.Lock,
) -> Path:
    async with semaphore:
        markets = load_markets()
        niche = find_niche(markets, niche_id)
        query = build_search_query(niche_id, city_id)
        out = ROOT / "data" / f"scrape-{niche_id}.json"

        print(f"[{niche_id}] Starting scrape ({query})", flush=True)
        try:
            leads = await scrape_maps_leads(
                search_query=query,
                max_results=per_niche_cap,
                max_check_listings=MAX_CHECK_LISTINGS,
                leads_output=out,
                skip_index=skip_index,
                niche_id=niche_id,
                niche_label=niche["label"],
                skip_sheet_upsert=True,
                require_leads=False,
                browser=browser,
            )
            async with index_lock:
                for lead in leads:
                    skip_index.register_lead(lead)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(leads, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[{niche_id}] Wrote {len(leads)} lead(s) → {out.name}", flush=True)
            return out
        except Exception as exc:
            print(f"[{niche_id}] Scrape failed: {exc}", flush=True)
            out.write_text("[]", encoding="utf-8")
            return out


async def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    city_id = os.environ.get("CITY_ID", load_markets()["default_city"])
    max_total = int(os.environ.get("MAX_RESULTS", "50"))
    markets = load_markets()
    niche_ids = [n["id"] for n in markets["niches"]]
    cap = per_niche_max(max_total, len(niche_ids))

    skip_index: InventorySkipIndex | None = None
    existing_count = 0
    try:
        existing = load_inventory()
        existing_count = len(existing)
        if existing:
            skip_index = InventorySkipIndex(existing)
            print(f"Loaded {existing_count} lead(s) from sheet for dedupe.", flush=True)
    except Exception as exc:
        print(f"Sheet inventory not loaded: {exc}", flush=True)
        skip_index = InventorySkipIndex([])

    print(
        f"Scraping {len(niche_ids)} niches in {city_id} "
        f"(max {cap}/niche, {NICHE_CONCURRENCY} concurrent, one browser install)",
        flush=True,
    )

    semaphore = asyncio.Semaphore(NICHE_CONCURRENCY)
    index_lock = asyncio.Lock()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--window-size=1920,1080",
            ],
        )
        try:
            await asyncio.gather(
                *[
                    scrape_one(browser, semaphore, niche_id, city_id, cap, skip_index, index_lock)
                    for niche_id in niche_ids
                ]
            )
        finally:
            await browser.close()

    print("All niche scrapes finished.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
