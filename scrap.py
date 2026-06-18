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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
        page.set_default_timeout(30000)

        search_url = f"https://www.google.com/maps/search/{quote_plus(SEARCH_QUERY)}"
        print(f"Opening Maps search: {SEARCH_QUERY}")
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
        # Get all listing elements (they are 'article' roles inside the feed)
        listing_elements = await page.locator('div[role="article"]').all()
        print(f"Found {len(listing_elements)} total listings. Processing up to {MAX_RESULTS}...")

        leads = []  # Will hold only no‑website businesses
        processed = 0

        for idx, listing in enumerate(listing_elements):
            if processed >= MAX_RESULTS:
                break
            try:
                # Click the listing to open the details panel on the right
                await listing.click()
                await asyncio.sleep(random.uniform(1.0, 2.5))

                try:
                    await page.wait_for_url(re.compile(r"/maps/place/"), timeout=8000)
                except PlaywrightTimeoutError:
                    pass

                # Wait for the details panel to appear
                panel = page.locator('div[role="main"] div[role="feed"]')  # sometimes the panel is a feed too
                # Actually the info panel is often a div with class "m6QErb DxyBCb kA9KIf dS8AEf" but we'll use a more robust locator
                # The detail panel contains the business name at the top
                # We'll wait for a heading element
                await page.wait_for_selector('h1.fontHeadlineLarge', timeout=5000)

                # ---------- EXTRACT WEBSITE ----------
                website = None
                # Look for a link that looks like a website
                website_link = page.locator('a[href*="http"]:has-text("Website")')
                if await website_link.count() > 0:
                    website = await website_link.get_attribute("href")
                else:
                    # Some listings have a globe icon with a link; try alternative selector
                    website_link = page.locator('a.CsEnBe')  # common class for website link
                    if await website_link.count() > 0:
                        website = await website_link.get_attribute("href")
                    else:
                        # Sometimes the website is inside a button or plain text; we can search for any anchor with href
                        anchors = page.locator('a[href^="http"]')
                        for anchor in await anchors.all():
                            href = await anchor.get_attribute("href")
                            if href and "google.com" not in href and "maps.google" not in href:
                                # likely a real website
                                website = href
                                break

                # If website exists, skip this listing
                if website:
                    print(f"Skipping {idx+1}: has website {website}")
                    continue

                # ---------- EXTRACT OTHER FIELDS (only for no‑website) ----------
                # Business Name
                name_elem = page.locator('h1.fontHeadlineLarge')
                name = await name_elem.text_content() if await name_elem.count() > 0 else None
                name = name.strip() if name else None

                # Category / Niche
                category_elem = page.locator('button[aria-label*="Category"]')  # often appears as a button
                if await category_elem.count() == 0:
                    category_elem = page.locator('div.fontBodyMedium span:first-child')  # fallback
                category = await category_elem.text_content() if await category_elem.count() > 0 else None
                category = category.strip() if category else None

                # Phone
                phone_elem = page.locator('button[data-item-id="phone"]')
                if await phone_elem.count() == 0:
                    phone_elem = page.locator('a[href^="tel:"]')
                phone = await phone_elem.text_content() if await phone_elem.count() > 0 else None
                phone = phone.strip() if phone else None

                # Address
                address_elem = page.locator('button[data-item-id="address"]')
                if await address_elem.count() == 0:
                    address_elem = page.locator('div[data-item-id="address"]')
                address = await address_elem.text_content() if await address_elem.count() > 0 else None
                address = address.strip() if address else None

                # Rating & Reviews
                rating_elem = page.locator('span[aria-hidden="true"]:has-text("★")')
                rating = None
                reviews = None
                if await rating_elem.count() > 0:
                    rating_text = await rating_elem.text_content()
                    if rating_text:
                        # e.g., "4.5" or "4.5 ★ (123)"
                        match = re.search(r'([\d.]+)\s*★', rating_text)
                        if match:
                            rating = float(match.group(1))
                        # Reviews count: often next to stars
                        reviews_span = page.locator('span[aria-label*="reviews"]')
                        if await reviews_span.count() > 0:
                            rev_text = await reviews_span.text_content()
                            if rev_text:
                                rev_match = re.search(r'[\d,]+', rev_text)
                                if rev_match:
                                    reviews = int(rev_match.group().replace(',', ''))

                # Build lead object
                lead = {
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
                lead["google_maps_url"] = resolve_maps_url(lead)
                leads.append(lead)
                processed += 1
                print(f"✅ Added no‑website lead #{processed}: {name}")

            except Exception as e:
                print(f"⚠️ Error processing listing {idx+1}: {e}")
                continue

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