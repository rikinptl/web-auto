#!/usr/bin/env python3
"""
Google Maps Lead Scraper - B2B No-Website Filter

This script uses Playwright (async) to scrape Google Maps for local service businesses
and extracts only those that do NOT have a website listed. It saves the filtered leads
to 'no_website_leads.json'.

Usage:
    python google_maps_scraper.py

Configuration:
    - SEARCH_QUERY:    The business type and location (e.g., "plumber near Chicago")
    - MAX_RESULTS:     Maximum number of listings to process (stops scrolling after this)
    - HEADLESS:        Set to False to watch the browser (helps debugging)
"""

import asyncio
import json
import os
import random
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from maps_url import resolve_maps_url  # noqa: E402
from sheets import replace_inventory  # noqa: E402

# ==================== CONFIGURATION ====================
SEARCH_QUERY = os.environ.get("SEARCH_QUERY", "plumber near Dallas, TX")
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "50"))
HEADLESS = os.environ.get("HEADLESS", "false").lower() in {"1", "true", "yes"}
SLOW_MO = int(os.environ.get("SLOW_MO", "100"))
NAV_TIMEOUT_MS = int(os.environ.get("NAV_TIMEOUT_MS", "60000"))


async def dismiss_consent(page) -> None:
    for label in ("Accept all", "Reject all", "I agree"):
        try:
            await page.get_by_role("button", name=label).click(timeout=3000)
            await asyncio.sleep(0.5)
            return
        except PlaywrightTimeoutError:
            continue


async def wait_for_results(page) -> None:
    """Wait for Maps results without networkidle (Maps never goes idle in CI)."""
    selectors = [
        'div[role="feed"] div[role="article"]',
        'div[role="feed"]',
        'div[role="article"]',
    ]
    last_error = None
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=NAV_TIMEOUT_MS)
            return
        except PlaywrightTimeoutError as exc:
            last_error = exc
    raise last_error or PlaywrightTimeoutError("Maps results did not load")


def maps_url_with_lang(url: str) -> str:
    if "hl=" in url:
        return url
    return f"{url}{'&' if '?' in url else '?'}hl=en"


def aria_value(aria: str | None, prefix: str) -> str | None:
    if not aria or prefix not in aria:
        return None
    value = aria.split(prefix, 1)[1].strip()
    return value or None


def is_google_url(href: str) -> bool:
    return any(
        token in href
        for token in ("google.com", "maps.google", "gstatic.com", "googleusercontent")
    )


async def wait_for_place_panel(page) -> None:
    selectors = [
        'button[data-item-id="address"]',
        'button[aria-label^="Address:"]',
        'div[role="main"] h1',
        "h1",
    ]
    last_error = None
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=15000)
            return
        except PlaywrightTimeoutError as exc:
            last_error = exc
    raise last_error or PlaywrightTimeoutError("Place panel did not load")


async def collect_place_urls(page, limit: int) -> list[tuple[str, str]]:
    articles = page.locator('div[role="feed"] div[role="article"]')
    count = await articles.count()
    places: list[tuple[str, str]] = []
    seen: set[str] = set()

    for i in range(count):
        if len(places) >= limit:
            break
        link = articles.nth(i).locator('a[href*="/maps/place/"]').first
        if await link.count() == 0:
            continue
        href = await link.get_attribute("href")
        if not href or href in seen:
            continue
        seen.add(href)
        label = (await link.get_attribute("aria-label")) or ""
        places.append((href, label))

    return places


async def extract_website(page) -> str | None:
    selectors = [
        'a[data-item-id="authority"]',
        'a[aria-label^="Website:"]',
        'button[aria-label^="Website:"]',
    ]
    for selector in selectors:
        loc = page.locator(selector).first
        if await loc.count() == 0:
            continue
        href = await loc.get_attribute("href")
        if href and not is_google_url(href):
            return href
        aria = await loc.get_attribute("aria-label")
        website = aria_value(aria, "Website:")
        if website and not website.startswith("http"):
            website = f"https://{website.lstrip('/')}"
        if website:
            return website
    return None


async def extract_text(locator) -> str | None:
    if await locator.count() == 0:
        return None
    text = await locator.text_content()
    return text.strip() if text else None


async def extract_place_details(page, list_label: str) -> dict:
    name = await extract_text(page.locator('div[role="main"] h1').first)
    if not name:
        name = await extract_text(page.locator("h1").first)
    if not name and list_label:
        name = list_label.split("·", 1)[0].strip()

    category = await extract_text(
        page.locator('button[jsaction*="category"], button[aria-label^="Category:"]').first
    )
    if not category:
        category = await extract_text(page.locator("button.DkEaL").first)

    phone_loc = page.locator('button[data-item-id="phone"], button[aria-label^="Phone:"]').first
    phone = await extract_text(phone_loc)
    if not phone:
        phone = aria_value(await phone_loc.get_attribute("aria-label"), "Phone:")

    address_loc = page.locator(
        'button[data-item-id="address"], button[aria-label^="Address:"]'
    ).first
    address = await extract_text(address_loc)
    if not address:
        address = aria_value(await address_loc.get_attribute("aria-label"), "Address:")

    rating = None
    reviews = None
    stars = page.locator('div[role="main"] span[aria-label*="stars"]').first
    if await stars.count() > 0:
        aria = await stars.get_attribute("aria-label") or ""
        rating_match = re.search(r"([\d.]+)\s*stars?", aria, re.I)
        if rating_match:
            rating = float(rating_match.group(1))
        reviews_match = re.search(r"([\d,]+)\s*reviews?", aria, re.I)
        if reviews_match:
            reviews = int(reviews_match.group(1).replace(",", ""))

    return {
        "name": name,
        "niche": category,
        "category": category,
        "phone": phone,
        "address": address,
        "city": parse_city_from_address(address),
        "rating": rating,
        "reviews": reviews,
        "website": None,
        "google_maps_url": page.url if "google.com/maps" in page.url else "",
        "scraped_status": "Done",
        "copy_status": "Pending",
        "live_url": "",
    }


# ==================== MAIN SCRAPER ====================

def parse_city_from_address(address: str | None) -> str | None:
    if not address:
        return None
    parts = [part.strip() for part in address.split(",")]
    if len(parts) >= 3:
        state = parts[2].split()[0]
        return f"{parts[1]}, {state}"
    if len(parts) == 2:
        return parts[1]
    return None


async def scrape_google_maps():
    """Main entry point: launches browser, performs search, filters no‑website leads."""
    async with async_playwright() as p:
        # Launch browser with anti‑detection tweaks
        browser = await p.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--window-size=1920,1080"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        page.set_default_timeout(30000)

        search_url = f"https://www.google.com/maps/search/{quote_plus(SEARCH_QUERY)}?hl=en"
        print(f"Opening Maps search: {SEARCH_QUERY}", flush=True)
        await page.goto(search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)

        await dismiss_consent(page)
        await wait_for_results(page)
        await asyncio.sleep(random.uniform(1.5, 2.5))

        # ---------- INFINITE SCROLL ----------
        # Locate the scrollable container (the feed panel)
        feed_container = page.locator('div[role="feed"]')
        # The actual scrollable element is a parent with overflow scroll; find it.
        scrollable = page.locator(
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf, '  # old class pattern
            'div[role="feed"] >> xpath=ancestor::div[contains(@style, "overflow")]'
        )
        # Fallback: locate by checking for scrollHeight
        if await scrollable.count() == 0:
            # Try to find any scrollable div inside the feed
            scrollable = page.locator(
                'div[role="feed"] >> xpath=ancestor::div[@style and contains(@style, "overflow-y")]'
            )

        # If still not found, use the body (less ideal)
        if await scrollable.count() == 0:
            scrollable = page.locator('body')

        # Scroll until we reach the bottom or MAX_RESULTS
        processed_count = 0
        last_height = 0
        no_new_items_attempts = 0

        while processed_count < MAX_RESULTS:
            # Get current scroll height
            current_height = await scrollable.evaluate("el => el.scrollHeight")
            # Scroll to bottom
            await scrollable.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            # Wait for new items to load
            await asyncio.sleep(random.uniform(2, 4))
            # Count current visible listings (approximate)
            listings = page.locator('div[role="article"]')
            count = await listings.count()
            if count > processed_count:
                processed_count = count
                no_new_items_attempts = 0
            else:
                no_new_items_attempts += 1
                if no_new_items_attempts >= 3:
                    break  # no more items loading
            # If scroll height didn't increase, we might be at the end
            new_height = await scrollable.evaluate("el => el.scrollHeight")
            if new_height == last_height and no_new_items_attempts > 1:
                break
            last_height = new_height

        # ---------- EXTRACT DATA FROM EACH LISTING ----------
        # Visit place URLs directly — clicking cards is unreliable in headless CI.
        place_urls = await collect_place_urls(page, MAX_RESULTS * 4)
        print(
            f"Found {len(place_urls)} place URLs. Looking for up to {MAX_RESULTS} no-website leads...",
            flush=True,
        )

        leads = []
        processed = 0
        checked = 0

        for idx, (place_url, list_label) in enumerate(place_urls):
            if processed >= MAX_RESULTS:
                break
            checked += 1
            try:
                await page.goto(
                    maps_url_with_lang(place_url),
                    wait_until="domcontentloaded",
                    timeout=NAV_TIMEOUT_MS,
                )
                await dismiss_consent(page)
                await wait_for_place_panel(page)
                await asyncio.sleep(random.uniform(0.8, 1.5))

                website = await extract_website(page)
                if website:
                    print(f"Skipping {idx + 1}: has website {website}", flush=True)
                    continue

                lead = await extract_place_details(page, list_label)
                lead["google_maps_url"] = resolve_maps_url(lead)
                leads.append(lead)
                processed += 1
                print(f"Added no-website lead #{processed}: {lead['name']}", flush=True)

            except Exception as e:
                print(f"Error processing listing {idx + 1}: {e}", flush=True)
                continue

        if checked == 0:
            print("No place URLs found in search results.", flush=True)

        # ---------- SAVE RESULTS ----------
        root = Path(__file__).resolve().parent
        output_file = root / "no_website_leads.json"
        leads_file = root / "data" / "leads.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Done! Found {len(leads)} leads without a website. Saved to {output_file.name}")

        if leads:
            leads_file.parent.mkdir(parents=True, exist_ok=True)
            leads_file.write_text(json.dumps(leads, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Wrote {leads_file.relative_to(root)} for site generation")

            try:
                from dotenv import load_dotenv

                load_dotenv(root / ".env")
                replace_inventory(leads)
                print("Synced scraped leads to Google Sheet (full inventory replace)")
            except Exception as exc:
                print(f"Sheet sync skipped: {exc}")
        elif os.environ.get("REQUIRE_LEADS", "").lower() in {"1", "true", "yes"}:
            raise SystemExit("No no-website leads found — pipeline stopped.")

        await browser.close()


# ==================== RUN ====================
if __name__ == "__main__":
    asyncio.run(scrape_google_maps())