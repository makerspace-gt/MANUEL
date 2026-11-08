#!/usr/bin/env python3
"""Macht aus den Zammad-Exporten tickets-Repair*.xlsx die Datei tickets.json für die Läufe.

Das Jahr stammt aus dem Dateinamen. Die Datei enthält echte Tickets und gehört nicht ins Repo.

Aufruf:
    python3 MANUEL/eval/decision/tickets_export.py [Muster der Exporte] [Ausgabe]
"""

import glob
import json
import re
import sys

from nachrichten import sheet_rows

FIELDS = {
    "titel": "Title", "defekt": "Defekt", "hack": "Hack", "marke": "Marke",
    "bezeichnung": "Bezeichnung", "strom": "Stromversorgung", "ergebnis": "Ergebnis",
    "tags": "Tags", "vde": "VDE 0701/0702 geprüft", "artikel": "Article Count",
}


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "tickets-Repair*.xlsx"
    output = sys.argv[2] if len(sys.argv) > 2 else "tickets.json"
    tickets = {}
    for path in sorted(glob.glob(pattern)):
        year = re.search(r"(\d{4})", path).group(1)
        head, rows = sheet_rows(path)
        index = {name: i for i, name in enumerate(head)}
        for row in rows:
            number = (row[0] if row else "").split(".")[0]
            if not number.isdigit():
                continue
            entry = {"id": number, "jahr": year}
            for key, column in FIELDS.items():
                position = index.get(column)
                value = row[position] if position is not None and position < len(row) else ""
                entry[key] = (value or "").strip()
            if entry["artikel"].endswith(".0"):
                entry["artikel"] = entry["artikel"][:-2]
            tickets[number] = entry
    json.dump(list(tickets.values()), open(output, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(len(tickets), "Tickets nach", output)


if __name__ == "__main__":
    main()
