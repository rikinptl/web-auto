"""Build and validate Google Maps URLs for leads."""

from urllib.parse import quote_plus


def build_maps_search_url(lead: dict) -> str:
    name = (lead.get("name") or "").strip()
    address = (lead.get("address") or "").strip()
    city = (lead.get("city") or "").strip()

    if address:
        query = f"{name} {address}".strip() if name else address
    elif name and city:
        query = f"{name} {city}"
    else:
        query = name or city

    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


def is_valid_maps_place_url(url: str) -> bool:
    if not url or "google.com/maps" not in url:
        return False

    if "/search?" in url and "query=" in url:
        return True

    if "/place/" not in url:
        return False

    place_segment = url.split("/place/", 1)[1].split("/", 1)[0].split("@", 1)[0]
    if not place_segment or place_segment in {"@", ""}:
        return False

    # Reject coordinate-only place URLs with no real place id/name.
    if place_segment.startswith("@") or place_segment.replace("+", "").replace(".", "").isdigit():
        return False

    return True


def resolve_maps_url(lead: dict) -> str:
    existing = (lead.get("google_maps_url") or "").strip()
    if is_valid_maps_place_url(existing):
        return existing
    return build_maps_search_url(lead)
