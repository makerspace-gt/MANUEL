#!/usr/bin/env python3
"""Chart of the power draw of MANUEL from the logger, for chapter 12 of the case study.

The logger writes one line per minute to /var/log/manuel/metrics-YYYY-MM.csv, see docs/inbetriebnahme.md
step 8. A copy lies in docs/messungen. The chart shows the power at the plug and the load of the GPU
as two panels with a shared time axis, as medians over 10 minutes. Readings below 1 W count as missing,
the plug reports 0 W for a moment when it restarts. The script prints the numbers for the text.
Only the standard library is used, the style comes from eval/ora/charts.py.

Run in the repository root:
    python3 eval/strom/power_chart.py docs/messungen/metrics-2026-11.csv
"""

import csv
import datetime as dt
import importlib.util
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("charts", ROOT / "eval" / "ora" / "charts.py")
charts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(charts)

BUCKET = dt.timedelta(minutes=10)


def de(value, digits):
    """Number with a decimal comma, as in German texts."""
    return f"{value:.{digits}f}".replace(".", ",")


def read(path):
    rows = []
    for row in csv.DictReader(Path(path).open(encoding="utf-8")):
        power = float(row["plug_power_w"]) if row["plug_power_w"] else None
        rows.append((dt.datetime.fromisoformat(row["time"]), power if power and power >= 1 else None,
                     float(row["gpu_busy_percent"]) if row["gpu_busy_percent"] else None,
                     float(row["plug_total_kwh"]) if row["plug_total_kwh"] else None))
    return rows


def buckets(rows, index):
    out, current, values = [], None, []
    for row in rows:
        start = row[0] - dt.timedelta(minutes=row[0].minute % 10, seconds=row[0].second)
        if current is not None and start != current:
            if values:
                out.append((current, statistics.median(values)))
            values = []
        current = start
        if row[index] is not None:
            values.append(row[index])
    if values:
        out.append((current, statistics.median(values)))
    return out


def panel(series, left, right, top, base, maximum, start, end, slot_class, label, unit):
    span = (end - start).total_seconds()
    body = charts.y_axis(left, right, top, base, maximum)
    body.append(f'<text class="secondary" x="{left}" y="{top - 10}" font-size="12">{charts.escape(label)} in {unit}</text>')
    points = " ".join(f"{left + (right - left) * (t - start).total_seconds() / span:.1f},"
                      f"{base - (base - top) * min(v, maximum) / maximum:.1f}" for t, v in series)
    body.append(f'<polyline class="{slot_class}" fill="none" stroke-width="2" stroke-linejoin="round" points="{points}"/>')
    return body


def main():
    rows = read(sys.argv[1] if len(sys.argv) > 1 else "docs/messungen/metrics-2026-11.csv")
    power, gpu = buckets(rows, 1), buckets(rows, 2)
    start, end = rows[0][0], rows[-1][0]
    days = (end - start).total_seconds() / 86400
    kwh = [r[3] for r in rows if r[3] is not None]
    energy = kwh[-1] - kwh[0]
    readings = [r[1] for r in rows if r[1] is not None]
    idle = [r[1] for r in rows if r[1] is not None and r[2] is not None and r[2] < 5]
    left, right, width = 64, 856, 880
    body = []
    body += panel(power, left, right, 96, 266, charts.nice_top(max(v for _, v in power)), start, end,
                  "line", "Leistung an der Steckdose", "Watt")
    body += panel(gpu, left, right, 326, 436, 100, start, end, "line", "Auslastung der GPU", "Prozent")
    day = start.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)
    while day <= end:
        x = left + (right - left) * (day - start).total_seconds() / (end - start).total_seconds()
        body.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="96" y2="436"/>')
        body.append(f'<text class="secondary" x="{x:.1f}" y="456" font-size="11" text-anchor="middle">{day:%d.%m.}</text>')
        day += dt.timedelta(days=1)
    subtitle = (f"{start:%d.%m.} bis {end:%d.%m.%Y}, Median über 10 Minuten. Im Leerlauf {de(statistics.median(idle), 1)} W, "
                f"höchstens {de(max(readings), 0)} W, zusammen {de(energy, 2)} kWh")
    charts.svg("strom-verlauf", width, 476, "Strom und Last von MANUEL", subtitle, body)
    print(f"{days:.1f} Tage, Leerlauf {statistics.median(idle):.1f} W, Spitze {max(readings):.1f} W, "
          f"{energy:.3f} kWh, {energy / days:.3f} kWh je Tag")


if __name__ == "__main__":
    main()
