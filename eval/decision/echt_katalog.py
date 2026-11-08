#!/usr/bin/env python3
"""Ordnet Tickets mit dem Katalog ein.

Die Ähnlichkeitssuche nutzt Name und Synonyme jedes Eintrags, das Decision-Modell bekommt die
Beschreibung als Erläuterung der Option. Einträge ohne Beschreibung gehen nur mit dem Namen ein.
Die Tickets liegen nur lokal und gehören nicht ins Repo.

Aufruf:
    python3 echt_katalog.py <tickets.json> <eintraege.json> <Ausgabe.jsonl> <Modell> [Text] [Anzahl]

eintraege.json ist eine Liste mit name, beschreibung und synonyme je Eintrag. Text legt fest, was das
Decision-Modell zu jeder Option sieht: beschreibung (nur die Beschreibung), synonyme (Name und
Synonyme) oder ohne_abgrenzung (Name, Synonyme und Beschreibung ohne die Sätze über eigene Einträge).
"""

import json
import re
import sys
import time

from decision import post
from echt2 import embed, unit


def option(entry, mode):
    """Der Text, den das Decision-Modell zu einer Option sieht."""
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
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
