#!/usr/bin/env python3
"""Prepares the backfill of repairs from 2024 to 2026 to Restarters.net, see docs/adr/0036.

Reads the local Zammad exports, the team's target values and the statistics, and writes a local
preview with one row per device. Nothing is sent. Columns with personal data such as customer or
owner are never read. The defect is free text and is only used once the ticket is anonymized
after docs/adr/0038, until then it is left out.

The date of a repair comes from the ticket's tags. The team tags each ticket with the date of the
event, a postponed ticket gets one tag per event and the last one counts. Older tickets only carry the
month, then the one date of the statistics in that month counts. Without a usable tag the date is the last
date of the statistics between creating and closing the ticket, or Pending till if it is a date of the
statistics. The one Laufzettel of 2025 already reached the Open
Repair Alliance via anstiftung and is left out.

Run in the repository root:
    python3 eval/restarters/backfill.py --exports "../tickets-Repair Café-Created *.xlsx" \\
        --targets ../tickets-kontrolle-d3.xlsx --statistics Repair-Café-Statistik.ods \\
        --laufzettel ../Laufzettel-Download-Makerspace-Guetersloh-e-V-.csv --out PREVIEW.tsv

The preview contains ticket numbers and stays local, like the exports.
"""

import argparse
import collections
import csv
import datetime as dt
import glob
import importlib.util
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "katalog" / "kategorien.tsv"
FORM = ROOT / "quellen" / "anstiftung" / "kategorien.csv"
SHEET = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

EXPORT_COLUMNS = ["#", "Tags", "Ergebnis", "Marke", "Pending till", "Created At", "Closed At"]
TARGET_COLUMNS = ["Ticket", "Kategorie", "Kategorie richtig"]
# Reasons of "nicht erfolgt" with a barrier Restarters accepts. "Abnutzung zu groß" matches the standard's
# "Item too worn out", which the API of Restarters does not accept, so it goes without a barrier.
BARRIERS = {
    "Ersatzteil nicht erhältlich": "Spare parts not available",
    "Ersatzteil zu teuer": "Spare parts too expensive",
    "Öffnung des Gerätes nicht möglich": "No way to open the product",
    "Reparaturinformationen nicht verfügbar": "Repair information not available",
    "Hilfsmittel oder Zubehör fehlt": "Lack of equipment",
}


def xlsx_rows(path, columns, sheet_name=None):
    """Rows of a sheet as dicts, but only with the given columns, all others are skipped."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            shared = ["".join(t.text or "" for t in si.iter(SHEET + "t"))
                      for si in ET.fromstring(archive.read("xl/sharedStrings.xml")).iter(SHEET + "si")]
        target = sorted(n for n in names if n.startswith("xl/worksheets/sheet"))[0]
        if sheet_name:
            rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
            for sheet in ET.fromstring(archive.read("xl/workbook.xml")).iter(SHEET + "sheet"):
                if sheet.get("name") == sheet_name:
                    link = rels[sheet.get(REL + "id")]
                    target = link.lstrip("/") if link.startswith("/") else "xl/" + link
        header = None
        for row in ET.fromstring(archive.read(target)).iter(SHEET + "row"):
            values = {}
            for cell in row.iter(SHEET + "c"):
                column = "".join(ch for ch in cell.get("r") if ch.isalpha())
                if header is not None and column not in header:
                    continue
                value = cell.find(SHEET + "v")
                text = value.text if value is not None else ""
                if cell.get("t") == "s":
                    text = shared[int(text)]
                elif cell.get("t") == "inlineStr":
                    text = "".join(t.text or "" for t in cell.iter(SHEET + "t"))
                values[column] = (text or "").strip()
            if header is None:
                if columns[0] in values.values():
                    header = {column: name for column, name in values.items() if name in columns}
                continue
            yield {header[column]: value for column, value in values.items()}


def catalog_index():
    """Every name, synonym and form name in lower case, pointing to its catalog row."""
    form = {row["id"]: row["category"] for row in csv.DictReader(FORM.open(encoding="utf-8"))}
    index = {}
    for row in csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t"):
        names = [row["name"], row["name"].split(" (")[0]] + [s for s in row["synonyms"].split(" | ") if s]
        if row["key"].count(".") == 2:  # no own distinction, the categories of the form belong to it
            names += [form[i] for i in row["form_ids"].split(" | ") if i in form]
        for name in names:
            index.setdefault(name.lower(), row)
    return index


def restarters_category(entry):
    """Category on Restarters.net from the catalog. The id is the second part of the key, 0 means the size decides."""
    restarters_id = entry["key"].split(".")[1]
    note = "Größe klären" if restarters_id == "0" else entry["status"].partition(", ")[2]
    return {"restarters_id": "" if restarters_id == "0" else restarters_id,
            "restarters_category": entry["restarters_category"], "note": note}


def event_dates(statistics):
    """Dates of the statistics. A Sunday or Monday moves to the Saturday before, with the original kept.

    The Repair Café takes place on Saturdays. Some dates in the first half of 2025 were entered one or
    two days late, the Laufzettel of 2025-05-03 for example appears as 2025-05-04 in the statistics.
    """
    spec = importlib.util.spec_from_file_location("sharecard_script", ROOT / "sharecard" / "sharecard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dates, moved = [], {}
    for event in module.read_events(statistics):
        if (event.get("processed") or 0) <= 0:
            continue
        date = event["date"]
        if date.weekday() in (6, 0):
            saturday = date - dt.timedelta(days=(date.weekday() + 2) % 7)
            moved[saturday] = date
            date = saturday
        dates.append(date)
    return sorted(dates), moved


def tag_date(tags, dates):
    """Date of the event from the tags, the source of that date and a note for the team."""
    days, months, others = [], [], []
    for tag in (t.strip() for t in tags.split(",")):
        try:
            days.append(dt.date.fromisoformat(tag))
            continue
        except ValueError:
            pass
        if len(tag) == 7 and tag[4] == "-" and tag.replace("-", "").isdigit():
            months.append(tag)
        elif tag:
            others.append(tag)
    if days:
        date = max(days)
        return date, "Tag", "" if date in dates else f"Datum {date.isoformat()} fehlt in der Statistik"
    if months:
        month = max(months)
        in_month = [d for d in dates if d.isoformat().startswith(month)]
        if len(in_month) == 1:
            return in_month[0], "Monat", ""
        return None, "", f"Monat {month} hat {len(in_month)} Termine in der Statistik"
    special = [t for t in others if t[:4].isdigit()]
    return None, "", f"Tag {special[0]}" if special else ""


def status(result):
    """Status and barrier for Restarters, the action and a note for the team."""
    if not result or result == "No-Show":
        return "", "", "nicht melden", "ohne Ergebnis" if not result else "nicht erschienen"
    main, _, reason = result.partition("::")
    if main == "gelungen":
        return "Fixed", "", "melden", ""
    if main == "teilweise gelungen":
        return "", "", "klären", "teilweise gelungen"
    if main == "vertagt":
        return "Repairable", "", "melden", reason
    if main.startswith("abgebrochen"):
        return "End of life", "", "melden", "abgebrochen"
    if main == "nicht erfolgt":
        if reason in BARRIERS:
            return "End of life", BARRIERS[reason], "melden", ""
        if reason == "Abnutzung zu groß":
            return "End of life", "", "melden", "Hindernis Item too worn out nimmt Restarters nicht an"
        return "", "", "klären", f"nicht erfolgt, {reason or 'ohne Grund'}"
    return "", "", "klären", f"unbekanntes Ergebnis {result}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--exports", required=True)
    parser.add_argument("--targets", required=True, type=Path)
    parser.add_argument("--statistics", required=True, type=Path)
    parser.add_argument("--laufzettel", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    catalog = catalog_index()
    dates, moved = event_dates(args.statistics)
    targets = {}
    for row in xlsx_rows(args.targets, TARGET_COLUMNS, "Kontrolle"):
        if row.get("Ticket"):
            targets[row["Ticket"].split(".")[0]] = row.get("Kategorie richtig") or row.get("Kategorie") or ""
    reported = set()
    with args.laufzettel.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day, month, year = (row.get("Datum Reparaturveranstaltung") or "..").split(".")[:3]
            if year.strip() == "2025":
                reported.add((f"{year.strip()}-{month}-{day}", (row.get("Unterkategorie") or "").strip().lower()))

    rows, seen = [], set()
    for path in sorted(glob.glob(args.exports)):
        for ticket in xlsx_rows(path, EXPORT_COLUMNS):
            number = ticket.get("#", "").split(".")[0]
            if not number.isdigit() or number in seen:
                continue
            seen.add(number)
            closed = (ticket.get("Closed At") or "")[:10]
            pending = (ticket.get("Pending till") or "")[:10]
            created = dt.date.fromisoformat((ticket.get("Created At") or "1900-01-01")[:10])
            date, source, tag_note = tag_date(ticket.get("Tags", ""), dates)
            if date is None and closed:
                before = [d for d in dates if created <= d <= dt.date.fromisoformat(closed)]
                date = before[-1] if before else None
                source = "Anlegen und Schließen" if date else ""
            if date is None and pending and created <= dt.date.fromisoformat(pending) and \
                    dt.date.fromisoformat(pending) in dates:
                date, source = dt.date.fromisoformat(pending), "Pending till"
            repair_status, barrier, action, note = status(ticket.get("Ergebnis", ""))
            target = targets.get(number, "")
            entry = catalog.get(target.lower()) if target and target != "??" else None
            mapped = restarters_category(entry) if entry else None
            notes = [n for n in (note, tag_note) if n]
            if action != "nicht melden":
                if entry is None:
                    action, notes = "klären", notes + ["Kategorie offen" if not target or target == "??"
                                                       else f"Kategorie {target} nicht im Katalog"]
                elif not mapped or not mapped["restarters_id"]:
                    action, notes = "klären", notes + [mapped["note"] if mapped else "ORA-Gruppe ohne Zuordnung"]
                elif mapped["note"]:
                    notes.append(mapped["note"])
                if entry is not None and not entry["name_en"]:
                    action, notes = "klären", notes + ["englischer Name fehlt im Katalog"]
                if date is None:
                    following = [d for d in dates if d >= created]
                    guess = f", geschätzt {following[0].isoformat()}" if following else ""
                    action, notes = "klären", notes + [f"Termin unbekannt{guess}"]
                elif (date.isoformat(), target.lower()) in reported:
                    action, notes = "auslassen", notes + ["schon als Laufzettel bei der anstiftung"]
                if date in moved:
                    notes.append(f"Statistik nennt {moved[date].isoformat()}, gesetzt auf den Samstag davor")
            rows.append({
                "ticket": number, "created": created.isoformat() if ticket.get("Created At") else "",
                "closed": closed, "event_date": date.isoformat() if date else "",
                "date_source": source, "target_category": target,
                "catalog_key": entry["key"] if entry else "", "item_type": entry["name_en"] if entry else "",
                "ora_group": entry["ora_group"] if entry else "",
                "restarters_id": mapped["restarters_id"] if mapped else "",
                "restarters_category": mapped["restarters_category"] if mapped else "",
                "brand": ticket.get("Marke", ""), "result": ticket.get("Ergebnis", ""),
                "repair_status": repair_status, "barrier": barrier, "action": action, "note": ", ".join(notes),
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    by_year = collections.Counter((r["event_date"][:4] or "ohne Termin", r["action"]) for r in rows)
    print(len(rows), "Tickets in", args.out)
    for (year, action), count in sorted(by_year.items()):
        print(f"  {year} {action}: {count}")
    print("  Herkunft des Termins:", dict(collections.Counter(r["date_source"] or "keine" for r in rows)))
    print("  Status beim Melden:", dict(collections.Counter(r["repair_status"] for r in rows if r["action"] == "melden")))
    print("  Gründe zum Klären:", dict(collections.Counter(r["note"].split(",")[0] for r in rows if r["action"] == "klären")
                                   .most_common(8)))


if __name__ == "__main__":
    main()
