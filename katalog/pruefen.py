#!/usr/bin/env python3
"""Prüft kategorien.tsv auf Widersprüche.

Ein Synonym darf nicht der Name oder das Synonym eines anderen Eintrags sein. Mit --warnungen
zeigt es zusätzlich Synonyme, die den Namen eines anderen Eintrags als Wortteil enthalten. Meist ist das
harmlos, etwa Lampe in Bettlampe, es hilft aber beim Durchsehen. Die Stromversorgung
nutzt nur die Werte des Laufzettels, die ORA-Gruppe nur Gruppen aus ora-gruppen.tsv.

Aufruf im Wurzelverzeichnis des Repos:
    python3 katalog/pruefen.py [--warnungen]
"""

import csv
import re
import sys
from pathlib import Path

KATALOG = Path("katalog/kategorien.tsv")
GRUPPEN = Path("eval/decision/ora-gruppen.tsv")
STROM = {"230 V", "mit Netzteil", "Batterie", "Akku", "ohne Kabel (Mechanik)"}


def key(text):
    return re.sub(r"\W", "", text.lower())


def main():
    groups = {line.split("\t")[1] for line in GRUPPEN.read_text(encoding="utf-8").splitlines()
              if line and not line.startswith("#")}
    rows = list(csv.DictReader(KATALOG.open(encoding="utf-8"), delimiter="\t"))
    owner = {}
    problems = []
    for row in rows:
        for word in [row["name"]] + [s for s in row["synonyme"].split(" | ") if s]:
            other = owner.setdefault(key(word), row["name"])
            if other != row["name"]:
                problems.append(f"{row['name']}: {word} gehört schon zu {other}")
    for row in rows:
        if row["ora_gruppe"] not in groups:
            problems.append(f"{row['name']}: unbekannte ORA-Gruppe {row['ora_gruppe']}")
        for value in row["strom"].split(" | "):
            if value not in STROM:
                problems.append(f"{row['name']}: unbekannte Stromversorgung {value}")
        for field in ("beschreibung", "beschreibung_en"):
            if re.search(r"[:;–]", row[field]):
                problems.append(f"{row['name']}: Doppelpunkt, Semikolon oder Gedankenstrich in {field}")
    names = {key(row["name"]): row["name"] for row in rows}
    warnings = []
    for row in rows:
        for word in [s for s in row["synonyme"].split(" | ") if s]:
            for short, other in names.items():
                if other != row["name"] and len(short) >= 5 and short in key(word) and short != key(word):
                    warnings.append(f"Warnung {row['name']}: {word} enthält {other}")
    if "--warnungen" in sys.argv:
        print("\n".join(warnings))
    print("\n".join(problems) or f"{len(rows)} Einträge ohne Widerspruch")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
