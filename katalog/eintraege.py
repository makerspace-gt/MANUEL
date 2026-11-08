#!/usr/bin/env python3
"""Baut aus kategorien.tsv die Einträge, aus denen MANUEL bei der Einordnung wählt.

Jeder Eintrag bekommt als Namen für die Ähnlichkeitssuche die Kategorien des Laufzettels, die zu ihm
gehören, dazu seinen eigenen Namen ohne Klammerzusatz und seine Synonyme, jeweils mit Oberkategorie
davor. Einträge mit eigener Unterscheidung wie Kopfhörer, In-Ear erscheinen nur mit Namen und Synonymen,
denn die Kategorie des Laufzettels gehört zum allgemeinen Eintrag, bei dem MANUEL nachfragt. Die Liste der Kategorien
des Laufzettels stammt von der anstiftung und liegt nicht im Repo.

Aufruf im Wurzelverzeichnis des Repos:
    python3 katalog/eintraege.py <formular.csv> <Ausgabe.json> [abc.json]

formular.csv hat die Spalten Oberkategorie, Unterkategorie und id. abc.json ordnet Namen den Klassen
A, B oder C zu, ohne die Datei gilt jeder Eintrag als A.
"""

import csv
import json
import sys
from pathlib import Path

KATALOG = Path("katalog/kategorien.tsv")

# Namen des Laufzettels, die MANUEL nicht anzeigt, siehe gleichwertig.tsv
AUSGEBLENDET = {"Ghettoblaster"}


def main():
    form_file, output = sys.argv[1:3]
    classes = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else {}
    form = {int(row["id"]): (row["Oberkategorie"], row["Unterkategorie"])
            for row in csv.DictReader(open(form_file, encoding="utf-8"))}
    entries, seen = [], set()
    for row in csv.DictReader(KATALOG.open(encoding="utf-8"), delimiter="\t"):
        parts = row["schluessel"].split(".")
        lead = int(parts[1])
        own = len(parts) == 3
        ids = [] if own else [int(i) for i in row["formular_ids"].split(" | ") if i]
        upper = form[lead][0]
        labels = []
        own_name = [] if "(" in row["name"] else [(upper, row["name"])]  # Klammern trennen nur Dubletten
        for ober, name in [form[i] for i in ids] + own_name + [
                (upper, s) for s in row["synonyme"].split(" | ") if s]:
            label = f"{ober} / {name}"
            if name not in AUSGEBLENDET and label not in seen:
                labels.append(label)
                seen.add(label)
        entries.append({"schluessel": row["schluessel"], "name": row["name"],
                        "klasse": classes.get(row["name"], "A" if not classes else "C"), "namen": labels})
    json.dump(entries, open(output, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"{len(entries)} Einträge mit {sum(len(e['namen']) for e in entries)} Namen")


if __name__ == "__main__":
    main()
