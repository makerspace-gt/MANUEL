#!/usr/bin/env python3
"""Fetches the categories of Restarters.net via the public API.

The API returns under /api/v2/items all items recorded so far with their category. From this
follows the list of categories with identifier and whether the device needs power. The items
themselves are free text of the users and are not saved.

Run in the repository root:
    python3 quellen/restarters/fetch_categories.py
"""

import csv
import json
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

URL = "https://restarters.net/api/v2/items"
OUTPUT = Path("quellen/restarters/kategorien.csv")


def main():
    request = urllib.request.Request(URL, headers={"User-Agent": "MANUEL-Recherche"})
    data = json.load(urllib.request.urlopen(request, timeout=60))
    items = data.get("data", data)
    categories, count = {}, Counter()
    for item in items:
        categories[item["idcategories"]] = (item["categoryname"], item["powered"])
        count[item["idcategories"]] += 1
    with OUTPUT.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["id", "category", "power", "items_in_api"])
        for ident in sorted(categories):
            name, powered = categories[ident]
            writer.writerow([ident, name, "ja" if powered else "nein", count[ident]])
    print(f"{len(categories)} Kategorien am {date.today()} nach {OUTPUT}")


if __name__ == "__main__":
    main()
