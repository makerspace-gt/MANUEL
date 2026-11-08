#!/usr/bin/env python3
"""Reads the option lists from the saved page "Laufzettel erstellen" on reparatur-initiativen.org.

The page was saved while logged in. The script writes a cleaned copy without the session's security
token and without the login name and extracts the lists.

* kategorien.csv with top category, category, ID and whether the category is confirmed
* marken.csv with brand and ID
* felder.csv with the other option fields, for example result and reasons

Run in the repository root:
    python3 quellen/anstiftung/parse_form.py <saved page.html>
"""

import csv
import html
import re
import sys
from pathlib import Path

OUTPUT_DIR = Path("quellen/anstiftung")


def options(body):
    """Returns (group, value, text) for all options, group from optgroup."""
    result, group = [], ""
    for part in re.finditer(r'<optgroup label="([^"]*)"|<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', body, re.S):
        if part.group(1) is not None:
            group = html.unescape(part.group(1))
        elif part.group(2):
            result.append((group, part.group(2), html.unescape(re.sub(r"<[^>]+>", "", part.group(3))).strip()))
    return result


def main():
    source = Path(sys.argv[1])
    page = source.read_text(encoding="utf-8")
    clean = re.sub(r'(name="(?:_csrfToken|_Token\[[^\]]*\])"[^>]*value=")[^"]*', r"\1entfernt", page)
    clean = re.sub(r'(value=")[^"]*("[^>]*name="(?:_csrfToken|_Token\[[^\]]*\])")', r"\1entfernt\2", clean)
    clean = re.sub(r'(<div class="greeting">Willkommen)[^<]*', r"\1", clean)
    (OUTPUT_DIR / "laufzettel-erstellen.html").write_text(clean, encoding="utf-8")
    selects = {m.group(1): m.group(2) for m in re.finditer(r'<select[^>]*name="([^"]*)"[^>]*>(.*?)</select>', page, re.S)}
    with (OUTPUT_DIR / "kategorien.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["top_category", "category", "id", "confirmed"])
        for group, value, text in options(selects["InfoSheets[category_id]"]):
            unconfirmed = text.endswith("(unbestätigt)")
            writer.writerow([group, text.removesuffix("(unbestätigt)").strip(), value, "nein" if unconfirmed else "ja"])
    with (OUTPUT_DIR / "marken.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["brand", "id"])
        for _, value, text in options(selects["InfoSheets[brand_id]"]):
            writer.writerow([text, value])
    with (OUTPUT_DIR / "felder.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["field", "value", "text"])
        for name, body in selects.items():
            if name in ("InfoSheets[category_id]", "InfoSheets[brand_id]"):
                continue
            for _, value, text in options(body):
                writer.writerow([name, value, text])
        for m in re.finditer(r'<input[^>]*type="(?:radio|checkbox)"[^>]*>', page):
            tag = m.group(0)
            name = re.search(r'name="([^"]*)"', tag)
            value = re.search(r'value="([^"]*)"', tag)
            ident = re.search(r'id="([^"]*)"', tag)
            label = re.search(r'<label[^>]*for="%s"[^>]*>(.*?)</label>' % re.escape(ident.group(1)), page, re.S) if ident else None
            text = html.unescape(re.sub(r"<[^>]+>", "", label.group(1))).strip() if label else ""
            if name and value:
                writer.writerow([name.group(1), value.group(1), text])
    print("geschrieben nach", OUTPUT_DIR)


if __name__ == "__main__":
    main()
