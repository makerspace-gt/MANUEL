#!/usr/bin/env python3
"""Classifies tickets by the first message as it arrives.

The script replaces mandatory texts from the reception with subject and defect. Besides category and
power supply it asks whether item and defect are recognisable and whether the request is about several
items. The tickets exist only locally and do not belong in the repo.

Usage:
    python3 real4.py <tickets.json> <nachrichten.json> <cf-mf.csv> <output.jsonl> <model>
"""

import csv
import json
import re
import sys
import time

from decision import post
from real2 import embed, unit

PLACEHOLDER = re.compile(
    r"^(kam spontan vorbei|wurde spontan mitgebracht|handschriftliche notiz ins zammad übertragen.*|intern)?$",
    re.IGNORECASE | re.DOTALL,
)
FORM = re.compile(r"Was bringst du mit\?:\s*(.*?)\s*Was ist daran defekt\?:\s*(.*)", re.DOTALL)
VOICEMAIL = "Folgende Nachricht wurde hinterlassen:"
POWER = {
    "230 V": "Direkt am Stromnetz über Stecker und Kabel",
    "mit Netzteil": "Über ein externes Netzteil",
    "Akku": "Mit eingebautem oder wechselbarem Akku",
    "Batterie": "Mit Einwegbatterien",
    "ohne Kabel (Mechanik)": "Ohne Strom, rein mechanisch",
    "unbekannt": "Geht aus dem Text nicht hervor",
}


def message(ticket, entry):
    """Returns the text and where it comes from."""
    text = (entry.get("text") or "").strip()
    if PLACEHOLDER.match(text):
        fallback = ticket["titel"]
        if ticket["defekt"] and ticket["defekt"] != "??":
            fallback += ". Defekt: " + ticket["defekt"]
        return fallback, "empfang"
    if VOICEMAIL in text:
        return text.split(VOICEMAIL, 1)[1].strip(" '\n"), "voicemail"
    form = FORM.search(text)
    if form:
        return f"Gegenstand: {form.group(1)}. Defekt: {form.group(2)}", "formular"
    # If volunteers create the ticket themselves, the subject is empty and the title often names the item first
    title = (entry.get("titel") or ticket["titel"] or "").strip()
    if not (entry.get("betreff") or "").strip() and title:
        return f"Titel: {title}\n{text}", "notiz mit titel"
    return text, "nachricht"


def yes_no(question, yes, no):
    return {"type": "noul", "instructions": question, "criteria": {"true": yes, "false": no}}


def main():
    tickets_file, messages_file, csv_file, output, model = sys.argv[1:6]
    with open(csv_file, encoding="utf-8", errors="replace") as handle:
        rows = list(csv.DictReader(handle))
    names = sorted({f"{r['Oberkategorie']} / {r['Unterkategorie']}" for r in rows})
    vectors = []
    for start in range(0, len(names), 64):
        vectors += [unit(v) for v in embed(names[start:start + 64])]
    tickets = json.load(open(tickets_file, encoding="utf-8"))
    messages = json.load(open(messages_file, encoding="utf-8"))

    questions = {
        "strom": {"type": "choice", "instructions": "Womit wird der Gegenstand betrieben?", "criteria": POWER},
        "gegenstand": yes_no(
            "Geht aus dem Text hervor, welcher Gegenstand repariert werden soll?",
            "Ja, der Gegenstand ist benannt",
            "Nein, es bleibt offen, worum es geht, zum Beispiel nur ein Terminwunsch",
        ),
        "defekt": yes_no(
            "Geht aus dem Text hervor, was an dem Gegenstand defekt ist?",
            "Ja, ein Fehler ist beschrieben",
            "Nein, es steht nur, dass etwas repariert werden soll oder gar nichts dazu",
        ),
        "mehrere": yes_no(
            "Geht es um mehr als einen Gegenstand?",
            "Ja, zwei oder mehr Gegenstände, auch gleiche wie zwei Lichterketten",
            "Nein, es geht um einen einzigen Gegenstand",
        ),
    }

    with open(output, "w", encoding="utf-8") as out:
        for ticket in tickets:
            entry = messages.get(ticket["id"])
            if ticket["titel"].lower() == "statistik" or not entry:
                continue
            state, source = message(ticket, entry)
            state = state[:1500]
            start = time.monotonic()
            row = {"id": ticket["id"], "titel": ticket["titel"], "quelle": source,
                   "soll_defekt": ticket["defekt"], "soll_strom": ticket["strom"], "fehler": None}
            try:
                query = unit(embed([state])[0])
                scored = sorted(
                    ((sum(a * b for a, b in zip(query, vector)), name)
                     for vector, name in zip(vectors, names)),
                    reverse=True,
                )
                shortlist = [name for _, name in scored[:25]]
                answers = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {**questions, "kategorie": {
                        "type": "choice",
                        "instructions": "Welche Kategorie beschreibt den Gegenstand am besten?",
                        "criteria": {name: None for name in shortlist},
                    }},
                })["answers"]
                row["kategorie"] = answers["kategorie"]["choice"]
                row["kategorie_p"] = answers["kategorie"]["probabilities"][row["kategorie"]]
                row["strom"] = answers["strom"]["choice"]
                row["strom_p"] = answers["strom"]["probabilities"][row["strom"]]
                for name in ("gegenstand", "defekt", "mehrere"):
                    row[name] = answers[name]["noul"]
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
