#!/usr/bin/env python3
"""Describe the Open Repair Data with tables and charts.

Answers how many repairs are reported per month and year, which partner reports how much,
which product categories appear over the years, and how many events stand behind the entries.
Tables go to docs/ora, charts to docs/grafiken. Every chart is written twice, once with a dark
mode for the web and once light only for the PDF, because the PDF renderer ignores @media.
Chart labels are German, the audience is the team in Gütersloh, see docs/adr/0029.

Usage from the repository root:
    python3 eval/ora/charts.py quellen/openrepair-data
"""

import csv
import statistics
import sys
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

TABLES = Path("docs/ora")
CHARTS = Path("docs/grafiken")
FIRST_YEAR = 2015
LAST_MONTH = "2026-07"  # data until the end of July 2026

# Fixed slot per partner, colour follows the partner, never its rank
PARTNERS = [
    ("The Restart Project", "Restart Project", 1),
    ("Repair Café International", "Repair Café International", 2),
    ("Repair Café Denmark", "Repair Café Denmark", 3),
    ("anstiftung", "anstiftung", 4),
    ("Repair Cafe Wales", "Repair Cafe Wales", 5),
]
OTHER = ("Andere", 0)

STYLE = """
.bg { fill: #fcfcfb; } .primary { fill: #0b0b0b; } .secondary { fill: #52514e; }
.grid { stroke: #e4e3df; } .axis { stroke: #b5b4ae; } .line { stroke: #2a78d6; }
.s0 { fill: #9a9992; } .s1 { fill: #2a78d6; } .s2 { fill: #eb6834; } .s3 { fill: #1baf7a; }
.s4 { fill: #eda100; } .s5 { fill: #e87ba4; }
.h0 { fill: #f0efec; } .h1 { fill: #cde2fb; } .h2 { fill: #9ec5f4; } .h3 { fill: #5598e7; }
.h4 { fill: #256abf; } .h5 { fill: #0d366b; } .on-dark { fill: #fcfcfb; }
@media (prefers-color-scheme: dark) {
  .bg { fill: #1a1a19; } .primary { fill: #f0efec; } .secondary { fill: #c3c2b7; }
  .grid { stroke: #3a3a37; } .axis { stroke: #5c5b55; } .line { stroke: #3987e5; }
  .s0 { fill: #75746e; } .s1 { fill: #3987e5; } .s2 { fill: #d95926; } .s3 { fill: #199e70; }
  .s4 { fill: #c98500; } .s5 { fill: #d55181; }
  .h0 { fill: #262624; } .h1 { fill: #104281; } .h2 { fill: #1c5cab; } .h3 { fill: #3987e5; }
  .h4 { fill: #86b6ef; } .h5 { fill: #cde2fb; } .on-dark { fill: #0b0b0b; }
}
text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
"""


def number(value):
    return f"{value:,.0f}".replace(",", ".")


def read(folder):
    rows = []
    for name in ("eee", "non-eee"):
        for file in sorted(folder.glob(f"OpenRepairData_*_aggregate_*_{name}.csv")):
            with file.open(encoding="utf-8") as handle:
                rows += list(csv.DictReader(handle))
    return rows


def write_table(name, header, rows):
    TABLES.mkdir(parents=True, exist_ok=True)
    with (TABLES / name).open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def svg(name, width, height, title, subtitle, body):
    head = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
    ]
    content = [
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="primary" x="24" y="30" font-size="18" font-weight="600">{escape(title)}</text>',
        f'<text class="secondary" x="24" y="50" font-size="13">{escape(subtitle)}</text>',
    ] + body + ["</svg>"]
    CHARTS.mkdir(parents=True, exist_ok=True)
    (CHARTS / f"{name}.svg").write_text("\n".join(head + [f"<style>{STYLE}</style>"] + content) + "\n", encoding="utf-8")
    light = STYLE.split("@media")[0] + 'text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }\n'
    (CHARTS / f"{name}-hell.svg").write_text("\n".join(head + [f"<style>{light}</style>"] + content) + "\n", encoding="utf-8")


def nice_top(value):
    for step in (1, 2, 2.5, 5, 10):
        magnitude = 10 ** (len(str(int(value))) - 1)
        if step * magnitude >= value:
            return step * magnitude
    return value


def y_axis(left, right, top, base, maximum, ticks=4):
    out = []
    for i in range(ticks + 1):
        value = maximum * i / ticks
        y = base - (base - top) * i / ticks
        css = "axis" if i == 0 else "grid"
        out.append(f'<line class="{css}" x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="secondary" x="{left - 8}" y="{y + 4:.1f}" font-size="11" text-anchor="end">{number(value)}</text>')
    return out


def legend(x, y, items):
    out = []
    for label, slot in items:
        out.append(f'<rect class="s{slot}" x="{x}" y="{y - 10}" width="12" height="12" rx="2"/>')
        out.append(f'<text class="secondary" x="{x + 17}" y="{y}" font-size="12">{escape(label)}</text>')
        x += 30 + len(label) * 6.6
    return out


def by_year_partner(rows):
    known = {key for key, _, _ in PARTNERS}
    counts = defaultdict(Counter)
    for row in rows:
        year = row["event_date"][:4]
        if year and int(year) >= FIRST_YEAR:
            partner = row["data_provider"] if row["data_provider"] in known else OTHER[0]
            counts[year][partner] += 1
    years = sorted(counts)
    series = [(key, label, slot) for key, label, slot in PARTNERS] + [(OTHER[0], OTHER[0], OTHER[1])]
    write_table("entries_by_year_partner.tsv", ["year"] + [label for _, label, _ in series] + ["total"],
                [[y] + [counts[y][key] for key, _, _ in series] + [sum(counts[y].values())] for y in years])
    width, height = 860, 420
    left, right, top, base = 70, width - 24, 96, height - 40
    maximum = nice_top(max(sum(counts[y].values()) for y in years))
    step = (right - left) / len(years)
    body = y_axis(left, right, top, base, maximum)
    body += legend(left, 76, [(label, slot) for _, label, slot in series])
    for i, year in enumerate(years):
        x = left + i * step + 6
        y = base
        for key, label, slot in series:
            value = counts[year][key]
            h = (base - top) * value / maximum
            if h >= 1.5:  # skip slivers, the PDF renderer rejects zero height
                body.append(f'<rect class="s{slot}" x="{x:.1f}" y="{y - h:.1f}" width="{step - 12:.1f}" height="{max(h - 1, 0):.1f}">'
                            f"<title>{escape(label)} {year}: {number(value)}</title></rect>")
            y -= h
        total = sum(counts[year].values())
        body.append(f'<text class="primary" x="{x + (step - 12) / 2:.1f}" y="{y - 5:.1f}" font-size="10" text-anchor="middle">{number(total)}</text>')
        body.append(f'<text class="secondary" x="{x + (step - 12) / 2:.1f}" y="{base + 16}" font-size="11" text-anchor="middle">{year}</text>')
    svg("ora-jahre-partner", width, height, "Gemeldete Reparaturen je Jahr und Partner",
        "Einträge der Open Repair Data nach Datum der Veranstaltung, 2026 nur bis Juli", body)


def by_month(rows):
    counts = Counter(row["event_date"][:7] for row in rows if row["event_date"][:4] >= str(FIRST_YEAR))
    months = [m for m in sorted(counts) if m <= LAST_MONTH]
    write_table("entries_by_month.tsv", ["month", "entries"], [[m, counts[m]] for m in months])
    width, height = 860, 340
    left, right, top, base = 70, width - 24, 70, height - 40
    maximum = nice_top(max(counts[m] for m in months))
    step = (right - left) / (len(months) - 1)
    points = " ".join(f"{left + i * step:.1f},{base - (base - top) * counts[m] / maximum:.1f}" for i, m in enumerate(months))
    body = y_axis(left, right, top, base, maximum)
    body.append(f'<polyline class="line" fill="none" stroke-width="2" points="{points}"/>')
    for i, m in enumerate(months):
        if m.endswith("-01"):
            x = left + i * step
            body.append(f'<text class="secondary" x="{x:.1f}" y="{base + 16}" font-size="11" text-anchor="middle">{m[:4]}</text>')
    peak = max(months, key=lambda m: counts[m])
    i = months.index(peak)
    body.append(f'<text class="primary" x="{left + i * step:.1f}" y="{base - (base - top) * counts[peak] / maximum - 8:.1f}" '
                f'font-size="11" text-anchor="middle">{number(counts[peak])} im {peak[5:]}/{peak[:4]}</text>')
    svg("ora-monate", width, height, "Gemeldete Reparaturen je Monat",
        "Alle Partner zusammen, nach Datum der Veranstaltung", body)


def groups_by_year(rows, top_n=15):
    counts = defaultdict(Counter)
    for row in rows:
        year = row["event_date"][:4]
        if year and int(year) >= FIRST_YEAR:
            counts[year][row["product_category"]] += 1
    years = sorted(counts)
    total = Counter()
    for year in years:
        total.update(counts[year])
    groups = [g for g, _ in total.most_common(top_n)]
    share = {(g, y): counts[y][g] / sum(counts[y].values()) for g in groups for y in years}
    write_table("share_of_groups_by_year.tsv", ["product_category"] + years,
                [[g] + [f"{share[(g, y)] * 100:.1f}" for y in years] for g in groups])
    width = 860
    left, top, cell_h = 230, 74, 22
    cell_w = (width - left - 24) / len(years)
    height = top + cell_h * len(groups) + 40
    steps = [0.02, 0.04, 0.06, 0.08, 0.12]
    body = []
    for j, year in enumerate(years):
        body.append(f'<text class="secondary" x="{left + j * cell_w + cell_w / 2:.1f}" y="{top - 8}" font-size="11" text-anchor="middle">{year}</text>')
    for i, group in enumerate(groups):
        y = top + i * cell_h
        body.append(f'<text class="secondary" x="{left - 8}" y="{y + 15}" font-size="11" text-anchor="end">{escape(group)}</text>')
        for j, year in enumerate(years):
            value = share[(group, year)]
            level = sum(value >= s for s in steps)
            x = left + j * cell_w
            ink = "on-dark" if level >= 4 else "primary"
            body.append(f'<rect class="h{level}" x="{x + 1:.1f}" y="{y + 1}" width="{cell_w - 2:.1f}" height="{cell_h - 2}" rx="2">'
                        f"<title>{escape(group)} {year}: {value * 100:.1f} %</title></rect>")
            body.append(f'<text class="{ink}" x="{x + cell_w / 2:.1f}" y="{y + 15}" font-size="10" text-anchor="middle">{value * 100:.0f}</text>')
    body.append(f'<text class="secondary" x="{left}" y="{height - 14}" font-size="11">Anteil an allen Einträgen des Jahres in Prozent. Je dunkler, desto größer der Anteil.</text>')
    svg("ora-gruppen-jahre", width, height, f"Die {top_n} häufigsten ORA-Gruppen je Jahr",
        "Anteil jeder Gruppe an den gemeldeten Reparaturen eines Jahres", body)


def events(rows):
    per_event = defaultdict(Counter)
    groups = defaultdict(set)
    for row in rows:
        partner = row["data_provider"]
        per_event[partner][(row["group_identifier"], row["event_date"])] += 1
        groups[partner].add(row["group_identifier"])
    table = []
    for partner in sorted(per_event, key=lambda p: -sum(per_event[p].values())):
        sizes = list(per_event[partner].values())
        table.append([partner, len(groups[partner]), len(sizes), sum(sizes),
                      f"{statistics.median(sizes):.0f}", f"{statistics.mean(sizes):.1f}", max(sizes)])
    write_table("events_by_partner.tsv",
                ["partner", "groups", "events", "entries", "entries_per_event_median", "entries_per_event_mean",
                 "entries_per_event_max"], table)


def main():
    rows = read(Path(sys.argv[1]))
    by_year_partner(rows)
    by_month(rows)
    groups_by_year(rows)
    events(rows)
    print(f"{len(rows)} entries, tables in {TABLES}, charts in {CHARTS}")


if __name__ == "__main__":
    main()
