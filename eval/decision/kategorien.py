#!/usr/bin/env python3
"""Liest den Kategorienbaum aus database.sql von mapped-repair-events.

Aufruf im Wurzelverzeichnis des Repos:
    python3 eval/decision/kategorien.py eval/decision/kategorien.json
"""

import json
import re
import sys
from pathlib import Path

SQL = Path("mapped-repair-events/config/sql/init/database.sql")


def fields(row):
    """Trennt eine SQL-Zeile an Kommas außerhalb von Anführungszeichen."""
    return [value.strip() for value in re.findall(r"\s*'(?:[^'\\]|\\.)*'|[^,]+", row)]


def main():
    text = SQL.read_text(encoding="utf-8", errors="replace")
    start = text.index("INSERT INTO `categories`")
    start = text.index("VALUES", start)
    block = text[start:text.index(";\n", start)]
    result = []
    for row in re.findall(r"^\((.*)\),?$", block, re.M):
        values = fields(row)
        result.append({
            "id": int(values[0]),
            "name": values[1].strip("'").replace("\\'", "'"),
            "sichtbar": values[3] == "1",
            "parent": None if values[6] == "NULL" else int(values[6]),
        })
    Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(result), "Kategorien")


if __name__ == "__main__":
    main()
