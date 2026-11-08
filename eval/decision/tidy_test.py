#!/usr/bin/env python3
"""Prüft die Einordnung am bereinigten Datensatz der Datenpotenzialanalyse.

Laufzettel-tidy.csv enthält 281 Geräte von 2019 bis 2021 mit den Rohwerten und den von Hand
vergebenen Werten für Gerät, Kategorie, Stromversorgung und Defekt. Das ergibt echte Sollwerte.
Die Daten stehen unter CC BY 4.0 und enthalten keine Personendaten.

Aufruf:
    python3 tidy_test.py <Laufzettel-tidy.csv> <Werte.csv> <cf-mf.csv> <Ausgabe.jsonl> <Modell>
    python3 tidy_test.py auswertung <Ausgabe.jsonl>
    python3 tidy_test.py variante <Laufzettel-tidy.csv> <cf-mf.csv> <Ausgabe.jsonl> <Modell> <Sprachmodell>

Die Variante sucht ähnliche Kategorien nur mit der Gerätebezeichnung statt mit dem ganzen Text,
wie es die Kette aus echt5.py tut, und merkt sich, an welcher Stelle der Sollwert in der Vorauswahl
steht. Unter 70 Prozent Sicherheit entscheidet zusätzlich das Sprachmodell.
"""

import collections
import csv
import json
import sys
import time

from decision import post
from echt2 import embed, unit

OBER = {
    "Elektro Sonstiges": "Elektro divers",
    "Möbel (Holzbearbeitung)": "Möbel/Holz",
    "Handy / Smartphone / Tablet": "Smartphone/Tablet",
}
STROM = {
    "230 V": "Direkt am Stromnetz über Stecker und Kabel",
    "mit Netzteil": "Über ein externes Netzteil",
    "Akku": "Mit eingebautem oder wechselbarem Akku",
    "Batterie": "Mit Einwegbatterien",
    "ohne Kabel (Mechanik)": "Ohne Strom, rein mechanisch",
}


def run(tidy_file, values_file, csv_file, output, model):
    with open(csv_file, encoding="utf-8", errors="replace") as handle:
        names = sorted({f"{r['Oberkategorie']} / {r['Unterkategorie']}" for r in csv.DictReader(handle)})
    vectors = []
    for start in range(0, len(names), 64):
        vectors += [unit(v) for v in embed(names[start:start + 64])]
    with open(values_file, encoding="utf-8") as handle:
        defects = sorted({r["Defekt"] for r in csv.DictReader(handle)} - {"", "NA", "Fortsetzung"})
    with open(tidy_file, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    with open(output, "w", encoding="utf-8") as out:
        for index, row in enumerate(rows):
            device = row["Gerät/Gegenstand-raw"]
            defect = row["Defekt-raw"]
            if device in ("", "NA") and defect in ("", "NA"):
                continue
            state = device if device not in ("", "NA") else ""
            if defect not in ("", "NA"):
                state = f"{state}. Defekt: {defect}".strip(". ")
            start = time.monotonic()
            result = {
                "zeile": index, "text": state, "soll_geraet": row["Gerät/Gegenstand"],
                "soll_ober": OBER.get(row["Reparaturkategorie"], row["Reparaturkategorie"]),
                "soll_strom": row["Stromversorgung"], "soll_defekt": row["Defekt"], "fehler": None,
            }
            try:
                query = unit(embed([state])[0])
                scored = sorted(
                    ((sum(a * b for a, b in zip(query, vector)), name)
                     for vector, name in zip(vectors, names)),
                    reverse=True,
                )
                answers = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {
                        "kategorie": {
                            "type": "choice",
                            "instructions": "Welche Kategorie beschreibt diesen Gegenstand am besten?",
                            "criteria": {name: None for _, name in scored[:25]},
                        },
                        "strom": {
                            "type": "choice",
                            "instructions": "Womit wird dieser Gegenstand üblicherweise betrieben?",
                            "criteria": STROM,
                        },
                        "defekt": {
                            "type": "choice",
                            "instructions": "Welche Beschreibung passt am besten zum Defekt?",
                            "criteria": {name: None for name in defects},
                        },
                    },
                })["answers"]
                for name in ("kategorie", "strom", "defekt"):
                    result[name] = answers[name]["choice"]
                    result[name + "_p"] = answers[name]["probabilities"][answers[name]["choice"]]
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                result["fehler"] = f"{problem} {detail}"[:300]
            result["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()


def variant(tidy_file, csv_file, output, model, chat_model):
    with open(csv_file, encoding="utf-8", errors="replace") as handle:
        names = sorted({f"{r['Oberkategorie']} / {r['Unterkategorie']}" for r in csv.DictReader(handle)})
    vectors = []
    for start in range(0, len(names), 64):
        vectors += [unit(v) for v in embed(names[start:start + 64])]
    with open(tidy_file, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    with open(output, "w", encoding="utf-8") as out:
        for index, row in enumerate(rows):
            device, defect = row["Gerät/Gegenstand-raw"], row["Defekt-raw"]
            if device in ("", "NA") and defect in ("", "NA"):
                continue
            label = device if device not in ("", "NA") else defect
            state = label if defect in ("", "NA") or label == defect else f"{label}. Defekt: {defect}"
            result = {"zeile": index, "text": state, "soll_geraet": row["Gerät/Gegenstand"],
                      "soll_ober": OBER.get(row["Reparaturkategorie"], row["Reparaturkategorie"]),
                      "fehler": None, "sprachmodell": None}
            start = time.monotonic()
            try:
                query = unit(embed([label])[0])
                scored = sorted(
                    ((sum(a * b for a, b in zip(query, vector)), name)
                     for vector, name in zip(vectors, names)),
                    reverse=True,
                )
                shortlist = [name for _, name in scored[:25]]
                goal = [i for i, name in enumerate(shortlist)
                        if name.split(" / ", 1)[1].lower() == row["Gerät/Gegenstand"].lower()]
                result["rang"] = goal[0] + 1 if goal else None
                answer = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"kategorie": {
                        "type": "choice",
                        "instructions": "Welche Kategorie beschreibt diesen Gegenstand am besten?",
                        "criteria": {name: None for name in shortlist},
                    }},
                })["answers"]["kategorie"]
                result["kategorie"] = answer["choice"]
                result["kategorie_p"] = answer["probabilities"][answer["choice"]]
                result["sekunden"] = round(time.monotonic() - start, 3)
                if result["kategorie_p"] < 0.7:
                    listed = "\n".join(f"{i + 1}. {name}" for i, name in enumerate(shortlist))
                    reply = post("/api/chat", {
                        "model": chat_model, "stream": False, "think": False, "keep_alive": 600,
                        "format": {"type": "object", "properties": {"nummer": {"type": "integer"}},
                                   "required": ["nummer"]},
                        "options": {"temperature": 0, "seed": 42, "num_ctx": 4096},
                        "messages": [{"role": "user", "content": (
                            "Welche Kategorie beschreibt den Gegenstand am besten? "
                            f"Antworte mit der Nummer.\n\nGegenstand: {state}\n\n{listed}")}],
                    })
                    number = json.loads(reply["message"]["content"])["nummer"]
                    if 1 <= number <= len(shortlist):
                        result["sprachmodell"] = shortlist[number - 1]
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                result["fehler"] = f"{problem} {detail}"[:300]
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()


def evaluate(path):
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    good = [r for r in rows if not r["fehler"]]
    print(len(rows), "Zeilen,", len(rows) - len(good), "Fehler")

    def score(label, items, check):
        hits = sum(check(r) for r in items)
        print(f"{label:28} {hits:3}/{len(items):3} {hits / max(1, len(items)):4.0%}")

    known = [r for r in good if r["soll_geraet"] not in ("", "NA")]
    score("Gerät exakt", known, lambda r: r["kategorie"].split(" / ", 1)[1].lower() == r["soll_geraet"].lower())
    score("Oberkategorie", [r for r in good if r["soll_ober"] not in ("", "NA")],
          lambda r: r["kategorie"].split(" / ", 1)[0] == r["soll_ober"])
    score("Stromversorgung", [r for r in good if r["soll_strom"] in STROM], lambda r: r["strom"] == r["soll_strom"])
    score("Defekt", [r for r in good if r["soll_defekt"] not in ("", "NA", "Fortsetzung")],
          lambda r: r["defekt"] == r["soll_defekt"])
    wrong = collections.Counter(
        (r["soll_geraet"], r["kategorie"].split(" / ", 1)[1]) for r in known
        if r["kategorie"].split(" / ", 1)[1].lower() != r["soll_geraet"].lower()
    )
    print(wrong.most_common(30))
    print(collections.Counter((r["soll_defekt"], r["defekt"]) for r in good if r["soll_defekt"] != r["defekt"]).most_common(14))


if __name__ == "__main__":
    if sys.argv[1] == "auswertung":
        evaluate(sys.argv[2])
    elif sys.argv[1] == "variante":
        variant(*sys.argv[2:7])
    else:
        run(*sys.argv[1:6])
