#!/usr/bin/env python3
"""Counts the indicators of the trial per appointment from an export of zammad/export_tickets.py, see
docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc and docs/adr/0040-mit-dem-ticket-categorizer-von-zammad-beginnen.adoc.

Only device tickets count, as in eval/enrich/tickets.py. The appointment is the first date tag, else the
month tag or the pending time. Old exports with the German fields of our Zammad and new ones with the fields
of zammad/objects.rb both work. The output holds sums only and may go into the repository.

    devices          device tickets of the appointment
    no_show          result No-show
    fixed            result Fixed or Partly fixed
    postponed        result Postponed
    not_repaired     result Not repaired or Aborted
    open             no result yet
    repair_rate      fixed among fixed, postponed and not repaired
    by_guest         owner is the agent Gast, the guest repaired the device
    repairers        distinct owners other than the agent Gast and nobody
    new_repairers    of these, accounts created on or after --new-since
    helpful          tag suggestion-helpful, indicator 3
    not_helpful      tag suggestion-not-helpful
    suggested        tag solution-suggested, MANUEL wrote a solution approach
    typed            device type filled
    differs          tag category-differs, d3:9b disagreed with the device type

Indicator 4, devices reported to Restarters, comes from the reporting workflow and is not counted here.

With --monthly a second table counts per month the devices with a result, the distinct owners who closed
a repair and among them the new ones, whose first closed repair in the export falls into that month.
Months before --warm-up only seed the known owners, because the export starts in 2024. The owner is the
person who closed the repair, not necessarily everyone who helped.

Run in the repository root:
    python3 -I eval/indicators/indicators.py EXPORT_DIR [--since 2026-12-05] [--out FILE.tsv]
        [--monthly FILE.tsv] [--warm-up 2025-01]
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "enrich"))
sys.path.insert(0, str(HERE.parent))

import tickets as source  # noqa: E402
from lauf import write_run  # noqa: E402

# Top level of the result in both languages, see zammad/result_tree.rb
OUTCOME = {
    "fixed": "fixed", "gelungen": "fixed", "partly fixed": "fixed", "teilweise gelungen": "fixed",
    "postponed": "postponed", "vertagt": "postponed",
    "not repaired": "not_repaired", "nicht erfolgt": "not_repaired",
    "aborted": "not_repaired", "abgebrochen": "not_repaired",
    "no-show": "no_show",
}
COLUMNS = ["appointment", "devices", "no_show", "fixed", "postponed", "not_repaired", "open", "repair_rate",
           "by_guest", "repairers", "new_repairers", "helpful", "not_helpful", "suggested", "typed", "differs"]


def outcome(ticket):
    value = ticket.get("repair_result") or ticket.get("ergebnis") or ""
    top = value.split("::")[0].split(":")[0].strip().lower()
    return OUTCOME.get(top, "open" if not top else "other")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path)
    parser.add_argument("--since", type=date.fromisoformat, help="first appointment to count")
    parser.add_argument("--guest-login", default="guest", help="login of the agent Gast")
    parser.add_argument("--new-since", type=date.fromisoformat, default=date(2026, 9, 15))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--monthly", type=Path)
    parser.add_argument("--warm-up", default="2025-01", help="first month to report in --monthly")
    args = parser.parse_args()

    tickets_file, tickets = source.load(args.export)
    users_file = args.export.expanduser() / "users.json"
    created = {u.get("login"): (u.get("created_at") or "")[:10]
               for u in json.loads(users_file.read_text(encoding="utf-8"))} if users_file.exists() else {}

    rows = defaultdict(lambda: {"owners": set(), **{c: 0 for c in COLUMNS[1:] if c != "repair_rate"}})
    for ticket in tickets:
        day = source.appointment(ticket)
        if day is None or (args.since and day < args.since):
            continue
        row = rows[day]
        row["devices"] += 1
        kind = outcome(ticket)
        if kind in row:
            row[kind] += 1
        owner = ticket.get("owner") or "-"
        if owner == args.guest_login:
            row["by_guest"] += 1
        elif owner != "-":
            row["owners"].add(owner)
        tags = set(ticket.get("tags") or [])
        row["helpful"] += "suggestion-helpful" in tags
        row["not_helpful"] += "suggestion-not-helpful" in tags
        row["suggested"] += "solution-suggested" in tags
        row["differs"] += "category-differs" in tags
        row["typed"] += bool(ticket.get("device_type"))

    if args.monthly:
        write_monthly(tickets, args)

    out = []
    for day in sorted(rows):
        row = rows[day]
        done = row["fixed"] + row["postponed"] + row["not_repaired"]
        row["repairers"] = len(row["owners"])
        row["new_repairers"] = sum(1 for o in row["owners"] if created.get(o, "") >= args.new_since.isoformat())
        row["repair_rate"] = round(row["fixed"] / done, 3) if done else ""
        out.append({"appointment": day.isoformat(), **{c: row[c] for c in COLUMNS[1:]}})

    handle = args.out.open("w", encoding="utf-8", newline="") if args.out else sys.stdout
    writer = csv.DictWriter(handle, COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(out)
    if args.out:
        handle.close()
        write_run(args.out, inputs=[tickets_file, HERE / "indicators.py", HERE.parent / "enrich" / "tickets.py"],
                  outputs=[args.out], extra={"since": args.since and args.since.isoformat(),
                                             "guest_login": args.guest_login, "new_since": args.new_since.isoformat()})


MONTHLY = ["month", "with_result", "by_guest", "repairers", "new_repairers"]


def write_monthly(tickets, args):
    """Owners per month and the first month each one closed a repair, sums only."""
    months = defaultdict(lambda: {"with_result": 0, "by_guest": 0, "owners": set()})
    first = {}
    for ticket in sorted(tickets, key=lambda t: (source.appointment(t) or date.max)):
        day = source.appointment(ticket)
        if day is None or outcome(ticket) in ("open", "no_show", "other"):
            continue
        month = day.strftime("%Y-%m")
        row = months[month]
        row["with_result"] += 1
        owner = ticket.get("owner") or "-"
        if owner == args.guest_login:
            row["by_guest"] += 1
        elif owner != "-":
            row["owners"].add(owner)
            first.setdefault(owner, month)
    rows = [{"month": m, "with_result": r["with_result"], "by_guest": r["by_guest"], "repairers": len(r["owners"]),
             "new_repairers": sum(1 for o in r["owners"] if first[o] == m)}
            for m, r in sorted(months.items()) if m >= args.warm_up]
    with args.monthly.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, MONTHLY, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    write_run(args.monthly, inputs=[args.export.expanduser() / "tickets.json", HERE / "indicators.py"],
              outputs=[args.monthly], extra={"warm_up": args.warm_up, "guest_login": args.guest_login})


if __name__ == "__main__":
    main()
