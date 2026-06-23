"""Strip invisible icon glyphs Google Maps embeds in scraped text."""

import re
import unicodedata


def strip_icon_glyphs(text: str | None) -> str:
    """Remove PUA / format / control chars Maps embeds (e.g. U+E0B0 phone icon)."""
    if not text:
        return ""
    cleaned: list[str] = []
    for ch in text:
        if "\ue000" <= ch <= "\uf8ff":
            continue
        if "\U000f0000" <= ch <= "\U0010ffff":
            continue
        cat = unicodedata.category(ch)
        if cat in {"Co", "Cf", "Cc", "Cs", "Cn"}:
            continue
        cleaned.append(ch)
    return "".join(cleaned).strip()


def clean_phone(phone: str | None) -> str:
    """Display-safe phone: drop icon glyphs, keep digits and common formatting."""
    phone = strip_icon_glyphs(phone)
    if not phone:
        return ""
    return re.sub(r"[^\d+().\- x]", "", phone, flags=re.I).strip()


def ascii_slugify(text: str) -> str:
    """URL/repo-safe slug: fold accents (grúas → gruas) and drop non-ASCII."""
    if not text:
        return ""
    folded = unicodedata.normalize("NFKD", strip_icon_glyphs(text))
    ascii_text = folded.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower().strip()
    ascii_text = re.sub(r"[^\w\s-]", "", ascii_text)
    return re.sub(r"[\s_-]+", "-", ascii_text).strip("-") or "site"
