#!/usr/bin/env python3
"""Checks kategorien.tsv for contradictions.

A synonym must not be the name or a synonym of another entry. With --warnungen
it also shows synonyms that contain the name of another entry as part of a word. Usually this is
harmless, for example Lampe in Bettlampe, but it helps when reviewing. The power supply
uses only the values of the form, the ORA group only groups from ora-gruppen.tsv.

The key has the form ORA.Restarters.anstiftung or ORA.Restarters.anstiftung.eigene. In front is
the number of the ORA group, then the id of the category on Restarters.net, then the leading ID of the
form, at the end our own distinction where we split a category of anstiftung. The Restarters id 0
means that the size of the device decides, as for laptops and flat screens. The column
restarters_category must be the name of that id, and the id must have power exactly when the ORA
group has. Each ID of the form belongs to exactly one entry without its own distinction. The
preferred names in gleichwertig.tsv must be entries in the catalog. A confirmed entry needs
name_en, ora_group, restarters_category and power.

Run in the repository root:
    python3 katalog/check.py [--warnungen]
"""

import csv
import re
import sys
from pathlib import Path

CATALOG = Path("katalog/kategorien.tsv")
ORA_GROUPS = Path("eval/decision/ora-gruppen.tsv")
EQUIVALENT = Path("eval/decision/gleichwertig.tsv")
RESTARTERS = Path("quellen/restarters/kategorien.csv")
KEY_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)(\.\d+)?")
POWER = {"230 V", "mit Netzteil", "Batterie", "Akku", "ohne Kabel (Mechanik)"}


def key(text):
    return re.sub(r"\W", "", text.lower())


def main():
    groups = {line.split("\t")[1]: line.split("\t")[0] for line in ORA_GROUPS.read_text(encoding="utf-8").splitlines()
              if line and not line.startswith("#")}
    restarters = {row["id"]: row for row in csv.DictReader(RESTARTERS.open(encoding="utf-8"))}
    rows = list(csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t"))
    owner = {}
    problems = []
    for row in rows:
        for word in [row["name"]] + [s for s in row["synonyms"].split(" | ") if s]:
            other = owner.setdefault(key(word), row["name"])
            if other != row["name"]:
                problems.append(f"{row['name']}: {word} gehört schon zu {other}")
    seen, base = set(), {}
    for row in rows:
        match = KEY_PATTERN.fullmatch(row["key"])
        ids = [i for i in row["form_ids"].split(" | ") if i]
        if not match:
            problems.append(f"{row['name']}: Schlüssel {row['key']} hat nicht die Form ORA.Restarters.anstiftung")
        else:
            if groups.get(row["ora_group"]) != match[1]:
                problems.append(f"{row['name']}: Schlüssel {row['key']} passt nicht zur ORA-Gruppe")
            category = restarters.get(match[2])
            if match[2] != "0" and category is None:
                problems.append(f"{row['name']}: unbekannte Kategorie {match[2]} bei Restarters")
            elif row["restarters_category"] != (category["category"] if category else ""):
                problems.append(f"{row['name']}: restarters_category passt nicht zur ID {match[2]} im Schlüssel")
            elif category and (category["power"] == "nein") != row["ora_group"].startswith("Unpowered"):
                problems.append(f"{row['name']}: Strom der Kategorie {match[2]} bei Restarters passt nicht zur ORA-Gruppe")
            if match[3] not in ids:
                problems.append(f"{row['name']}: führende ID {match[3]} fehlt in form_ids")
            if not match[4]:
                for i in ids:
                    other = base.setdefault(i, row["name"])
                    if other != row["name"]:
                        problems.append(f"{row['name']}: ID {i} gehört schon zu {other}")
        if row["key"] in seen:
            problems.append(f"{row['name']}: Schlüssel {row['key']} doppelt")
        seen.add(row["key"])
    names_all = {row["name"] for row in rows}
    for line in EQUIVALENT.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and line.split("\t")[0] not in names_all:
            problems.append(f"gleichwertig.tsv: {line.split(chr(9))[0]} ist kein Eintrag im Katalog")
    for row in rows:
        if row["status"].startswith("bestätigt"):
            missing = [f for f in ("name_en", "ora_group", "restarters_category", "power") if not row[f].strip()]
            if missing:
                problems.append(f"{row['name']}: bestätigt, aber ohne {', '.join(missing)}")
        if row["ora_group"] not in groups:
            problems.append(f"{row['name']}: unbekannte ORA-Gruppe {row['ora_group']}")
        for value in [v for v in row["power"].split(" | ") if v]:
            if value not in POWER:
                problems.append(f"{row['name']}: unbekannte Stromversorgung {value}")
        for field in ("description", "description_en"):
            if re.search(r"[:;–]", row[field]):
                problems.append(f"{row['name']}: Doppelpunkt, Semikolon oder Gedankenstrich in {field}")
    names = {key(row["name"]): row["name"] for row in rows}
    warnings = []
    for row in rows:
        for word in [s for s in row["synonyms"].split(" | ") if s]:
            for short, other in names.items():
                if other != row["name"] and len(short) >= 5 and short in key(word) and short != key(word):
                    warnings.append(f"Warnung {row['name']}: {word} enthält {other}")
    if "--warnungen" in sys.argv:
        print("\n".join(warnings))
    print("\n".join(problems) or f"{len(rows)} Einträge ohne Widerspruch")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
