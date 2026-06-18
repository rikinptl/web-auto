#!/usr/bin/env python3
"""One-off fix: strip Maps icon glyphs from Phone column in the Google Sheet."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from sheets import _with_retry, ensure_headers, get_worksheet  # noqa: E402
from text_clean import clean_phone, strip_icon_glyphs  # noqa: E402


def main() -> None:
    worksheet = get_worksheet()
    ensure_headers(worksheet)
    records = _with_retry(worksheet.get_all_records, "get_all_records")

    batch_updates = []
    for row_number, row in enumerate(records, start=2):
        old_phone = row.get("Phone", "")
        new_phone = clean_phone(old_phone)
        old_name = row.get("Business Name", "")
        new_name = strip_icon_glyphs(old_name)
        if new_phone != old_phone:
            batch_updates.append({"range": f"C{row_number}", "values": [[new_phone]]})
        if new_name != old_name:
            batch_updates.append({"range": f"A{row_number}", "values": [[new_name]]})

    if not batch_updates:
        print("No phone or name glyphs found — sheet already clean.")
        return

    def _batch_update():
        worksheet.batch_update(batch_updates, value_input_option="USER_ENTERED")

    _with_retry(_batch_update, "clean_sheet_phones")
    print(f"Cleaned {len(batch_updates)} cell(s) in the sheet.")


if __name__ == "__main__":
    main()
