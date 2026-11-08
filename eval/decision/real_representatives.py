#!/usr/bin/env python3
"""Classifies tickets with merged entries that appear under their best matching name.

Each catalog entry merges several names of the form. The similarity search runs over
all names. In the shortlist each entry appears only once, under the name that is most similar
to the ticket. This way the decision model sees short, precise options without near duplicates.

With kaskade the model first chooses from A entries, if uncertain from B and then from C. The winners
of the rounds compete in a final round. Every round is saved.
The field rueckfrage gives the reason why MANUEL would ask back, see follow_up.py.
The tickets exist only locally and do not belong in the repo.

Usage:
    python3 real_representatives.py <tickets.json> <eintraege.json> <output.jsonl> <model> <alle|kaskade|ab> [threshold] [count]

eintraege.json is a list with name, klasse (A, B or C) and namen. The names are the form names
and synonyms, each with the top category in front.
"""

import json
import sys
import time

from decision import post
from real2 import embed, unit
from follow_up import reason

QUESTION = "Welche Kategorie beschreibt diesen Gegenstand am besten?"


def choose(state, options, model):
    answer = post("/v1/systemone", {
        "model": model, "keep_alive": 600, "state": state,
        "questions": {"kategorie": {"type": "choice", "instructions": QUESTION,
                                    "criteria": {name: None for name in options}}},
    })["answers"]["kategorie"]
    return answer["choice"], answer["probabilities"][answer["choice"]]


def shortlist(scored, labels, owner, classes, allowed, size):
    """The best entries of the allowed classes, each under its most similar name."""
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
                row["rueckfrage"] = reason(row["kategorie"], row["name"].split(" / ", 1)[-1],
                                          ticket["titel"], row["kategorie_p"], threshold)
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
