#!/usr/bin/env python3
"""Builds from kategorien.tsv the entries MANUEL chooses from during classification.

As names for the similarity search each entry gets the categories of the form that belong to it,
plus its own name without the bracketed suffix and its synonyms, each with the top category
in front. Entries with their own distinction such as Kopfhörer, In-Ear appear only with name and synonyms,
because the category of the form belongs to the general entry for which MANUEL asks back. The list of
categories of the form comes from anstiftung and is not in the repo.

Run in the repository root:
    python3 katalog/entries.py <formular.csv> <output.json> [abc.json]

formular.csv has the columns Oberkategorie, Unterkategorie and id, or top_category, category and id as
quellen/anstiftung/kategorien.csv. abc.json maps names to the classes
A, B or C, without the file every entry counts as A.
"""

import csv
import json
import sys
from pathlib import Path

CATALOG = Path("katalog/kategorien.tsv")

# Names of the form that MANUEL does not show, see equivalents.tsv
HIDDEN = {"Ghettoblaster"}


def read_form(path):
    """Categories of the form by id, from the export of anstiftung or from quellen/anstiftung/kategorien.csv."""
    rows = csv.DictReader(open(path, encoding="utf-8"))
    return {int(row["id"]): (row.get("Oberkategorie") or row["top_category"], row.get("Unterkategorie") or row["category"])
            for row in rows}


def build(form, classes=None, catalog=CATALOG):
    """Entries with key, name, class and the names for the similarity search."""
    classes = classes or {}
    entries, seen = [], set()
    for row in csv.DictReader(Path(catalog).open(encoding="utf-8"), delimiter="\t"):
        parts = row["key"].split(".")  # ORA.Restarters.anstiftung, optionally .eigene
        lead = int(parts[2])
        own = len(parts) == 4
        ids = [] if own else [int(i) for i in row["form_ids"].split(" | ") if i]
        upper = form[lead][0]
        labels = []
        own_name = [] if "(" in row["name"] else [(upper, row["name"])]  # Brackets only separate duplicates
        for top, name in [form[i] for i in ids if i in form] + own_name + [
                (upper, s) for s in row["synonyms"].split(" | ") if s]:
            label = f"{top} / {name}"
            if name not in HIDDEN and label not in seen:
                labels.append(label)
                seen.add(label)
        entries.append({"schluessel": row["key"], "name": row["name"],
                        "klasse": classes.get(row["name"], "A" if not classes else "C"), "namen": labels})
    return entries


def main():
    form_file, output = sys.argv[1:3]
    classes = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else {}
    entries = build(read_form(form_file), classes)
    json.dump(entries, open(output, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"{len(entries)} Einträge mit {sum(len(e['namen']) for e in entries)} Namen")


if __name__ == "__main__":
    main()
