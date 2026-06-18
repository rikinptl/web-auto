"""Strip invisible icon glyphs Google Maps embeds in scraped text."""


def strip_icon_glyphs(text: str | None) -> str | None:
    """Remove Private Use Area chars (e.g. U+E0B0 phone, U+E0C8 pin)."""
    if not text:
        return text
    cleaned = "".join(ch for ch in text if not ("\ue000" <= ch <= "\uf8ff")).strip()
    return cleaned or None
