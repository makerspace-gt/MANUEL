#!/usr/bin/env python3
"""Builds from kategorien.tsv the entries MANUEL chooses from during classification.

As names for the similarity search each entry gets the categories of the form that belong to it,
plus its own name without the bracketed suffix and its synonyms, each with the top category
in front. Entries with their own distinction such as Kopfhörer, In-Ear appear only with name and synonyms,
because the category of the form belongs to the general entry for which MANUEL asks back. The list of
categories of the form comes from anstiftung and is not in the repo.

Run in the repository root:
    python3 katalog/entries.py <formular.csv> <output.json> [abc.json]

formular.csv has the columns Oberkategorie, Unterkategorie and id. abc.json maps names to the classes
A, B or C, without the file every entry counts as A.
"""

import csv
import json
import sys
from pathlib import Path

CATALOG = Path("katalog/kategorien.tsv")

# Names of the form that MANUEL does not show, see gleichwertig.tsv
HIDDEN = {"Ghettoblaster"}


def main():
    form_file, output = sys.argv[1:3]
    classes = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else {}
    form = {int(row["id"]): (row["Oberkategorie"], row["Unterkategorie"])
            for row in csv.DictReader(open(form_file, encoding="utf-8"))}
    entries, seen = [], set()
    for row in csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t"):
        parts = row["key"].split(".")
        lead = int(parts[1])
        own = len(parts) == 3
        ids = [] if own else [int(i) for i in row["form_ids"].split(" | ") if i]
        upper = form[lead][0]
        labels = []
        own_name = [] if "(" in row["name"] else [(upper, row["name"])]  # Brackets only separate duplicates
        for top, name in [form[i] for i in ids] + own_name + [
                (upper, s) for s in row["synonyms"].split(" | ") if s]:
            label = f"{top} / {name}"
            if name not in HIDDEN and label not in seen:
                labels.append(label)
                seen.add(label)
        entries.append({"schluessel": row["key"], "name": row["name"],
                        "klasse": classes.get(row["name"], "A" if not classes else "C"), "namen": labels})
    json.dump(entries, open(output, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"{len(entries)} Einträge mit {sum(len(e['namen']) for e in entries)} Namen")


if __name__ == "__main__":
    main()
