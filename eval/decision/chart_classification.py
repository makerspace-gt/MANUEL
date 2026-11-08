#!/usr/bin/env python3
"""Creates the chart of hit rates of all methods for docs/einordnung.md.

The numbers come from evaluating the runs against the team's target values. The runs
themselves contain real tickets and are not in the repo, so only the totals are here.
Each bar shows the hit rate, the error bar the 95 percent Wilson interval.
The script needs only the standard library.

Run in the repository root:
    python3 eval/decision/chart_classification.py
"""

import math
from html import escape
from pathlib import Path

OUTPUT = Path("docs/grafiken/einordnung-verfahren.svg")
# Without dark mode for the PDF of the case study, the PDF renderer ignores @media.
OUTPUT_HELL = Path("docs/grafiken/einordnung-verfahren-hell.svg")

BANDS = ["gesamt", "unter 50", "50 bis 70", "70 bis 90", "ab 90"]

# Name, (correct, tickets) overall, then per confidence band below 50, 50 to 70, 70 to 90, from 90 percent.
# For the chain the bands lack the tickets in which no item was classified.
ROWS = [
    ("Am Betreff", [
        ("Formularnamen", (639, 745), [(49, 84), (79, 107), (211, 239), (300, 315)]),
        ("Vertreter-Namen", (636, 745), [(26, 57), (57, 89), (173, 201), (380, 398)]),
        ("Formularnamen mit Beschreibung", (630, 745), [(59, 96), (101, 138), (170, 194), (300, 317)]),
    ]),
    ("Am Betreff", [
        ("Vertreter-Namen, nur A und B", (615, 745), [(25, 72), (43, 78), (168, 200), (379, 395)]),
        ("Katalog ohne Abgrenzung", (610, 745), [(17, 46), (59, 103), (125, 167), (409, 429)]),
        ("Katalog mit Synonymen", (607, 745), [(20, 53), (52, 89), (124, 170), (411, 433)]),
    ]),
    ("Am Betreff", [
        ("Katalog mit Beschreibung", (592, 745), [(28, 72), (57, 104), (168, 207), (339, 362)]),
        ("Lange Optionen", (590, 745), [(16, 53), (41, 85), (130, 177), (403, 430)]),
        ("Kaskade A, B, C", (556, 745), [(0, 6), (7, 24), (142, 230), (407, 485)]),
    ]),
    ("An der Nachricht", [
        ("Kette vom 07.11.", (529, 745), [(27, 81), (50, 86), (191, 247), (261, 310)]),
        ("Kette, voller Text und Titel", (533, 745), [(28, 60), (59, 100), (187, 242), (259, 296)]),
        ("Kette mit Rückfall", (546, 745), [(31, 70), (60, 106), (190, 245), (265, 304)]),
    ]),
]

STYLE = """
.bg { fill: #fcfcfb; } .primary { fill: #0b0b0b; } .secondary { fill: #52514e; }
.grid { stroke: #e4e3df; } .axis { stroke: #b5b4ae; } .err { stroke: #0b0b0b; }
.s0 { fill: #9a9992; } .b1 { fill: #86b6ef; } .b2 { fill: #3987e5; } .b3 { fill: #1c5cab; }
.b4 { fill: #0d366b; }
@media (prefers-color-scheme: dark) {
  .bg { fill: #1a1a19; } .primary { fill: #f0efec; } .secondary { fill: #c3c2b7; }
  .grid { stroke: #3a3a37; } .axis { stroke: #5c5b55; } .err { stroke: #f0efec; }
  .s0 { fill: #75746e; } .b1 { fill: #184f95; } .b2 { fill: #2a78d6; } .b3 { fill: #6da7ec; }
  .b4 { fill: #b7d3f6; }
}
text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
"""


def wilson(hits, total, z=1.96):
    """95 percent Wilson interval of a rate, usable even for small numbers."""
    if not total:
        return 0.0, 0.0
    p = hits / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centre - half), min(1.0, centre + half)


def bar(x, y, width, base):
    """Bar with a 4 px rounded end on the data side, square at the baseline."""
    radius = min(4, width / 2, max(base - y, 0))
    return (
        f"M{x:.1f},{base:.1f} V{y + radius:.1f} Q{x:.1f},{y:.1f} {x + radius:.1f},{y:.1f} "
        f"H{x + width - radius:.1f} Q{x + width:.1f},{y:.1f} {x + width:.1f},{y + radius:.1f} "
        f"V{base:.1f} Z"
    )


def percent(value):
    return f"{value * 100:.0f}"


def panel(out, x0, y0, width, height, name, total, bands, first):
    """One method with five bars, overall and per confidence band."""
    plot_top, plot_bottom = y0 + 58, y0 + height - 40
    plot_h = plot_bottom - plot_top
    hits, count = total
    out.append(f'<text class="primary" x="{x0}" y="{y0 + 16}" font-size="14" font-weight="600">'
               f"{escape(name)}</text>")
    out.append(f'<text class="secondary" x="{x0}" y="{y0 + 34}" font-size="12">'
               f"{hits} von {count} richtig, {percent(hits / count)} %</text>")
    for value in (0, 50, 100):
        y = plot_bottom - value / 100 * plot_h
        css = "axis" if value == 0 else "grid"
        out.append(f'<line class="{css}" x1="{x0}" x2="{x0 + width}" y1="{y:.1f}" y2="{y:.1f}"/>')
        if first:
            out.append(f'<text class="secondary" x="{x0 - 6}" y="{y + 4:.1f}" font-size="11" '
                       f'text-anchor="end">{value} %</text>')
    slot_w = width / len(BANDS)
    bar_w = slot_w - 10
    for index, ((good, n), css) in enumerate(zip([total] + bands, ["s0", "b1", "b2", "b3", "b4"])):
        x = x0 + index * slot_w + 5
        centre = x + bar_w / 2
        rate = good / n if n else 0.0
        y = plot_bottom - rate * plot_h
        low, high = wilson(good, n)
        title = f"{BANDS[index]}: {good} von {n} richtig, {percent(rate)} %"
        out.append(f"<g><title>{escape(title)}</title>")
        if n:
            out.append(f'<path class="{css}" d="{bar(x, y, bar_w, plot_bottom)}"/>')
            y_low = plot_bottom - low * plot_h
            y_high = plot_bottom - high * plot_h
            out.append(
                f'<path class="err" fill="none" stroke-width="1.5" '
                f'd="M{centre:.1f},{y_low:.1f} V{y_high:.1f} M{centre - 4:.1f},{y_low:.1f} '
                f'H{centre + 4:.1f} M{centre - 4:.1f},{y_high:.1f} H{centre + 4:.1f}"/>'
            )
            out.append(f'<text class="primary" x="{centre:.1f}" y="{y_high - 5:.1f}" font-size="11" '
                       f'text-anchor="middle">{percent(rate)}</text>')
        out.append("</g>")
        out.append(f'<text class="secondary" x="{centre:.1f}" y="{plot_bottom + 16:.1f}" font-size="11" '
                   f'text-anchor="middle">n={n}</text>')


def main():
    columns, panel_w, panel_h = 3, 260, 230
    left, gap_x, top, gap_y = 56, 40, 150, 24
    width = left + columns * panel_w + (columns - 1) * gap_x + 24
    height = top + len(ROWS) * (panel_h + gap_y) + 30
    title = "Trefferquote der Verfahren nach Sicherheit des Modells"
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
        f"<style>{STYLE}</style>",
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="primary" x="{left}" y="30" font-size="20" font-weight="600">{escape(title)}</text>',
        f'<text class="secondary" x="{left}" y="52" font-size="13">'
        "Anteil richtiger Kategorien in Prozent, 745 Tickets mit Sollwert, Fehlerbalken 95-Prozent-Intervall "
        "nach Wilson</text>",
        f'<text class="secondary" x="{left}" y="70" font-size="13">'
        "Unter jedem Balken die Zahl der Tickets in dieser Stufe</text>",
    ]
    legend_x = left
    for label, css in zip(["gesamt", "Sicherheit unter 50 %", "50 bis 70 %", "70 bis 90 %", "ab 90 %"],
                          ["s0", "b1", "b2", "b3", "b4"]):
        out.append(f'<rect class="{css}" x="{legend_x}" y="88" width="12" height="12" rx="2"/>')
        out.append(f'<text class="secondary" x="{legend_x + 18}" y="99" font-size="13">{escape(label)}</text>')
        legend_x += 32 + len(label) * 7.0
    previous = None
    y = top
    for group, panels in ROWS:
        if group != previous:
            out.append(f'<text class="secondary" x="{left}" y="{y - 6}" font-size="12" '
                       f'font-weight="600" letter-spacing="0.5">{escape(group.upper())}</text>')
            previous = group
        for column, (name, total, bands) in enumerate(panels):
            x = left + column * (panel_w + gap_x)
            panel(out, x, y + 6, panel_w, panel_h, name, total, bands, column == 0)
        y += panel_h + gap_y
    out.append("</svg>")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    light = "\n".join(out).replace(STYLE, STYLE.split("@media")[0] + "text { font-family: system-ui, -apple-system, \"Segoe UI\", sans-serif; }\n")
    OUTPUT_HELL.write_text(light + "\n", encoding="utf-8")
    print(OUTPUT, OUTPUT_HELL)


if __name__ == "__main__":
    main()
