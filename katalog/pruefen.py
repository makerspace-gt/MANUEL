#!/usr/bin/env python3
"""Prüft kategorien.tsv auf Widersprüche.

Ein Synonym darf nicht der Name oder das Synonym eines anderen Eintrags sein. Mit --warnungen
zeigt es zusätzlich Synonyme, die den Namen eines anderen Eintrags als Wortteil enthalten. Meist ist das
harmlos, etwa Lampe in Bettlampe, es hilft aber beim Durchsehen. Die Stromversorgung
nutzt nur die Werte des Laufzettels, die ORA-Gruppe nur Gruppen aus ora-gruppen.tsv.

Der Schlüssel hat die Form ORA.anstiftung oder ORA.anstiftung.eigene. Vorne steht die Nummer der
ORA-Gruppe, in der Mitte die führende ID des Laufzettels, hinten eine eigene Unterscheidung, wo wir eine
Kategorie der anstiftung aufteilen. Jede ID des Laufzettels gehört zu genau einem Eintrag ohne eigene
Unterscheidung. Die bevorzugten Namen in gleichwertig.tsv müssen Einträge im Katalog sein.

Aufruf im Wurzelverzeichnis des Repos:
    python3 katalog/pruefen.py [--warnungen]
"""

import csv
import re
import sys
from pathlib import Path

KATALOG = Path("katalog/kategorien.tsv")
GRUPPEN = Path("eval/decision/ora-gruppen.tsv")
GLEICH = Path("eval/decision/gleichwertig.tsv")
SCHLUESSEL = re.compile(r"(\d+)\.(\d+)(\.\d+)?")
STROM = {"230 V", "mit Netzteil", "Batterie", "Akku", "ohne Kabel (Mechanik)"}


def key(text):
    return re.sub(r"\W", "", text.lower())


def main():
    groups = {line.split("\t")[1]: line.split("\t")[0] for line in GRUPPEN.read_text(encoding="utf-8").splitlines()
              if line and not line.startswith("#")}
    rows = list(csv.DictReader(KATALOG.open(encoding="utf-8"), delimiter="\t"))
    owner = {}
    problems = []
    for row in rows:
        for word in [row["name"]] + [s for s in row["synonyme"].split(" | ") if s]:
            other = owner.setdefault(key(word), row["name"])
            if other != row["name"]:
                problems.append(f"{row['name']}: {word} gehört schon zu {other}")
    seen, base = set(), {}
    for row in rows:
        match = SCHLUESSEL.fullmatch(row["schluessel"])
        ids = [i for i in row["formular_ids"].split(" | ") if i]
        if not match:
            problems.append(f"{row['name']}: Schlüssel {row['schluessel']} hat nicht die Form ORA.anstiftung")
        else:
            if groups.get(row["ora_gruppe"]) != match[1]:
                problems.append(f"{row['name']}: Schlüssel {row['schluessel']} passt nicht zur ORA-Gruppe")
            if match[2] not in ids:
                problems.append(f"{row['name']}: führende ID {match[2]} fehlt in formular_ids")
            if not match[3]:
                for i in ids:
                    other = base.setdefault(i, row["name"])
                    if other != row["name"]:
                        problems.append(f"{row['name']}: ID {i} gehört schon zu {other}")
        if row["schluessel"] in seen:
            problems.append(f"{row['name']}: Schlüssel {row['schluessel']} doppelt")
        seen.add(row["schluessel"])
    names_all = {row["name"] for row in rows}
    for line in GLEICH.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and line.split("\t")[0] not in names_all:
            problems.append(f"gleichwertig.tsv: {line.split(chr(9))[0]} ist kein Eintrag im Katalog")
    for row in rows:
        if row["ora_gruppe"] not in groups:
            problems.append(f"{row['name']}: unbekannte ORA-Gruppe {row['ora_gruppe']}")
        for value in [v for v in row["strom"].split(" | ") if v]:
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
