#!/usr/bin/env python3
"""Classifies tickets from a Zammad export with a decision model.

Two stages, first the top category, then the category below it, plus the power supply.
The tickets exist only locally in a JSON file and do not belong in the repo.

Usage:
    python3 real.py <tickets.json> <kategorien.json> <output.jsonl> <model>
"""

import json
import sys
import time

from decision import post

POWER = {
    "230 V": "Direkt am Stromnetz über Stecker und Kabel",
    "mit Netzteil": "Über ein externes Netzteil",
    "Akku": "Mit eingebautem oder wechselbarem Akku",
    "Batterie": "Mit Einwegbatterien",
    "ohne Kabel (Mechanik)": "Ohne Strom, rein mechanisch",
}


def ask(model, state, questions):
    return post("/v1/systemone", {
        "model": model, "keep_alive": 600, "state": state, "questions": questions,
    })["answers"]


def main():
    tickets_file, categories_file, output, model = sys.argv[1:5]
    categories = json.load(open(categories_file, encoding="utf-8"))
    tickets = json.load(open(tickets_file, encoding="utf-8"))
    top = {c["name"]: c["id"] for c in categories if c["parent"] is None and c["sichtbar"]}
    children = {}
    for category in categories:
        if category["parent"]:
            children.setdefault(category["parent"], []).append(category["name"])
    with open(output, "w", encoding="utf-8") as out:
        for ticket in tickets:
            if ticket["titel"].lower() == "statistik":
                continue
            state = ticket["titel"]
            if ticket["defekt"] and ticket["defekt"] != "??":
                state += ". Defekt: " + ticket["defekt"]
            start = time.monotonic()
            row = {"id": ticket["id"], "titel": ticket["titel"], "soll_strom": ticket["strom"], "fehler": None}
            try:
                first = ask(model, state, {
                    "ober": {
                        "type": "choice",
                        "instructions": "Zu welcher Oberkategorie gehört dieser Gegenstand?",
                        "criteria": {name: None for name in top},
                    },
                    "strom": {
                        "type": "choice",
                        "instructions": "Womit wird dieser Gegenstand betrieben?",
                        "criteria": POWER,
                    },
                })
                row["ober"] = first["ober"]["choice"]
                row["ober_p"] = first["ober"]["probabilities"][row["ober"]]
                row["strom"] = first["strom"]["choice"]
                row["strom_p"] = first["strom"]["probabilities"][row["strom"]]
                options = children.get(top[row["ober"]], [])
                if options:
                    second = ask(model, state, {"kategorie": {
                        "type": "choice",
                        "instructions": "Welche Kategorie beschreibt diesen Gegenstand am besten?",
                        "criteria": {name: None for name in options},
                    }})["kategorie"]
                    row["kategorie"] = second["choice"]
                    row["kategorie_p"] = second["probabilities"][second["choice"]]
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
