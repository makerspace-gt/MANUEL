#!/usr/bin/env python3
"""Classifies tickets with the catalog.

The similarity search uses name and synonyms of each entry, the decision model gets the
description as an explanation of the option. Entries without a description enter with their name only.
The tickets exist only locally and do not belong in the repo.

Usage:
    python3 real_catalog.py <tickets.json> <eintraege.json> <output.jsonl> <model> [text] [count]

eintraege.json is a list with name, beschreibung and synonyme per entry. Text sets what the
decision model sees for each option, beschreibung (only the description), synonyme (name and
synonyms) or ohne_abgrenzung (name, synonyms and description without the sentences about own entries).
"""

import json
import re
import sys
import time

from decision import post
from real2 import embed, unit


def option(entry, mode):
    """The text the decision model sees for an option."""
    if mode == "beschreibung":
        return entry["beschreibung"] or None
    words = ", ".join([entry["name"]] + entry["synonyme"])
    if mode == "synonyme":
        return words
    sentences = re.split(r"(?<=\.)\s+", entry["beschreibung"] or "")
    kept = " ".join(s for s in sentences if s and "eigene" not in s)
    return f"{words}. {kept}".strip(". ") if kept else words


def main():
    tickets_file, entries_file, output, model = sys.argv[1:5]
    mode = sys.argv[5] if len(sys.argv) > 5 else "beschreibung"
    size = int(sys.argv[6]) if len(sys.argv) > 6 else 25
    entries = json.load(open(entries_file, encoding="utf-8"))
    texts = [", ".join([e["name"]] + e["synonyme"]) for e in entries]
    vectors = []
    for start in range(0, len(texts), 64):
        vectors += [unit(v) for v in embed(texts[start:start + 64])]
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
                scored = sorted(((sum(a * b for a, b in zip(query, v)), i)
                                 for i, v in enumerate(vectors)), reverse=True)
                shortlist = [entries[i] for _, i in scored[:size]]
                answer = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"kategorie": {
                        "type": "choice",
                        "instructions": "Welche Kategorie beschreibt diesen Gegenstand am besten?",
                        "criteria": {e["name"]: option(e, mode) for e in shortlist},
                    }},
                })["answers"]["kategorie"]
                row["kategorie"] = answer["choice"]
                row["kategorie_p"] = answer["probabilities"][answer["choice"]]
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
