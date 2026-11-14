#!/usr/bin/env python3
"""Collects the event ids of our initiative on reparatur-initiativen.org, see docs/adr/0051.

The anstiftung gives every event (Termin) an id. Our export in the format of the Open Repair Data
carries it as an extra column, so the anstiftung could take over the rows as well. The public map
endpoint only lists events from the first day of the current month, so the script has to run before
each event to catch its id. Older ids come from the column Url of the Laufzettel download, which
stays local because it holds the defects. Only date, id and source go to docs/ora/anstiftung/events.tsv.

Run in the repository root:
    python3 eval/ora/anstiftung_events.py [--laufzettel ../Laufzettel-Download-Makerspace-Guetersloh-e-V-.csv]

Only the standard library is used.
"""

import argparse
import csv
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "docs" / "ora" / "anstiftung" / "events.tsv"
WORKSHOP = 17503
URL = f"https://www.reparatur-initiativen.de/workshops/ajaxGetAllWorkshopsForMap?workshopUid={WORKSHOP}"


def load():
    if not EVENTS.exists():
        return {}
    return {row["event_date"]: row for row in csv.DictReader(EVENTS.open(encoding="utf-8"), delimiter="\t")}


def from_map():
    request = urllib.request.Request(URL, headers={"X-Requested-With": "XMLHttpRequest", "User-Agent": "MANUEL"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    for workshop in data.get("workshops", []):
        for event in workshop.get("Workshop", {}).get("Events", []):
            if event.get("status") == 1:
                yield event["datumstart_formatted"], str(event["uid"]), "Karte"


def from_laufzettel(path):
    with open(path, encoding="utf-8-sig") as file:
        dialect = ";" if ";" in file.readline() else ","
        file.seek(0)
        for row in csv.DictReader(file, delimiter=dialect):
            match = re.search(r"event=(\d+),(\d{4}-\d{2}-\d{2})", row.get("Url", ""))
            if match:
                yield match.group(2), match.group(1), "Laufzettel"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--laufzettel", type=Path)
    args = parser.parse_args()
    events = load()
    found = list(from_map())
    if args.laufzettel:
        found += list(from_laufzettel(args.laufzettel))
    added = 0
    for date, uid, source in found:
        known = events.get(date)
        if known and known["event_id"] != uid:
            print(f"{date}: bekannt {known['event_id']}, gefunden {uid}, bitte prüfen")
            continue
        if not known:
            events[date] = {"event_date": date, "event_id": uid, "source": source}
            added += 1
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["event_date", "event_id", "source"], delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(events[d] for d in sorted(events))
    print(f"{added} neu, {len(events)} Termine in {EVENTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
