#!/usr/bin/env python3
"""Generate site-data.json from lead data using the DeepSeek API."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_site import render_site  # noqa: E402
from sheets import is_mock_lead  # noqa: E402

LEADS_FILE = ROOT / "data" / "leads.json"
EXAMPLE_DATA = ROOT / "data" / "site-data.example.json"
OUTPUT_FILE = ROOT / "site" / "site-data.json"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

SYSTEM_PROMPT = """You are an elite local SEO copywriter and web content strategist.
Return ONLY valid JSON matching this schema (fill every field richly):

{
  "business": {
    "name": "string",
    "shortName": "string",
    "tagline": "string",
    "niche": "string",
    "phone": "string",
    "address": "string",
    "city": "string",
    "hours": "string",
    "ctaLabel": "string"
  },
  "seo": { "title": "string", "description": "string" },
  "home": {
    "hero": {
      "eyebrow": "string",
      "headline": "string",
      "subheadline": "string",
      "primaryCta": "string",
      "secondaryCta": "string"
    },
    "stats": [{ "value": "string", "label": "string" }],
    "featureSections": [{
      "eyebrow": "string",
      "title": "string",
      "body": "string",
      "bullets": ["string"],
      "reverse": false,
      "cardLabel": "string",
      "cardTitle": "string",
      "cardBody": "string"
    }],
    "whyTitle": "string",
    "whyChooseUs": [{ "title": "string", "description": "string" }],
    "testimonials": [{ "quote": "string", "author": "string", "role": "string" }],
    "cta": {
      "headline": "string",
      "subheadline": "string",
      "primaryCta": "string",
      "secondaryCta": "string"
    }
  },
  "servicesPage": { "intro": "string" },
  "services": [{
    "icon": "01",
    "title": "string",
    "shortDescription": "string",
    "longDescription": "string",
    "benefits": ["string"],
    "process": [{ "title": "string", "description": "string" }],
    "faqs": [{ "question": "string", "answer": "string" }]
  }],
  "about": {
    "headline": "string",
    "mission": "string",
    "story": ["string"],
    "highlight": { "stat": "string", "label": "string" },
    "coreValues": [{ "title": "string", "description": "string" }]
  },
  "contact": {
    "headline": "string",
    "subheadline": "string",
    "primaryCta": "string",
    "formCta": "string",
    "serviceAreas": ["string"]
  }
}

Rules:
- Provide exactly 4 services with unique, detailed copy.
- Provide 4 stats, 2 featureSections, 4 whyChooseUs items, 3 testimonials.
- Each service needs 3-4 benefits, 3 process steps, 2 faqs.
- about.story must be 2 paragraphs.
- Write premium, trustworthy copy — not generic filler.
- Use the lead's real phone, address, city, rating, and reviews where relevant."""


def load_lead() -> dict:
    leads = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    if not leads:
        raise SystemExit(
            "No leads in data/leads.json. Use Actions → Lead pipeline → Run workflow to scrape real businesses."
        )
    index = int(os.environ.get("LEAD_INDEX", "0"))
    if index < 0 or index >= len(leads):
        raise SystemExit(f"LEAD_INDEX {index} out of range (0-{len(leads) - 1})")
    lead = leads[index]
    if is_mock_lead(lead):
        raise SystemExit(f"Refusing mock lead: {lead.get('name')}. Scrape real leads via Run workflow.")
    return lead


def call_deepseek(lead: dict, api_key: str) -> dict:
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
            {"role": "system", "content": SYSTEM_PROMPT},
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
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"DeepSeek API error ({exc.code}): {detail}") from exc

    content = body["choices"][0]["message"]["content"]
    return json.loads(content)


def merge_lead_facts(lead: dict, copy: dict) -> dict:
    business = copy.setdefault("business", {})
    business.setdefault("name", lead["name"])
    business["phone"] = lead.get("phone", business.get("phone", ""))
    business["address"] = lead.get("address", business.get("address", ""))
    business["city"] = lead.get("city", business.get("city", ""))
    business["niche"] = lead.get("niche") or lead.get("category", business.get("niche", ""))

    copy["social_proof"] = {
        "rating": lead.get("rating"),
        "reviews": lead.get("reviews"),
    }
    copy["meta"] = {
        "niche": business.get("niche", ""),
        "generated_by": "deepseek",
    }
    return copy


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    use_example = os.environ.get("USE_EXAMPLE_DATA", "").lower() in {"1", "true", "yes"}
    lead = load_lead()
    print(f"Generating site for: {lead['name']}")

    if use_example:
        site_data = json.loads(EXAMPLE_DATA.read_text(encoding="utf-8"))
        site_data = merge_lead_facts(lead, site_data)
        print("Using example site data template")
    else:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise SystemExit("DEEPSEEK_API_KEY is not set")
        copy = call_deepseek(lead, api_key)
        site_data = merge_lead_facts(lead, copy)

    render_site(site_data)
    print(f"Wrote {OUTPUT_FILE} and rendered HTML pages")


if __name__ == "__main__":
    main()
