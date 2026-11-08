#!/usr/bin/env python3
"""Lets a language model draft descriptions and synonyms for the catalog.

For each entry the model gets the names in the form, the ORA group and the most similar
other entries. The description should above all name the distinction from these neighbours.
People check the drafts before they go into the catalog.

Usage:
    python3 catalog_draft.py <input.json> <output.jsonl> <chat model>
"""

import json
import sys
import time

from decision import post
from real2 import embed, unit

POWER = ["230 V", "mit Netzteil", "Batterie", "Akku", "ohne Kabel (Mechanik)"]
SCHEMA = {
    "type": "object",
    "properties": {
        "beschreibung_de": {"type": "string"},
        "synonyme_de": {"type": "array", "items": {"type": "string"}},
        "name_en": {"type": "string"},
        "beschreibung_en": {"type": "string"},
        "synonyme_en": {"type": "array", "items": {"type": "string"}},
        "strom": {"type": "array", "items": {"type": "string", "enum": POWER}},
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
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                row["fehler"] = f"{problem} {detail}"[:300]
            row["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
