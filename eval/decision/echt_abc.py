#!/usr/bin/env python3
"""Ordnet Tickets in Stufen nach der ABC-Klasse der Einträge ein.

Erst wählt das Decision-Modell aus den ähnlichsten A-Einträgen. Ist es unsicher, folgt eine Runde mit
B-Einträgen, danach mit C-Einträgen. Die Sieger der Runden treten in einer Endrunde gegeneinander an,
weil die Sicherheit aus Runden mit verschiedenen Optionen nicht vergleichbar ist. Jede Runde wird
gespeichert, damit sich andere Regeln ohne neuen Lauf prüfen lassen.
Die Tickets liegen nur lokal und gehören nicht ins Repo.

Aufruf:
    python3 echt_abc.py <tickets.json> <eintraege.json> <Ausgabe.jsonl> <Modell> [Schwelle] [Anzahl]

eintraege.json ist eine Liste mit name und klasse (A, B oder C) je Eintrag.
"""

import json
import sys
import time

from decision import post
from echt2 import embed, unit

QUESTION = "Welche Kategorie beschreibt diesen Gegenstand am besten?"


def choose(state, options, model):
    answer = post("/v1/systemone", {
        "model": model, "keep_alive": 600, "state": state,
        "questions": {"kategorie": {"type": "choice", "instructions": QUESTION,
                                    "criteria": {name: None for name in options}}},
    })["answers"]["kategorie"]
    return answer["choice"], answer["probabilities"][answer["choice"]]


def main():
    tickets_file, entries_file, output, model = sys.argv[1:5]
    threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 0.7
    size = int(sys.argv[6]) if len(sys.argv) > 6 else 25
    entries = json.load(open(entries_file, encoding="utf-8"))
    names = [e["name"] for e in entries]
    classes = [e["klasse"] for e in entries]
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
            row = {"id": ticket["id"], "titel": ticket["titel"], "fehler": None, "runden": []}
            try:
                query = unit(embed([state])[0])
                scored = sorted(((sum(a * b for a, b in zip(query, v)), i)
                                 for i, v in enumerate(vectors)), reverse=True)
                for klasse in "ABC":
                    shortlist = [names[i] for _, i in scored if classes[i] == klasse][:size]
                    choice, p = choose(state, shortlist, model)
                    row["runden"].append({"klasse": klasse, "kategorie": choice, "p": p})
                    if p >= threshold:
                        break
                winners = [r["kategorie"] for r in row["runden"]]
                if len(winners) == 1:
                    row["kategorie"], row["kategorie_p"] = winners[0], row["runden"][0]["p"]
                else:
                    row["kategorie"], row["kategorie_p"] = choose(state, winners, model)
                    row["endrunde"] = True
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
