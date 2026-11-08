#!/usr/bin/env python3
"""Ordnet Tickets über Ähnlichkeit und Decision-Modell ein.

bge-m3 sucht die ähnlichsten Kategorien aus der CSV von mapped-repair-events, das Decision-Modell
wählt daraus. So kann eine falsche Oberkategorie die richtige Kategorie nicht mehr verdecken.
Die Tickets liegen nur lokal und gehören nicht ins Repo.

Aufruf:
    python3 echt2.py <tickets.json> <cf-mf.csv> <Ausgabe.jsonl> <Modell> [Anzahl]
"""

import csv
import json
import math
import sys
import time

from decision import post

EMBED = "bge-m3"


def embed(texts):
    return post("/api/embed", {"model": EMBED, "input": texts, "keep_alive": 600})["embeddings"]


def unit(vector):
    size = math.sqrt(sum(v * v for v in vector))
    return [v / size for v in vector]


def main():
    tickets_file, csv_file, output, model = sys.argv[1:5]
    size = int(sys.argv[5]) if len(sys.argv) > 5 else 25
    with open(csv_file, encoding="utf-8", errors="replace") as handle:
        rows = list(csv.DictReader(handle))
    names = sorted({f"{r['Oberkategorie']} / {r['Unterkategorie']}" for r in rows})
    vectors = []
    for start in range(0, len(names), 64):
        vectors += [unit(v) for v in embed(names[start:start + 64])]

    tickets = json.load(open(tickets_file, encoding="utf-8"))
    with open(output, "w", encoding="utf-8") as out:
        for ticket in tickets:
            if ticket["titel"].lower() == "statistik":
                continue
            state = ticket["titel"]
            if ticket["defekt"] and ticket["defekt"] != "??":
                state += ". Defekt: " + ticket["defekt"]
            start = time.monotonic()
            row = {"id": ticket["id"], "titel": ticket["titel"], "fehler": None}
            try:
                query = unit(embed([state])[0])
                scored = sorted(
                    ((sum(a * b for a, b in zip(query, vector)), name)
                     for vector, name in zip(vectors, names)),
                    reverse=True,
                )
                shortlist = [name for _, name in scored[:size]]
                answer = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"kategorie": {
                        "type": "choice",
                        "instructions": "Welche Kategorie beschreibt diesen Gegenstand am besten?",
                        "criteria": {name: None for name in shortlist},
                    }},
                })["answers"]["kategorie"]
                row["aehnlich"] = shortlist[0]
                row["kategorie"] = answer["choice"]
                row["kategorie_p"] = answer["probabilities"][answer["choice"]]
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
