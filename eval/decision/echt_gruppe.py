#!/usr/bin/env python3
"""Ordnet Tickets mit vorgeschalteter ORA-Gruppe ein.

Erst wählt das Decision-Modell aus den Gruppen des Open Repair Data Standard. Die Shortlist für
die Kategorie besteht dann aus den ähnlichsten Kategorien der beiden wahrscheinlichsten Gruppen,
ergänzt um die ähnlichsten Kategorien ohne Einschränkung. So verdeckt eine falsche Gruppe die
richtige Kategorie nicht vollständig. Die Tickets liegen nur lokal und gehören nicht ins Repo.

Aufruf:
    python3 echt_gruppe.py <tickets.json> <formular.csv> <zuordnung.tsv> <ora-gruppen.tsv> \
        <Ausgabe.jsonl> <Modell> [aus Gruppen] [ohne Einschränkung]

zuordnung.tsv enthält pro Zeile "Oberkategorie / Kategorie" und die ORA-Gruppe, getrennt durch Tab.
"""

import csv
import json
import sys
import time

from decision import post
from echt2 import embed, unit


def similar(query, vectors, names, allowed, size):
    scored = sorted(
        ((sum(a * b for a, b in zip(query, vector)), name)
         for vector, name in zip(vectors, names) if allowed is None or name in allowed),
        reverse=True,
    )
    return [name for _, name in scored[:size]]


def main():
    tickets_file, csv_file, mapping_file, groups_file, output, model = sys.argv[1:7]
    in_groups = int(sys.argv[7]) if len(sys.argv) > 7 else 20
    free = int(sys.argv[8]) if len(sys.argv) > 8 else 10
    with open(csv_file, encoding="utf-8") as handle:
        names = sorted({f"{r['Oberkategorie']} / {r['Unterkategorie']}" for r in csv.DictReader(handle)})
    group_of = dict(line.rstrip("\n").split("\t")[:2] for line in open(mapping_file, encoding="utf-8"))
    groups = {}
    for line in open(groups_file, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        _, name, text = line.rstrip("\n").split("\t")[:3]
        groups[name] = text
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
                answer = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"gruppe": {
                        "type": "choice",
                        "instructions": "Zu welcher Gruppe gehört dieser Gegenstand?",
                        "criteria": groups,
                    }},
                })["answers"]["gruppe"]
                ranked = sorted(answer["probabilities"].items(), key=lambda t: -t[1])
                top = {name for name, _ in ranked[:2]}
                allowed = {name for name in names if group_of.get(name) in top}
                query = unit(embed([state])[0])
                shortlist = similar(query, vectors, names, allowed, in_groups)
                for name in similar(query, vectors, names, None, free):
                    if name not in shortlist:
                        shortlist.append(name)
                choice = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"kategorie": {
                        "type": "choice",
                        "instructions": "Welche Kategorie beschreibt diesen Gegenstand am besten?",
                        "criteria": {name: None for name in shortlist},
                    }},
                })["answers"]["kategorie"]
                row["gruppe"] = ranked[0][0]
                row["gruppe_p"] = ranked[0][1]
                row["zweite"] = ranked[1][0]
                row["zweite_p"] = ranked[1][1]
                row["kategorie"] = choice["choice"]
                row["kategorie_p"] = choice["probabilities"][choice["choice"]]
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
