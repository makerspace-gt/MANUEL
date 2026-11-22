#!/usr/bin/env python3
"""Monthly sums from the team's statistics spreadsheet since 2019, for the baseline of the trial, see
docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc.

Reads only the sheet "Eingabe" with the reader of sharecard/sharecard.py and keeps appointments that took
place, so planned and cancelled dates drop out. Partly fixed counts as fixed, as in the Open Repair Data
(eval/ora/result_mapping.tsv), aborted counts as not repaired. The output holds sums per month only.

Run in the repository root:
    python3 -I eval/indicators/statistics.py Repair-Café-Statistik.ods OUT.tsv
"""

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "sharecard"))
sys.path.insert(0, str(ROOT / "eval"))

import sharecard  # noqa: E402
from lauf import write_run  # noqa: E402

COLUMNS = ["month", "events", "processed", "fixed", "partly", "postponed", "not_repaired", "unknown", "no_show"]


def main():
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    months = defaultdict(lambda: dict.fromkeys(COLUMNS[1:], 0))
    for event in sharecard.read_events(source):
        processed = sharecard.number(event, "processed")
        if processed == 0 or event["date"] > date.today():
            continue
        row = months[event["date"].strftime("%Y-%m")]
        row["events"] += 1
        row["processed"] += processed
        row["fixed"] += sharecard.number(event, "fixed") + sharecard.number(event, "partly")
        row["partly"] += sharecard.number(event, "partly")
        row["postponed"] += sharecard.number(event, "postponed")
        row["not_repaired"] += sharecard.number(event, "failed") + sharecard.number(event, "aborted")
        row["unknown"] += sharecard.number(event, "unknown")
        row["no_show"] += sharecard.number(event, "no_show")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows({"month": month, **months[month]} for month in sorted(months))
    write_run(target, inputs=[source, HERE / "statistics.py", ROOT / "sharecard" / "sharecard.py"], outputs=[target])
    print(f"{len(months)} Monate in {target}")


if __name__ == "__main__":
    main()
