#!/usr/bin/env python3
"""Counts how often names and synonyms of the catalog appear in data and proposes new synonyms.

Counts every name and synonym in the German records of the Open Repair Data (category and problem text)
and, with --tickets, in the title and fault of our own tickets.

Proposals come from the titles of our tickets with a target value (--targets), because the free text of
the Open Repair Data describes faults and parts, not the object. A word of the title becomes a proposal
when at least --min tickets of the entry contain it, at least --share of all tickets with that word belong
to the entry, and the word is not yet a name or synonym of any entry. Tickets and proposals stay on this
computer, only reviewed words go into the catalog, see
docs/adr/0048-keine-personenbezogenen-daten-nach-aussen-geben.adoc.

The target values may use older keys. They are matched by the id of the form in the third part.

Run in the repository root:
    python3 katalog/synonyms.py [--tickets ~/bench/vorabtest/tickets.json --targets ~/bench/vorabtest/soll.tsv]
                                [--keys k1,k2] [--described] [--out DIR]

Prints names and synonyms found nowhere and the proposals, with --out writes counts.tsv and proposals.tsv.
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CATALOG = Path("katalog/kategorien.tsv")
ORDS = [Path(f"quellen/openrepair-data/OpenRepairData_v0.3_aggregate_202607_{kind}.csv") for kind in ("eee", "non-eee")]
WORD = re.compile(r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß-]{3,}")
# Words of ticket titles that name no object
STOP = {"defekt", "kaputt", "reparatur", "repair", "café", "cafe", "anfrage", "anmeldung", "termin", "geht",
        "nicht", "mehr", "funktioniert", "problem", "hilfe", "frage", "gerät", "geräte", "alte", "alter", "altes",
        "neue", "neuer", "neues", "meine", "mein", "unser", "unsere", "bitte", "danke", "hallo", "noch", "auch",
        "oder", "und", "mit", "ohne", "kabel", "schalter", "akku", "batterie", "stecker", "taste", "deckel"}


def boundary(word):
    return re.compile(r"(?<![a-zäöüß])" + re.escape(word.lower()) + r"(?![a-zäöüß])")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tickets", type=Path, help="tickets.json with titel and defekt, stays local")
    parser.add_argument("--targets", type=Path, help="TSV with ticket and key, stays local")
    parser.add_argument("--keys", help="only these keys, separated by commas")
    parser.add_argument("--described", action="store_true", help="only entries with a description")
    parser.add_argument("--min", type=int, default=3)
    parser.add_argument("--share", type=float, default=0.6)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = list(csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t"))
    keys = set(args.keys.split(",")) if args.keys else {row["key"] for row in rows}
    if args.described:
        keys &= {row["key"] for row in rows if row["description"].strip()}

    texts = []
    for path in ORDS:
        for record in csv.DictReader(path.open(encoding="utf-8")):
            if record["country"] == "DEU":
                texts.append(f"{record['partner_product_category']} {record['problem']}".lower())
    tickets = json.loads(args.tickets.expanduser().read_text(encoding="utf-8")) if args.tickets else []
    ticket_texts = [f"{t.get('titel', '')} {t.get('defekt', '')}".lower() for t in tickets]

    counts = []
    for row in rows:
        if row["key"] not in keys:
            continue
        for kind, word in [("name", row["name"])] + [("synonym", s) for s in row["synonyms"].split(" | ") if s]:
            pattern = boundary(word)
            counts.append({"key": row["key"], "name": row["name"], "kind": kind, "word": word,
                           "ords": sum(1 for t in texts if pattern.search(t)),
                           "tickets": sum(1 for t in ticket_texts if pattern.search(t)) if tickets else ""})

    proposals = []
    if tickets and args.targets:
        by_form = {i: row["key"] for row in rows for i in row["form_ids"].split(" | ") if i}
        current = {row["key"] for row in rows}
        target = {}
        for line in csv.DictReader(args.targets.expanduser().open(encoding="utf-8"), delimiter="\t"):
            key = line["key"]
            if key not in current:
                parts = key.split(".")
                key = by_form.get(parts[2]) if len(parts) > 2 else None
            if key:
                target[str(line["ticket"])] = key
        known = {w.lower() for row in rows for w in [row["name"]] + row["synonyms"].split(" | ") if w}
        known |= {part.strip().lower() for row in rows for part in re.split(r"[/(),]", row["name"]) if part.strip()}
        names = {row["key"]: row["name"] for row in rows}
        per_word, per_entry_word, per_entry = Counter(), defaultdict(Counter), Counter()
        for ticket in tickets:
            words = {w.lower() for w in WORD.findall(str(ticket.get("titel", "")))} - STOP
            per_word.update(words)
            key = target.get(str(ticket.get("id")))
            if key:
                per_entry[key] += 1
                per_entry_word[key].update(words)
        for key, words in per_entry_word.items():
            if key not in keys:
                continue
            for word, n in words.most_common():
                if n < args.min:
                    break
                if word in known or n / per_word[word] < args.share:
                    continue
                proposals.append({"key": key, "name": names[key], "word": word, "tickets": n,
                                  "share": round(n / per_word[word], 2), "entry_tickets": per_entry[key]})

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        for name, data in (("counts.tsv", counts), ("proposals.tsv", proposals)):
            with (args.out / name).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(data[0]) if data else ["key"], delimiter="\t")
                writer.writeheader()
                writer.writerows(data)
        print(f"{len(counts)} Wörter gezählt, {len(proposals)} Vorschläge in {args.out}")
        return
    for c in counts:
        if c["ords"] == 0 and not c["tickets"]:
            print(f"nirgends gefunden\t{c['key']}\t{c['name']}\t{c['kind']}\t{c['word']}")
    for p in proposals:
        print(f"Vorschlag\t{p['key']}\t{p['name']}\t{p['word']}\t{p['tickets']} von {p['entry_tickets']} Tickets\tAnteil {p['share']}")


if __name__ == "__main__":
    main()
