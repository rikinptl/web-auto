#!/usr/bin/env python3
"""Generate site-data.json from lead data using the DeepSeek API."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEADS_FILE = ROOT / "data" / "leads.json"
OUTPUT_FILE = ROOT / "site" / "site-data.json"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def load_lead() -> dict:
    leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    if not leads:
        raise SystemExit("No leads found in data/leads.json")
    index = int(os.environ.get("LEAD_INDEX", "0"))
    if index < 0 or index >= len(leads):
        raise SystemExit(f"LEAD_INDEX {index} out of range (0-{len(leads) - 1})")
    return leads[index]


def call_deepseek(lead: dict, api_key: str) -> dict:
    system_prompt = (
        "You are a local SEO copywriter. Return ONLY valid JSON with these keys: "
        "businessName, tagline, heroHeadline, heroSubtext, services (array of "
        "{title, description}), aboutTitle, aboutText, ctaText. "
        "Write persuasive, professional copy for a local service business. "
        "Keep sentences concise and trustworthy."
    )
    user_prompt = json.dumps(
        {
            "business_name": lead["name"],
            "niche": lead.get("niche") or lead.get("category", ""),
            "city": lead.get("city", ""),
            "phone": lead.get("phone", ""),
            "address": lead.get("address", ""),
            "rating": lead.get("rating"),
            "reviews": lead.get("reviews"),
        },
        indent=2,
    )

    payload = {
        "model": "deepseek-chat",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
    }

    request = urllib.request.Request(
        DEEPSEEK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"DeepSeek API error ({exc.code}): {detail}") from exc

    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def build_site_data(lead: dict, copy: dict) -> dict:
    return {
        "businessName": copy.get("businessName") or lead["name"],
        "tagline": copy.get("tagline", ""),
        "hero": {
            "headline": copy.get("heroHeadline", ""),
            "subtext": copy.get("heroSubtext", ""),
        },
        "services": copy.get("services", []),
        "about": {
            "title": copy.get("aboutTitle", "About Us"),
            "text": copy.get("aboutText", ""),
        },
        "contact": {
            "phone": lead.get("phone", ""),
            "address": lead.get("address", ""),
            "city": lead.get("city", ""),
        },
        "social_proof": {
            "rating": lead.get("rating"),
            "reviews": lead.get("reviews"),
        },
        "ctaText": copy.get("ctaText", "Call Now"),
        "meta": {
            "niche": lead.get("niche") or lead.get("category", ""),
            "generated_by": "deepseek",
        },
    }


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not set")

    lead = load_lead()
    print(f"Generating copy for: {lead['name']}")

    copy = call_deepseek(lead, api_key)
    site_data = build_site_data(lead, copy)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(site_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
