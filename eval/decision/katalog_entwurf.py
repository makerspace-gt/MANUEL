#!/usr/bin/env python3
"""Lässt ein Sprachmodell Beschreibungen und Synonyme für den Katalog entwerfen.

Für jeden Eintrag bekommt das Modell die Namen im Formular, die ORA-Gruppe und die ähnlichsten
anderen Einträge. Die Beschreibung soll vor allem die Abgrenzung zu diesen Nachbarn nennen.
Die Entwürfe prüfen Menschen, bevor sie in den Katalog kommen.

Aufruf:
    python3 katalog_entwurf.py <eingabe.json> <Ausgabe.jsonl> <Chat-Modell>
"""

import json
import sys
import time

from decision import post
from echt2 import embed, unit

STROM = ["230 V", "mit Netzteil", "Batterie", "Akku", "ohne Kabel (Mechanik)"]
SCHEMA = {
    "type": "object",
    "properties": {
        "beschreibung_de": {"type": "string"},
        "synonyme_de": {"type": "array", "items": {"type": "string"}},
        "name_en": {"type": "string"},
        "beschreibung_en": {"type": "string"},
        "synonyme_en": {"type": "array", "items": {"type": "string"}},
        "strom": {"type": "array", "items": {"type": "string", "enum": STROM}},
    },
    "required": ["beschreibung_de", "synonyme_de", "name_en", "beschreibung_en", "synonyme_en", "strom"],
}
PROMPT = """Du hilfst bei einem Katalog für ein Repair Café. Gäste bringen defekte Gegenstände mit.
Schreibe für diesen Eintrag eine kurze Beschreibung und Synonyme.

Eintrag: {name}
Namen im Formular: {mitglieder}
Gruppe im Open Repair Data Standard: {ora}
Ähnliche andere Einträge im Katalog: {nachbarn}

Regeln:
- beschreibung_de ist ein Satz mit höchstens 25 Wörtern. Er sagt, was der Gegenstand ist, und grenzt ihn
  von den ähnlichen Einträgen ab, wenn eine Verwechslung naheliegt.
- synonyme_de sind höchstens 6 andere deutsche Wörter, mit denen Gäste denselben Gegenstand bezeichnen.
  Keine Marken, keine Oberbegriffe, keine Namen der ähnlichen Einträge.
- name_en, beschreibung_en und synonyme_en sind dasselbe auf Englisch, britisch oder amerikanisch.
- strom ist die übliche Stromversorgung, eine oder mehrere der erlaubten Angaben.
Antworte nur mit JSON."""


def main():
    source, output, model = sys.argv[1:4]
    entries = json.load(open(source, encoding="utf-8"))
    names = [e["name"] for e in entries]
    vectors = []
    for start in range(0, len(names), 64):
        vectors += [unit(v) for v in embed(names[start:start + 64])]
    with open(output, "w", encoding="utf-8") as out:
        for index, entry in enumerate(entries):
            scored = sorted(((sum(a * b for a, b in zip(vectors[index], v)), n)
                             for v, n in zip(vectors, names) if n != entry["name"]), reverse=True)
            neighbours = [n for _, n in scored[:6]]
            row = {"name": entry["name"], "nachbarn": neighbours, "fehler": None}
            start = time.monotonic()
            try:
                reply = post("/api/chat", {
                    "model": model, "stream": False, "think": False, "keep_alive": 600,
                    "format": SCHEMA, "options": {"temperature": 0, "seed": 42, "num_ctx": 4096},
                    "messages": [{"role": "user", "content": PROMPT.format(
                        name=entry["name"],
                        mitglieder=", ".join(f"{m['ober']} / {m['name']}" for m in entry["mitglieder"]),
                        ora=entry["ora"], nachbarn=", ".join(neighbours))}],
                })
                row.update(json.loads(reply["message"]["content"]))
            except Exception as problem:  # Ein Fehler soll den Rest des Laufs nicht verhindern
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
