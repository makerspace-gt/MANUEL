#!/usr/bin/env python3
"""Wertet die Ergebnisse von decision.py aus.

Aufruf im Verzeichnis eval/decision:
    python3 auswerten.py [Verzeichnis] [--details Dateiname]
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def read(path):
    rows = [json.loads(line) for line in path.open(encoding="utf-8")]
    return rows, [row for row in rows if not row["fehler"]]


def auc(rows):
    """Anteil der Paare, in denen ein gefährlicher Fall höher liegt als ein harmloser."""
    high = [row["sicherheit"] for row in rows if row["soll_sicherheit"]]
    low = [row["sicherheit"] for row in rows if not row["soll_sicherheit"]]
    pairs = sum((a > b) + 0.5 * (a == b) for a in high for b in low)
    return pairs / (len(high) * len(low)) if high and low else float("nan")


def summary(path):
    rows, good = read(path)
    if not good:
        return f"{path.stem:34} keine Antwort, {rows[0]['fehler'][:90]}"
    hits = sum(row["kategorie"] == row["soll_kategorie"] for row in good)
    danger = [row for row in good if row["soll_sicherheit"]]
    safe = [row for row in good if not row["soll_sicherheit"]]
    missed = sum(row["sicherheit"] < 0.5 for row in danger)
    alarms = sum(row["sicherheit"] >= 0.5 for row in safe)
    limit = min((row["sicherheit"] for row in danger), default=0.0)
    forced = sum(row["sicherheit"] >= limit for row in safe)
    seconds = statistics.median(row["sekunden"] for row in good[1:])
    return (
        f"{path.stem:34} Kat {hits:2}/{len(good)} {hits / len(good):4.0%} | "
        f"Sicher verpasst {missed:2}/{len(danger)} Fehlalarm {alarms:2}/{len(safe)} AUC {auc(good):.3f} | "
        f"ohne Verpasste: Schwelle {limit:.3f} Fehlalarm {forced:2}/{len(safe)} | "
        f"{seconds:5.2f} s | Fehler {len(rows) - len(good)}"
    )


def details(path):
    _, good = read(path)
    print("Verpasst bei 0,5:")
    for row in good:
        if row["soll_sicherheit"] and row["sicherheit"] < 0.5:
            print(f"  {row['id']} {row['gruppe']:9} {row['sicherheit']:.3f}")
    print("Fehlalarm bei 0,5:")
    for row in good:
        if not row["soll_sicherheit"] and row["sicherheit"] >= 0.5:
            print(f"  {row['id']} {row['gruppe']:9} {row['sicherheit']:.3f}")
    wrong = Counter(
        (row["soll_kategorie"], row["kategorie"])
        for row in good if row["kategorie"] != row["soll_kategorie"]
    )
    print("Kategorie falsch:", wrong.most_common(12))
    groups = Counter(row["gruppe"] for row in good if row["soll_sicherheit"] and row["sicherheit"] < 0.5)
    print("Verpasst nach Gruppe:", dict(groups))


def main():
    args = sys.argv[1:]
    if "--details" in args:
        index = args.index("--details")
        name = args[index + 1]
        del args[index:index + 2]
        root = Path(args[0] if args else "results")
        details(root / name)
        return
    root = Path(args[0] if args else "results")
    for path in sorted(root.glob("*.jsonl")):
        print(summary(path))


if __name__ == "__main__":
    main()
