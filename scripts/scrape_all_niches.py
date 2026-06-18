#!/usr/bin/env python3
"""Scrape all niches in parallel — stop globally as soon as max_results qualified leads are found."""

import asyncio
import json
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_search import build_search_query, find_niche, load_markets  # noqa: E402
from scrape_pool import GlobalLeadPool  # noqa: E402
from scrap import HEADLESS, SLOW_MO, scrape_maps_leads  # noqa: E402
from sheets import InventorySkipIndex, load_inventory  # noqa: E402

NICHE_CONCURRENCY = int(os.environ.get("NICHE_CONCURRENCY", "5"))
MAX_CHECK_LISTINGS = int(os.environ.get("MAX_CHECK_LISTINGS", "60"))
POOL_OUTPUT = ROOT / "data" / "scrape-pool.json"


async def scrape_one(
    browser,
    semaphore: asyncio.Semaphore,
    niche_id: str,
    city_id: str,
    skip_index: InventorySkipIndex,
    global_pool: GlobalLeadPool,
) -> None:
    async with semaphore:
        if global_pool.should_stop():
            print(f"[{niche_id}] Skipping — global cap already reached", flush=True)
            return

        markets = load_markets()
        niche = find_niche(markets, niche_id)
        query = build_search_query(niche_id, city_id)

        print(f"[{niche_id}] Starting scrape ({query})", flush=True)
        try:
            await scrape_maps_leads(
                search_query=query,
                max_results=global_pool.cap,
                max_check_listings=MAX_CHECK_LISTINGS,
                leads_output=POOL_OUTPUT,
                skip_index=skip_index,
                niche_id=niche_id,
                niche_label=niche["label"],
                skip_sheet_upsert=True,
                require_leads=False,
                browser=browser,
                global_pool=global_pool,
            )
        except Exception as exc:
            print(f"[{niche_id}] Scrape failed: {exc}", flush=True)


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

    global_pool = GlobalLeadPool(max_total, skip_index)

    print(
        f"Scraping {len(niche_ids)} niches in {city_id} "
        f"(global cap {max_total}, {NICHE_CONCURRENCY} concurrent, early stop at cap)",
        flush=True,
    )

    semaphore = asyncio.Semaphore(NICHE_CONCURRENCY)

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
            tasks = [
                scrape_one(browser, semaphore, niche_id, city_id, skip_index, global_pool)
                for niche_id in niche_ids
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await browser.close()

    leads = global_pool.leads[:max_total]
    POOL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    POOL_OUTPUT.write_text(json.dumps(leads, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Finished — {len(leads)} qualified lead(s) (global cap {max_total}). Wrote {POOL_OUTPUT.name}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
