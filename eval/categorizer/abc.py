#!/usr/bin/env python3
"""ABC classes of the catalog entries by their frequency in the German Open Repair Data.

Every entry of anstiftung in Germany names a category of the form as "top category ~ category".
The category leads over the ID of the form to the catalog entry without its own distinction.
Sorted by frequency, class A reaches up to 80 percent of the repairs, B up to 95 percent, the rest is C,
see docs/einordnung.md, section "ABC-Analyse der Einträge". Entries without repairs are C.

Run in the repository root:
    python3 eval/categorizer/abc.py [quellen/openrepair-data] [eval/categorizer/abc.tsv]
"""

import collections
import csv
import sys
from pathlib import Path

CATALOG = Path("katalog/kategorien.tsv")
FORM = Path("quellen/anstiftung/kategorien.csv")
FILES = ("OpenRepairData_v0.3_aggregate_202607_eee.csv", "OpenRepairData_v0.3_aggregate_202607_non-eee.csv")


def main():
    data = Path(sys.argv[1] if len(sys.argv) > 1 else "quellen/openrepair-data")
    output = Path(sys.argv[2] if len(sys.argv) > 2 else "eval/categorizer/abc.tsv")
    catalog = list(csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t"))
    entry_of_id = {}
    for row in catalog:
        if row["key"].count(".") == 2:  # without own distinction, the categories of the form belong to it
            for form_id in [i for i in row["form_ids"].split(" | ") if i]:
                entry_of_id[form_id] = row["key"]
    ids_of_name = collections.defaultdict(set)
    for row in csv.DictReader(FORM.open(encoding="utf-8")):
        ids_of_name[(row["top_category"], row["category"])].add(row["id"])
        ids_of_name[(None, row["category"])].add(row["id"])
    counts, unmatched = collections.Counter(), collections.Counter()
    for name in FILES:
        for row in csv.DictReader((data / name).open(encoding="utf-8")):
            if row["country"] != "DEU" or row["data_provider"] != "anstiftung":
                continue
            top, _, category = (part.strip() for part in row["partner_product_category"].partition("~"))
            ids = ids_of_name.get((top, category)) or ids_of_name.get((None, category)) or set()
            keys = {entry_of_id[i] for i in ids if i in entry_of_id}
            if len(keys) == 1:
                counts[keys.pop()] += 1
            else:
                unmatched[row["partner_product_category"]] += 1
    total = sum(counts.values())
    running, classes = 0, {}
    for key, count in counts.most_common():
        share = running / total  # share before this entry, so the entry that crosses 80 percent is still A
        classes[key] = "A" if share < 0.80 else "B" if share < 0.95 else "C"
        running += count
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter="\t", lineterminator="\n")
        writer.writerow(["key", "name", "class", "repairs_deu"])
        for row in catalog:
            writer.writerow([row["key"], row["name"], classes.get(row["key"], "C"), counts.get(row["key"], 0)])
    summary = collections.Counter(classes.get(row["key"], "C") for row in catalog)
    print(f"{total} Reparaturen zugeordnet, {sum(unmatched.values())} nicht eindeutig, Klassen {dict(sorted(summary.items()))}")


if __name__ == "__main__":
    main()
