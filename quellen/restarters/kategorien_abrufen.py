#!/usr/bin/env python3
"""Ruft die Kategorien von Restarters.net über die öffentliche API ab.

Die API liefert unter /api/v2/items alle bisher erfassten Gegenstände mit ihrer Kategorie. Daraus
ergibt sich die Liste der Kategorien mit Kennung und ob das Gerät Strom braucht. Die Gegenstände
selbst sind Freitext der Nutzerinnen und Nutzer und werden nicht gespeichert.

Aufruf im Wurzelverzeichnis des Repos:
    python3 quellen/restarters/kategorien_abrufen.py
"""

import csv
import json
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

URL = "https://restarters.net/api/v2/items"
ZIEL = Path("quellen/restarters/kategorien.csv")


def main():
    request = urllib.request.Request(URL, headers={"User-Agent": "MANUEL-Recherche"})
    data = json.load(urllib.request.urlopen(request, timeout=60))
    items = data.get("data", data)
    categories, count = {}, Counter()
    for item in items:
        categories[item["idcategories"]] = (item["categoryname"], item["powered"])
        count[item["idcategories"]] += 1
    with ZIEL.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["id", "kategorie", "strom", "gegenstaende_in_der_api"])
        for ident in sorted(categories):
            name, powered = categories[ident]
            writer.writerow([ident, name, "ja" if powered else "nein", count[ident]])
    print(f"{len(categories)} Kategorien am {date.today()} nach {ZIEL}")


if __name__ == "__main__":
    main()
