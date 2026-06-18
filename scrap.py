#!/usr/bin/env python3
"""
Google Maps Lead Scraper - B2B No-Website Filter

Scrolls Maps results in batches, quickly checks each place for a website,
and fully extracts only businesses without one. Keeps scrolling until
MAX_RESULTS qualified leads are found or MAX_CHECK_LISTINGS is reached.

Configuration (env):
    SEARCH_QUERY         Business type + location
    MAX_RESULTS          Target count of no-website leads to collect
    MAX_CHECK_LISTINGS   Max listings to inspect before giving up (default 80)
    HEADLESS             true/false
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
from sheets import InventorySkipIndex, load_inventory, upsert_leads  # noqa: E402
from text_clean import clean_phone, strip_icon_glyphs  # noqa: E402

# ==================== CONFIGURATION ====================
SEARCH_QUERY = os.environ.get("SEARCH_QUERY", "plumber near Dallas, TX")
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "50"))
MAX_CHECK_LISTINGS = int(
    os.environ.get(
        "MAX_CHECK_LISTINGS",
        os.environ.get("MAX_SCROLL_LISTINGS", str(max(80, MAX_RESULTS * 15))),
    )
)
HEADLESS = os.environ.get("HEADLESS", "false").lower() in {"1", "true", "yes"}
SLOW_MO = int(os.environ.get("SLOW_MO", "100"))
SKIP_SHEET_UPSERT = os.environ.get("SKIP_SHEET_UPSERT", "").lower() in {"1", "true", "yes"}
NAV_TIMEOUT_MS = int(os.environ.get("NAV_TIMEOUT_MS", "60000"))
QUICK_CHECK_TIMEOUT_MS = int(os.environ.get("QUICK_CHECK_TIMEOUT_MS", "10000"))
MAX_REVIEW_SNIPPETS = int(os.environ.get("MAX_REVIEW_SNIPPETS", "8"))
REVIEW_SCRAPE_TIMEOUT_SEC = float(os.environ.get("REVIEW_SCRAPE_TIMEOUT_SEC", "12"))
SKIP_REVIEW_SCRAPE = os.environ.get("SKIP_REVIEW_SCRAPE", "").lower() in {"1", "true", "yes"}


async def dismiss_consent(page) -> None:
    for label in ("Accept all", "Reject all", "I agree"):
        try:
            await page.get_by_role("button", name=label).click(timeout=3000)
            await asyncio.sleep(0.5)
            return
        except PlaywrightTimeoutError:
            continue


async def wait_for_results(page) -> None:
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
    cleaned = strip_icon_glyphs(value)
    return cleaned or None


def is_google_url(href: str) -> bool:
    return any(
        token in href
        for token in ("google.com", "maps.google", "gstatic.com", "googleusercontent")
    )


async def get_scrollable(page):
    scrollable = page.locator('div[role="feed"]')
    if await scrollable.count() == 0:
        scrollable = page.locator(
            'div.m6QErb.DxyBCb.kA9KIf.dS8AEf, '
            'div[role="feed"] >> xpath=ancestor::div[contains(@style, "overflow")]'
        )
    if await scrollable.count() == 0:
        scrollable = page.locator("body")
    return scrollable


async def scroll_feed(page, scrollable) -> int:
    """Scroll the results feed once. Returns new listing count after scroll."""
    before = await page.locator('div[role="feed"] div[role="article"]').count()
    await scrollable.evaluate("el => el.scrollTo(0, el.scrollHeight)")
    await asyncio.sleep(random.uniform(1.2, 2.0))
    return await page.locator('div[role="feed"] div[role="article"]').count() - before


async def collect_new_place_urls(
    page,
    seen: set[str],
    limit: int,
    skip_index: InventorySkipIndex | None = None,
) -> list[tuple[str, str]]:
    articles = page.locator('div[role="feed"] div[role="article"]')
    count = await articles.count()
    places: list[tuple[str, str]] = []

    for i in range(count):
        if len(places) >= limit:
            break
        link = articles.nth(i).locator('a[href*="/maps/place/"]').first
        if await link.count() == 0:
            continue
        href = await link.get_attribute("href")
        if not href or href in seen:
            continue
        if skip_index and skip_index.has_maps_url(href):
            seen.add(href)
            continue
        label = (await link.get_attribute("aria-label")) or ""
        places.append((href, label))

    return places


async def wait_for_place_panel(page, timeout_ms: int = 15000) -> None:
    selectors = [
        'button[data-item-id="address"]',
        'button[aria-label^="Address:"]',
        'div[role="main"] h1',
        "h1",
    ]
    last_error = None
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=timeout_ms)
            return
        except PlaywrightTimeoutError as exc:
            last_error = exc
    raise last_error or PlaywrightTimeoutError("Place panel did not load")


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


async def quick_website_check(detail_page, place_url: str) -> str | None:
    await detail_page.goto(
        maps_url_with_lang(place_url),
        wait_until="domcontentloaded",
        timeout=NAV_TIMEOUT_MS,
    )
    await dismiss_consent(detail_page)
    try:
        await detail_page.wait_for_selector(
            'a[data-item-id="authority"], a[aria-label^="Website:"], '
            'button[aria-label^="Website:"], h1',
            timeout=QUICK_CHECK_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        pass
    return await extract_website(detail_page)


async def extract_text(locator) -> str | None:
    if await locator.count() == 0:
        return None
    text = await locator.text_content()
    return strip_icon_glyphs(text.strip() if text else None)


def normalize_review_snippet(text: str) -> str:
    text = strip_icon_glyphs(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def scrape_review_snippets(page, max_snippets: int = MAX_REVIEW_SNIPPETS) -> list[str]:
    """Collect recent Google Maps review text for downstream copy personalization."""
    snippets: list[str] = []
    seen: set[str] = set()

    tab_selectors = [
        'button[role="tab"][aria-label*="Reviews"]',
        'button[aria-label*="reviews"][role="tab"]',
        'button[jsaction*="review"][aria-label*="review"]',
    ]
    for selector in tab_selectors:
        tab = page.locator(selector).first
        if await tab.count() == 0:
            continue
        try:
            await tab.click(timeout=4000)
            await asyncio.sleep(0.6)
            break
        except Exception:
            continue

    review_link = page.locator(
        'button[jsaction*="review"], button[aria-label*=" reviews"]'
    ).first
    if await review_link.count() > 0:
        try:
            await review_link.click(timeout=3000)
            await asyncio.sleep(0.5)
        except Exception:
            pass

    scrollable_selectors = [
        'div[role="main"] div.m6QErb[aria-label*="Reviews"]',
        'div[role="main"] div.m6QErb.DxyBCb',
        'div[role="main"] div.m6QErb',
    ]
    scrollable = None
    for selector in scrollable_selectors:
        loc = page.locator(selector).first
        if await loc.count() > 0:
            scrollable = loc
            break

    text_selectors = [
        "span.wiI7pd",
        "div.MyEned span",
        '[data-review-id] span[lang]',
    ]

    for _ in range(5):
        for selector in text_selectors:
            locs = page.locator(selector)
            count = await locs.count()
            for i in range(count):
                if len(snippets) >= max_snippets:
                    break
                raw = await locs.nth(i).text_content()
                text = normalize_review_snippet(raw or "")
                if len(text) < 25 or len(text) > 500:
                    continue
                if text.lower().startswith("response from the owner"):
                    continue
                key = text.lower()[:100]
                if key in seen:
                    continue
                seen.add(key)
                snippets.append(text)
            if len(snippets) >= max_snippets:
                break

        if len(snippets) >= max_snippets or scrollable is None:
            break

        try:
            await scrollable.evaluate("el => { el.scrollTop += 500; }")
            await asyncio.sleep(0.45)
        except Exception:
            break

    return snippets[:max_snippets]


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

    review_snippets: list[str] = []
    if not SKIP_REVIEW_SCRAPE and (reviews or 0) > 0:
        try:
            review_snippets = await asyncio.wait_for(
                scrape_review_snippets(page),
                timeout=REVIEW_SCRAPE_TIMEOUT_SEC,
            )
        except Exception:
            review_snippets = []

    return {
        "name": name,
        "niche": category,
        "category": category,
        "phone": clean_phone(phone),
        "address": address,
        "city": parse_city_from_address(address),
        "rating": rating,
        "reviews": reviews,
        "review_snippets": review_snippets,
        "website": None,
        "google_maps_url": page.url if "google.com/maps" in page.url else "",
        "scraped_status": "Done",
        "copy_status": "Pending",
        "live_url": "",
    }


def apply_niche_tag(lead: dict, niche_id: str = "", niche_label: str = "") -> None:
    """Tag lead with configured niche when scraping in parallel batch mode."""
    if niche_label:
        lead["niche"] = niche_label
    if niche_id:
        lead["niche_id"] = niche_id


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


async def process_batch(
    detail_page,
    batch: list[tuple[str, str]],
    seen: set[str],
    leads: list[dict],
    checked: int,
    skip_index: InventorySkipIndex | None = None,
    niche_id: str = "",
    niche_label: str = "",
    global_pool=None,
    max_results: int = 50,
    max_check_listings: int = 80,
) -> int:
    """Check a batch of places. Returns updated checked count."""
    if global_pool and global_pool.should_stop():
        return checked

    with_website = 0
    in_inventory = 0
    qualified = 0
    prefix = f"[{niche_id}] " if niche_id else ""

    for place_url, list_label in batch:
        if global_pool and global_pool.should_stop():
            break
        if not global_pool and len(leads) >= max_results:
            break
        if checked >= max_check_listings:
            break

        seen.add(place_url)
        checked += 1

        if skip_index and skip_index.has_maps_url(place_url):
            in_inventory += 1
            print(f"{prefix}skip ({checked}): already in sheet", flush=True)
            continue

        try:
            website = await quick_website_check(detail_page, place_url)
            if website:
                with_website += 1
                print(f"{prefix}skip ({checked}): has website", flush=True)
                continue

            await wait_for_place_panel(detail_page)
            lead = await extract_place_details(detail_page, list_label)
            lead["google_maps_url"] = resolve_maps_url(lead)
            apply_niche_tag(lead, niche_id, niche_label)

            if skip_index and skip_index.has_lead(lead):
                in_inventory += 1
                print(f"{prefix}skip ({checked}): already in sheet ({lead['name']})", flush=True)
                continue

            if global_pool:
                if not await global_pool.try_add(lead):
                    if global_pool.should_stop():
                        break
                    continue
            else:
                if skip_index:
                    skip_index.register_lead(lead)

            leads.append(lead)
            qualified += 1
            total = await global_pool.count() if global_pool else len(leads)
            cap_label = global_pool.cap if global_pool else max_results
            review_note = ""
            n_reviews = len(lead.get("review_snippets") or [])
            if n_reviews:
                review_note = f", {n_reviews} review snippet(s)"
            print(
                f"{prefix}qualified ({checked}): {lead['name']} ({total}/{cap_label}){review_note}",
                flush=True,
            )

        except Exception as exc:
            print(f"{prefix}error ({checked}): {exc}", flush=True)

    total = len(leads)
    if global_pool:
        total = len(global_pool.leads)
    print(
        f"{prefix}Batch done — checked {len(batch)}, {in_inventory} in sheet, "
        f"{with_website} with websites, {qualified} new qualified "
        f"({total} global total)",
        flush=True,
    )
    return checked


async def scrape_maps_leads(
    *,
    search_query: str,
    max_results: int,
    max_check_listings: int,
    leads_output: Path,
    skip_index: InventorySkipIndex | None = None,
    existing_count: int = 0,
    niche_id: str = "",
    niche_label: str = "",
    skip_sheet_upsert: bool = False,
    require_leads: bool = False,
    browser=None,
    global_pool=None,
) -> list[dict]:
    """Scrape one Maps search. Optionally reuse an existing browser instance."""

    async def run_with_browser(owned_browser) -> list[dict]:
        prefix = f"[{niche_id}] " if niche_id else ""
        if global_pool and global_pool.should_stop():
            print(f"{prefix}Skipping — global cap already reached.", flush=True)
            return []

        context = await owned_browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        search_page = await context.new_page()
        detail_page = await context.new_page()
        for page in (search_page, detail_page):
            page.set_default_navigation_timeout(NAV_TIMEOUT_MS)
            page.set_default_timeout(30000)

        search_url = f"https://www.google.com/maps/search/{quote_plus(search_query)}?hl=en"
        print(f"{prefix}Opening Maps search: {search_query}", flush=True)
        await search_page.goto(search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        await dismiss_consent(search_page)
        await wait_for_results(search_page)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        scrollable = await get_scrollable(search_page)
        seen: set[str] = set()
        leads: list[dict] = []
        checked = 0
        stale_scrolls = 0
        batch_num = 0

        print(
            f"{prefix}Target: "
            f"{'global cap ' + str(global_pool.cap) if global_pool else str(max_results) + ' leads'} "
            f"({existing_count} already in sheet; will check up to {max_check_listings})",
            flush=True,
        )

        while checked < max_check_listings:
            if global_pool and global_pool.should_stop():
                print(f"{prefix}Stopping — global cap reached.", flush=True)
                break
            if not global_pool and len(leads) >= max_results:
                break

            remaining = max_check_listings - checked
            batch = await collect_new_place_urls(search_page, seen, remaining, skip_index)
            if not batch:
                if global_pool and global_pool.should_stop():
                    break
                new_count = await scroll_feed(search_page, scrollable)
                if new_count <= 0:
                    stale_scrolls += 1
                    if stale_scrolls >= 5:
                        print(f"{prefix}No more listings to load.", flush=True)
                        break
                else:
                    stale_scrolls = 0
                continue

            batch_num += 1
            print(f"{prefix}Batch {batch_num}: inspecting {len(batch)} new listings...", flush=True)
            checked = await process_batch(
                detail_page,
                batch,
                seen,
                leads,
                checked,
                skip_index,
                niche_id,
                niche_label,
                global_pool,
                max_results,
                max_check_listings,
            )
            stale_scrolls = 0

            if global_pool and global_pool.should_stop():
                break
            if not global_pool and len(leads) >= max_results:
                break
            if checked >= max_check_listings:
                break

            await scroll_feed(search_page, scrollable)

        print(
            f"{prefix}Finished — {len(leads)} new qualified lead(s) after checking {checked} listings.",
            flush=True,
        )

        await context.close()
        return leads

    if browser is not None:
        return await run_with_browser(browser)

    async with async_playwright() as p:
        owned = await p.chromium.launch(
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
            return await run_with_browser(owned)
        finally:
            await owned.close()


def persist_leads(
    leads: list[dict],
    leads_output: Path,
    *,
    skip_sheet_upsert: bool,
    require_leads: bool,
    checked_hint: str = "",
    existing_count: int = 0,
) -> None:
    root = Path(__file__).resolve().parent
    output_file = root / "no_website_leads.json"

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    if leads:
        leads_output.parent.mkdir(parents=True, exist_ok=True)
        leads_output.write_text(json.dumps(leads, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {leads_output.relative_to(root)}", flush=True)

        if not skip_sheet_upsert:
            try:
                stats = upsert_leads(leads)
                print(
                    f"Merged {len(leads)} new lead(s) into Google Sheet "
                    f"(updated {stats['updated']}, appended {stats['appended']})",
                    flush=True,
                )
            except Exception as exc:
                print(f"Sheet sync skipped: {exc}", flush=True)
        else:
            print("SKIP_SHEET_UPSERT set — sheet update deferred to merge step", flush=True)
    elif require_leads:
        raise SystemExit(
            f"No new no-website leads found {checked_hint}"
            f"({existing_count} already in sheet) — pipeline stopped."
        )


async def scrape_google_maps():
    skip_index: InventorySkipIndex | None = None
    existing_count = 0
    try:
        from dotenv import load_dotenv

        load_dotenv(Path(__file__).resolve().parent / ".env")
        existing = load_inventory()
        existing_count = len(existing)
        if existing:
            skip_index = InventorySkipIndex(existing)
            print(
                f"Loaded {existing_count} lead(s) from Google Sheet — will skip already scraped.",
                flush=True,
            )
    except Exception as exc:
        print(f"Sheet inventory not loaded (will scrape without skip list): {exc}", flush=True)

    leads_rel = os.environ.get("LEADS_OUTPUT", "data/leads.json")
    leads_file = Path(leads_rel) if Path(leads_rel).is_absolute() else Path(__file__).resolve().parent / leads_rel

    leads = await scrape_maps_leads(
        search_query=SEARCH_QUERY,
        max_results=MAX_RESULTS,
        max_check_listings=MAX_CHECK_LISTINGS,
        leads_output=leads_file,
        skip_index=skip_index,
        existing_count=existing_count,
        niche_id=os.environ.get("NICHE_ID", ""),
        niche_label=os.environ.get("NICHE_LABEL", ""),
        skip_sheet_upsert=SKIP_SHEET_UPSERT,
        require_leads=os.environ.get("REQUIRE_LEADS", "").lower() in {"1", "true", "yes"},
    )
    persist_leads(
        leads,
        leads_file,
        skip_sheet_upsert=SKIP_SHEET_UPSERT,
        require_leads=os.environ.get("REQUIRE_LEADS", "").lower() in {"1", "true", "yes"},
        existing_count=existing_count,
    )


if __name__ == "__main__":
    asyncio.run(scrape_google_maps())
