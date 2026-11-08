#!/usr/bin/env python3
"""Tests decision models with the further questions on the tickets from zusatz.tsv.

Run in the directory eval/decision:
    python3 extra.py lauf <output.jsonl> <model> [de|en]
    python3 extra.py auswertung <directory>
"""

import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

from decision import post

FIELDS = ("absicht", "wunsch", "kleinigkeit", "strom", "marke", "vollstaendig")

QUESTIONS = {
    "de": {
        "absicht": ("choice", "Was möchte die Person mit dieser Nachricht?", {
            "neu": "Sie beschreibt ein Gerät oder Problem und möchte Hilfe bei der Reparatur",
            "absage": "Sie kommt nicht oder sagt ab und nennt keine neue Zeit, auch wenn sie sich später wieder melden will",
            "verschieben": "Sie möchte einen bestehenden Termin behalten und nennt dafür eine andere Zeit",
            "rueckfrage": "Sie hat eine allgemeine Frage",
        }),
        "wunsch": ("choice", "Welche Uhrzeit wünscht sich die Person?", {
            "1100": "11:00 Uhr", "1130": "11:30 Uhr", "1200": "12:00 Uhr", "1230": "12:30 Uhr",
            "1300": "13:00 Uhr", "1330": "13:30 Uhr", "1400": "14:00 Uhr",
            "frueh": "Früh am Tag, ohne genaue Uhrzeit",
            "mittel": "Um die Mittagszeit, ohne genaue Uhrzeit",
            "spaet": "Spät am Tag, ohne genaue Uhrzeit oder ab einer Uhrzeit",
            "keine": "Sie nennt keinen Zeitwunsch",
        }),
        "kleinigkeit": ("noul", "Ist das eine Kleinigkeit?", {
            "true": "Ja, zum Beispiel ein Schalter tauschen, nur schauen oder klären, welches Ersatzteil nötig ist",
            "false": "Nein, das braucht eine richtige Reparatur oder es ist unklar",
        }),
        "strom": ("choice", "Womit wird der Gegenstand betrieben?", {
            "netz": "Netzstrom über Stecker",
            "akku": "Eingebauter oder wechselbarer Akku",
            "batterie": "Einwegbatterien",
            "mechanisch": "Ohne Strom",
            "unbekannt": "Geht aus dem Text nicht hervor",
        }),
        "marke": ("noul", "Nennt der Text eine Marke oder einen Hersteller?", {
            "true": "Ja", "false": "Nein",
        }),
        "vollstaendig": ("noul", "Sind das Gerät und sein Fehler beschrieben?", {
            "true": "Ja, beides steht im Text", "false": "Nein, mindestens eines fehlt",
        }),
    },
    "en": {
        "absicht": ("choice", "What does the person want with this message?", {
            "neu": "They describe an item or problem and want help repairing it",
            "absage": "They will not come or cancel and name no new time, even if they plan to get back later",
            "verschieben": "They keep an existing appointment and name a different time for it",
            "rueckfrage": "They have a general question",
        }),
        "wunsch": ("choice", "Which time does the person ask for?", {
            "1100": "11:00", "1130": "11:30", "1200": "12:00", "1230": "12:30",
            "1300": "13:00", "1330": "13:30", "1400": "14:00",
            "frueh": "Early in the day, no exact time",
            "mittel": "Around midday, no exact time",
            "spaet": "Late in the day, no exact time or from a given time on",
            "keine": "They do not name a time",
        }),
        "kleinigkeit": ("noul", "Is this a small job?", {
            "true": "Yes, for example replacing a switch, just having a look or finding out which spare part is needed",
            "false": "No, this needs a proper repair or it is unclear",
        }),
        "strom": ("choice", "What powers the item?", {
            "netz": "Mains power via a plug",
            "akku": "Built-in or replaceable rechargeable battery",
            "batterie": "Disposable batteries",
            "mechanisch": "No electricity",
            "unbekannt": "Not clear from the text",
        }),
        "marke": ("noul", "Does the text name a brand or manufacturer?", {
            "true": "Yes", "false": "No",
        }),
        "vollstaendig": ("noul", "Are the device and its fault both described?", {
            "true": "Yes, both are in the text", "false": "No, at least one is missing",
        }),
    },
}


def read_tickets():
    rows = []
    with (Path(__file__).parent / "zusatz.tsv").open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            ident, *labels, text = line.rstrip("\n").split("\t")
            rows.append((ident, dict(zip(FIELDS, labels)), text))
    return rows


def request(lang):
    questions = {}
    for name, (kind, instructions, criteria) in QUESTIONS[lang].items():
        questions[name] = {"type": kind, "instructions": instructions, "criteria": criteria}
    return questions


def run(output, model, lang):
    questions = request(lang)
    with open(output, "w", encoding="utf-8") as out:
        for ident, labels, text in read_tickets():
            start = time.monotonic()
            row = {"id": ident, "soll": labels, "fehler": None}
            try:
                reply = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": text, "questions": questions,
                })["answers"]
                row["ist"] = {
                    name: value.get("choice", value.get("noul")) for name, value in reply.items()
                }
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


def evaluate(root):
    for path in sorted(Path(root).glob("*.jsonl")):
        rows = [json.loads(line) for line in path.open(encoding="utf-8")]
        good = [row for row in rows if not row["fehler"]]
        if not good:
            print(path.stem, "keine Antwort", rows[0]["fehler"][:120])
            continue
        parts = []
        for name in FIELDS:
            hits = 0
            for row in good:
                value, expected = row["ist"][name], row["soll"][name]
                if QUESTIONS["de"][name][0] == "noul":
                    hits += (value >= 0.5) == (expected == "1")
                else:
                    hits += value == expected
            parts.append(f"{name} {hits}/{len(good)}")
        seconds = statistics.median(row["sekunden"] for row in good[1:])
        print(f"{path.stem:26} " + " | ".join(parts) + f" | {seconds:.2f} s | Fehler {len(rows) - len(good)}")
        wrong = Counter(
            (row["soll"]["wunsch"], row["ist"]["wunsch"]) for row in good
            if row["ist"]["wunsch"] != row["soll"]["wunsch"]
        )
        print("    Wunsch falsch:", wrong.most_common(6))


def main():
    if sys.argv[1] == "lauf":
        run(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "de")
    else:
        evaluate(sys.argv[2])


if __name__ == "__main__":
    main()
