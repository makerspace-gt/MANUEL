#!/usr/bin/env python3
"""Ordnet Tickets mit zusammengefassten Einträgen ein, die unter ihrem passendsten Namen erscheinen.

Jeder Eintrag des Katalogs fasst mehrere Namen des Formulars zusammen. Die Ähnlichkeitssuche läuft über
alle Namen. In der Shortlist erscheint jeder Eintrag nur einmal, und zwar unter dem Namen, der dem Ticket
am ähnlichsten ist. So sieht das Decision-Modell kurze, genaue Optionen ohne Fast-Dubletten.

Mit kaskade wählt das Modell erst aus A-Einträgen, bei Unsicherheit aus B und dann aus C. Die Sieger
der Runden treten in einer Endrunde gegeneinander an. Jede Runde wird gespeichert.
Die Tickets liegen nur lokal und gehören nicht ins Repo.

Aufruf:
    python3 echt_vertreter.py <tickets.json> <eintraege.json> <Ausgabe.jsonl> <Modell> <alle|kaskade|ab> [Schwelle] [Anzahl]

eintraege.json ist eine Liste mit name, klasse (A, B oder C) und namen. Die Namen sind die Formularnamen
und Synonyme, jeweils mit Oberkategorie davor.
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


def shortlist(scored, labels, owner, classes, allowed, size):
    """Die besten Einträge der erlaubten Klassen, jeder unter seinem ähnlichsten Namen."""
    seen, options = set(), []
    for _, i in scored:
        entry = owner[i]
        if classes[entry] in allowed and entry not in seen:
            seen.add(entry)
            options.append(labels[i])
            if len(options) == size:
                break
    return options


def main():
    tickets_file, entries_file, output, model, mode = sys.argv[1:6]
    threshold = float(sys.argv[6]) if len(sys.argv) > 6 else 0.7
    size = int(sys.argv[7]) if len(sys.argv) > 7 else 25
    entries = json.load(open(entries_file, encoding="utf-8"))
    labels, owner = [], []
    for index, entry in enumerate(entries):
        for name in entry["namen"]:
            if name not in labels:
                labels.append(name)
                owner.append(index)
    classes = [e["klasse"] for e in entries]
    entry_of = dict(zip(labels, (entries[i]["name"] for i in owner)))
    vectors = []
    for start in range(0, len(labels), 64):
        vectors += [unit(v) for v in embed(labels[start:start + 64])]
    rounds = {"alle": ["ABC"], "ab": ["AB"], "kaskade": ["A", "B", "C"]}[mode]
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
                for allowed in rounds:
                    options = shortlist(scored, labels, owner, classes, allowed, size)
                    choice, p = choose(state, options, model)
                    row["runden"].append({"klasse": allowed, "name": choice, "p": p})
                    if p >= threshold:
                        break
                winners = list(dict.fromkeys(r["name"] for r in row["runden"]))
                if len(winners) == 1:
                    row["name"], row["kategorie_p"] = winners[0], max(r["p"] for r in row["runden"])
                else:
                    row["name"], row["kategorie_p"] = choose(state, winners, model)
                    row["endrunde"] = True
                row["kategorie"] = entry_of[row["name"]]
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
