#!/usr/bin/env python3
"""Schlägt für jede Kategorie des Formulars eine Gruppe aus ora-gruppen.tsv vor.

Das Decision-Modell sieht Oberkategorie und Kategorie und wählt eine der 46 Gruppen. Das Ergebnis
ist ein Entwurf, den Menschen prüfen. Die Kategorienliste gehört der anstiftung und liegt nicht im Repo.

Aufruf:
    python3 gruppen.py <formular.csv> <ora-gruppen.tsv> <Ausgabe.jsonl> <Modell>
"""

import csv
import json
import sys
import time

from decision import post


def groups(path):
    found = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        _, name, text = line.rstrip("\n").split("\t")
        found[name] = text
    return found


def main():
    csv_file, groups_file, output, model = sys.argv[1:5]
    criteria = groups(groups_file)
    with open(csv_file, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with open(output, "w", encoding="utf-8") as out:
        for row in rows:
            state = f"Oberkategorie: {row['Oberkategorie']}. Gerät oder Gegenstand: {row['Unterkategorie']}"
            result = {"ober": row["Oberkategorie"], "kategorie": row["Unterkategorie"], "id": row["id"], "fehler": None}
            start = time.monotonic()
            try:
                answer = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"gruppe": {
                        "type": "choice",
                        "instructions": "Zu welcher Gruppe gehört dieser Gegenstand?",
                        "criteria": criteria,
                    }},
                })["answers"]["gruppe"]
                ranked = sorted(answer["probabilities"].items(), key=lambda item: -item[1])
                result["gruppe"] = answer["choice"]
                result["p"] = answer["probabilities"][answer["choice"]]
                result["zweite"] = ranked[1][0]
                result["zweite_p"] = ranked[1][1]
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                result["fehler"] = f"{problem} {detail}"[:300]
            result["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
