#!/usr/bin/env python3
"""Classifies tickets in stages by the ABC class of the entries.

First the decision model chooses from the most similar A entries. If it is uncertain, a round with
B entries follows, then one with C entries. The winners of the rounds compete in a final round,
because the confidence from rounds with different options is not comparable. Every round is
saved so that other rules can be tested without a new run.
The tickets exist only locally and do not belong in the repo.

Usage:
    python3 real_abc.py <tickets.json> <eintraege.json> <output.jsonl> <model> [threshold] [count]

eintraege.json is a list with name and klasse (A, B or C) per entry.
"""

import json
import sys
import time

from decision import post
from real2 import embed, unit

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
                for abc_class in "ABC":
                    shortlist = [names[i] for _, i in scored if classes[i] == abc_class][:size]
                    choice, p = choose(state, shortlist, model)
                    row["runden"].append({"klasse": abc_class, "kategorie": choice, "p": p})
                    if p >= threshold:
                        break
                winners = [r["kategorie"] for r in row["runden"]]
                if len(winners) == 1:
                    row["kategorie"], row["kategorie_p"] = winners[0], row["runden"][0]["p"]
                else:
                    row["kategorie"], row["kategorie_p"] = choose(state, winners, model)
                    row["endrunde"] = True
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
