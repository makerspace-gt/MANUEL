#!/usr/bin/env python3
"""Stellt die Kategorien aller Partner der Open Repair Alliance nach ORA-Gruppen nebeneinander.

Jede Zeile ist eine Produktkategorie des Open Repair Data Standard. Jede Spalte zeigt, mit welchen
eigenen Kategorien ein Partner die Einträge dieser Gruppe erfasst hat, mit Anzahl und Anteil. Gezeigt
wird je Partner der feste Teil seines Kategoriesystems. Bei Restarters ist das die erste Stufe, die
zweite ist Freitext. Bei der anstiftung und dem Repair Monitor ist es die zweite Stufe, die erste
fasst nur grob zusammen. Wo es nur Freitext gibt, stehen die häufigsten Werte. Die letzte Spalte
zeigt die Einträge unseres Katalogs in dieser Gruppe.

Daneben entsteht eine vollständige Zuordnung in Langform. Jede Kategorie eines Partners steht dort mit
jeder ORA-Gruppe, der die Alliance sie zugeordnet hat. Bei reinem Freitext nur Werte ab 10 Einträgen.

Die Open Repair Data stehen unter CC BY-SA 4.0 und liegen als Submodul in quellen/openrepair-data.

Aufruf im Wurzelverzeichnis des Repos:
    python3 eval/ora/kategorien_matrix.py quellen/openrepair-data
"""

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

KATALOG = Path("katalog/kategorien.tsv")
GRUPPEN = Path("eval/decision/ora-gruppen.tsv")
MATRIX = Path("docs/ora/kategorien-matrix.tsv")
PARTNER = Path("docs/ora/partner.tsv")
ZUORDNUNG = Path("docs/ora/kategorien-zuordnung.tsv")
MIN_FREITEXT = 10
TOP = 3

# Welcher Teil von partner_product_category die feste Liste ist, 0 heißt nur Freitext
STUFE = {
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
FELDER = ["brand", "year_of_manufacture", "problem", "repair_barrier_if_end_of_life"]


def teil(value, stufe):
    parts = [p.strip() for p in (value or "").split(" ~ ")]
    if stufe == 0:
        return (value or "").strip().lower()
    return parts[stufe - 1] if len(parts) >= stufe else parts[-1]


def main():
    folder = Path(sys.argv[1])
    files = sorted(folder.glob("OpenRepairData_*_eee.csv")) + sorted(folder.glob("OpenRepairData_*_non-eee.csv"))
    files = [f for f in files if "Product_Categories" not in f.name]
    cells = defaultdict(lambda: defaultdict(Counter))
    totals = Counter()
    info = defaultdict(lambda: {"n": 0, "laender": Counter(), "jahre": set(), "stufe1": set(), "werte": set(),
                                "felder": Counter()})
    for file in files:
        for row in csv.DictReader(file.open(encoding="utf-8")):
            partner, group = row["data_provider"], row["product_category"]
            value = row["partner_product_category"]
            cells[group][partner][teil(value, STUFE.get(partner, 0))] += 1
            totals[group] += 1
            i = info[partner]
            i["n"] += 1
            i["laender"][row["country"]] += 1
            i["jahre"].add(row["event_date"][:4])
            i["stufe1"].add(teil(value, 1))
            i["werte"].add(value)
            for field in FELDER:
                v = (row[field] or "").strip().lower()
                if v and v not in ("unknown", "0"):
                    i["felder"][field] += 1
    groups = [line.split("\t")[:2] for line in GRUPPEN.read_text(encoding="utf-8").splitlines()
              if line and not line.startswith("#")]
    katalog = defaultdict(list)
    for row in csv.DictReader(KATALOG.open(encoding="utf-8"), delimiter="\t"):
        katalog[row["ora_gruppe"]].append(row["name"])
    partners = sorted(info, key=lambda p: -info[p]["n"])
    MATRIX.parent.mkdir(parents=True, exist_ok=True)
    with MATRIX.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "ora_gruppe", "eintraege"] + partners + ["MANUEL"])
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
            own = katalog.get(name, [])
            row.append(f"{len(own)}: {', '.join(sorted(own)[:TOP])}" if own else "")
            writer.writerow(row)
    # Für das PDF der Hausarbeit in zwei Teilen, sonst passt die Tabelle nicht auf die Seite
    rows = list(csv.reader(MATRIX.open(encoding="utf-8"), delimiter="\t"))
    half = 3 + (len(partners) + 1) // 2
    for number, columns in ((1, range(0, half)), (2, list(range(0, 2)) + list(range(half, len(rows[0]))))):
        with MATRIX.with_name(f"kategorien-matrix-teil{number}.tsv").open("w", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, delimiter="\t", lineterminator="\n")
            for row in rows:
                writer.writerow([row[c] for c in columns])
    with PARTNER.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["partner", "eintraege", "laender", "jahre", "feste_stufe", "werte_stufe1", "werte_gesamt"]
                        + [f"{f}_gefuellt" for f in FELDER])
        for partner in partners:
            i = info[partner]
            jahre = sorted(j for j in i["jahre"] if j)
            writer.writerow([partner, i["n"], ", ".join(k for k, _ in i["laender"].most_common(4)),
                             f"{jahre[0]} bis {jahre[-1]}", STUFE.get(partner, 0), len(i["stufe1"]),
                             len(i["werte"])] + [f"{i['felder'][f] * 100 // i['n']} %" for f in FELDER])
    with ZUORDNUNG.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(["partner", "kategorie_partner", "ora_gruppe", "eintraege", "anteil_an_kategorie"])
        for partner in partners:
            per_value = defaultdict(Counter)
            for group, by_partner in cells.items():
                for value, n in by_partner[partner].items():
                    per_value[value][group] += n
            for value in sorted(per_value, key=lambda v: (-sum(per_value[v].values()), v)):
                total = sum(per_value[value].values())
                if STUFE.get(partner, 0) == 0 and total < MIN_FREITEXT:
                    continue
                for group, n in per_value[value].most_common():
                    writer.writerow([partner, value, group, n, f"{n * 100 // total} %"])
    print(MATRIX, PARTNER, ZUORDNUNG)


if __name__ == "__main__":
    main()
