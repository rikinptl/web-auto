#!/usr/bin/env python3
"""Resolve niche/city config into a Google Maps search query."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETS_FILE = ROOT / "config" / "markets.json"


def load_markets() -> dict:
    return json.loads(MARKETS_FILE.read_text(encoding="utf-8"))


def find_niche(markets: dict, niche_id: str) -> dict:
    for niche in markets["niches"]:
        if niche["id"] == niche_id:
            return niche
    raise KeyError(f"Unknown niche id: {niche_id}")


def find_city(markets: dict, city_id: str) -> dict:
    for city in markets["cities"]:
        if city["id"] == city_id:
            return city
    raise KeyError(f"Unknown city id: {city_id}")


def build_search_query(niche_id: str, city_id: str) -> str:
    markets = load_markets()
    niche = find_niche(markets, niche_id)
    city = find_city(markets, city_id)
    return f"{niche['search_term']} near {city['search_term']}"


def main() -> None:
    markets = load_markets()
    niche_id = os.environ.get("NICHE_ID", markets["default_niche"])
    city_id = os.environ.get("CITY_ID", markets["default_city"])

    query = build_search_query(niche_id, city_id)
    print(query)

    # GitHub Actions output
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"search_query={query}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
