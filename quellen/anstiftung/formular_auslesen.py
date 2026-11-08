#!/usr/bin/env python3
"""Liest die Auswahllisten aus der gespeicherten Seite "Laufzettel erstellen" auf reparatur-initiativen.org.

Die Seite wurde angemeldet gespeichert. Das Skript schreibt eine bereinigte Kopie ohne Sicherheitstoken
der Sitzung und ohne Anmeldenamen und zieht die Listen heraus.

* kategorien.csv mit Oberkategorie, Kategorie, ID und ob die Kategorie bestätigt ist
* marken.csv mit Marke und ID
* felder.csv mit den übrigen Auswahlfeldern, etwa Ergebnis und Gründe

Aufruf im Wurzelverzeichnis des Repos:
    python3 quellen/anstiftung/formular_auslesen.py <gespeicherte Seite.html>
"""

import csv
import html
import re
import sys
from pathlib import Path

ZIEL = Path("quellen/anstiftung")


def options(body):
    """Liefert (Gruppe, Wert, Text) für alle Optionen, Gruppe aus optgroup."""
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
    (ZIEL / "laufzettel-erstellen.html").write_text(clean, encoding="utf-8")
    selects = {m.group(1): m.group(2) for m in re.finditer(r'<select[^>]*name="([^"]*)"[^>]*>(.*?)</select>', page, re.S)}
    with (ZIEL / "kategorien.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["Oberkategorie", "Kategorie", "id", "bestaetigt"])
        for group, value, text in options(selects["InfoSheets[category_id]"]):
            unconfirmed = text.endswith("(unbestätigt)")
            writer.writerow([group, text.removesuffix("(unbestätigt)").strip(), value, "nein" if unconfirmed else "ja"])
    with (ZIEL / "marken.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["Marke", "id"])
        for _, value, text in options(selects["InfoSheets[brand_id]"]):
            writer.writerow([text, value])
    with (ZIEL / "felder.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["Feld", "Wert", "Text"])
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
    print("geschrieben nach", ZIEL)


if __name__ == "__main__":
    main()
