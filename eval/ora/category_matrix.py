#!/usr/bin/env python3
"""Puts the categories of all partners of the Open Repair Alliance side by side by ORA group.

Each row is a product category of the Open Repair Data Standard. Each column shows with which
own categories a partner recorded the entries of this group, with count and share. Shown
per partner is the fixed part of its category system. For Restarters that is the first level, the
second is free text. For anstiftung and the Repair Monitor it is the second level, the first
only groups roughly. Where there is only free text, the most frequent values are shown. The last column
shows the entries of our catalog in this group.

In addition a complete mapping in long form is created. Each category of a partner appears there with
every ORA group the Alliance mapped it to. For pure free text only values with at least 10 entries.

The Open Repair Data are under CC BY-SA 4.0 and are a submodule in quellen/openrepair-data.

Run in the repository root:
    python3 eval/ora/category_matrix.py quellen/openrepair-data
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

CATALOG = Path("katalog/kategorien.tsv")
ORA_GROUPS = Path("eval/decision/ora-gruppen.tsv")
MATRIX = Path("docs/ora/kategorien-matrix.tsv")
PARTNER = Path("docs/ora/partner.tsv")
MAPPING = Path("docs/ora/kategorien-zuordnung.tsv")
MIN_FREE_TEXT = 10
TOP = 3

# Which part of partner_product_category is the fixed list, 0 means free text only
FIXED_LEVEL = {
    "The Restart Project": 1,
    "Repair Café International": 2,
    "anstiftung": 2,
    "Repair Cafe Wales": 1,
    "Repair Connects": 1,
    "iFixit": 1,
    "Repair Café Denmark": 0,
    "Repair Café Toronto": 0,
    "Fixit Clinic": 0,
}
FIELDS = ["brand", "year_of_manufacture", "problem", "repair_barrier_if_end_of_life"]


def fixed_part(value, level):
    parts = [p.strip() for p in (value or "").split(" ~ ")]
    if level == 0:
        return (value or "").strip().lower()
    return parts[level - 1] if len(parts) >= level else parts[-1]


def main():
    folder = Path(sys.argv[1])
    files = sorted(folder.glob("OpenRepairData_*_eee.csv")) + sorted(folder.glob("OpenRepairData_*_non-eee.csv"))
    files = [f for f in files if "Product_Categories" not in f.name]
    cells = defaultdict(lambda: defaultdict(Counter))
    totals = Counter()
    info = defaultdict(lambda: {"n": 0, "countries": Counter(), "years": set(), "level1": set(), "values": set(),
                                "fields": Counter()})
    for file in files:
        for row in csv.DictReader(file.open(encoding="utf-8")):
            partner, group = row["data_provider"], row["product_category"]
            value = row["partner_product_category"]
            cells[group][partner][fixed_part(value, FIXED_LEVEL.get(partner, 0))] += 1
            totals[group] += 1
            i = info[partner]
            i["n"] += 1
            i["countries"][row["country"]] += 1
            i["years"].add(row["event_date"][:4])
            i["level1"].add(fixed_part(value, 1))
            i["values"].add(value)
            for field in FIELDS:
                v = (row[field] or "").strip().lower()
                if v and v not in ("unknown", "0"):
                    i["fields"][field] += 1
    groups = [line.split("\t")[:2] for line in ORA_GROUPS.read_text(encoding="utf-8").splitlines()
              if line and not line.startswith("#")]
    catalog = defaultdict(list)
    for row in csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t"):
        catalog[row["ora_group"]].append(row["name"])
    partners = sorted(info, key=lambda p: -info[p]["n"])
    MATRIX.parent.mkdir(parents=True, exist_ok=True)
    with MATRIX.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "ora_group", "entries"] + partners + ["MANUEL"])
        for gid, name in groups:
            row = [gid, name, totals[name]]
            for partner in partners:
                counter = cells[name][partner]
                n = sum(counter.values())
                if not n:
                    row.append("")
                    continue
                top = ", ".join(f"{k or '(leer)'} {v * 100 // n} %" for k, v in counter.most_common(TOP))
                row.append(f"{n}: {top}")
            own = catalog.get(name, [])
            row.append(f"{len(own)}: {', '.join(sorted(own)[:TOP])}" if own else "")
            writer.writerow(row)
    # Two parts for the PDF of the case study, otherwise the table does not fit on the page
    rows = list(csv.reader(MATRIX.open(encoding="utf-8"), delimiter="\t"))
    half = 3 + (len(partners) + 1) // 2
    for number, columns in ((1, range(0, half)), (2, list(range(0, 2)) + list(range(half, len(rows[0]))))):
        with MATRIX.with_name(f"kategorien-matrix-teil{number}.tsv").open("w", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, delimiter="\t", lineterminator="\n")
            for row in rows:
                writer.writerow([row[c] for c in columns])
    with PARTNER.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["partner", "entries", "countries", "years", "fixed_level", "values_level1", "values_total"]
                        + [f"{f}_filled" for f in FIELDS])
        for partner in partners:
            i = info[partner]
            years = sorted(j for j in i["years"] if j)
            writer.writerow([partner, i["n"], ", ".join(k for k, _ in i["countries"].most_common(4)),
                             f"{years[0]} bis {years[-1]}", FIXED_LEVEL.get(partner, 0), len(i["level1"]),
                             len(i["values"])] + [f"{i['fields'][f] * 100 // i['n']} %" for f in FIELDS])
    with MAPPING.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["partner", "partner_category", "ora_group", "entries", "share_of_category"])
        for partner in partners:
            per_value = defaultdict(Counter)
            for group, by_partner in cells.items():
                for value, n in by_partner[partner].items():
                    per_value[value][group] += n
            for value in sorted(per_value, key=lambda v: (-sum(per_value[v].values()), v)):
                total = sum(per_value[value].values())
                if FIXED_LEVEL.get(partner, 0) == 0 and total < MIN_FREE_TEXT:
                    continue
                for group, n in per_value[value].most_common():
                    writer.writerow([partner, value, group, n, f"{n * 100 // total} %"])
    print(MATRIX, PARTNER, MAPPING)


if __name__ == "__main__":
    main()
