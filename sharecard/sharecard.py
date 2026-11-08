#!/usr/bin/env python3
"""Creates a share card with the summary of one Repair Café date, see docs/adr/0033.

The card shows how many devices were registered and processed, how many guests did not
show up and, once recorded, how many came without registration. A grid with one square per
registered device shows the results, a dot plot places the date among all dates of the
last three years, and the donations, a highlight and the next date complete the card.

Stage 1 reads the team's statistics spreadsheet. Only the sheet "Eingabe" is read, all other
sheets such as the name badges are skipped while parsing. The spreadsheet stays local, the card
contains totals only. A person checks every card before it is shared.

The script needs only the standard library. rsvg-convert turns the SVG into a PNG if it is
installed.

Run in the repository root:
    python3 sharecard/sharecard.py <statistics.ods> --date 2026-11-07 [--highlight TEXT]
        [--signup TEXT] [--metric registered|processed] [--out DIRECTORY]
"""

import argparse
import base64
import datetime as dt
import math
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from html import escape
from pathlib import Path

SHEET = "Eingabe"
TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"

# Column headers of the team's sheet (external source, German) and the field each one fills.
COLUMNS = {
    "Datum": "date", "Angemeldet": "registered", "bearbeitet": "processed", "gelungen": "fixed",
    "teilweise gelungen": "partly", "vertagt": "postponed", "nicht erfolgt": "failed", "abgebrochen": "aborted",
    "keine Information": "unknown", "no-show": "no_show", "Spenden": "donations", "spontan": "spontaneous",
}
NUMBERS = [field for field in COLUMNS.values() if field != "date"]

LOGO = Path(__file__).resolve().parent.parent / "case-study" / "bilder" / "dsee-foerderlogo.png"
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]

SIZE = 1080
MARGIN = 72
FONT = "system-ui, 'Noto Sans', Cantarell, 'Liberation Sans', sans-serif"
INK = {"surface": "#fcfcfb", "primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "axis": "#c3c2b7", "dot": "#b5b4ae", "accent": "#2a78d6"}
# Results in a fixed order, colours from the validated categorical palette, glyphs as second channel.
RESULTS = [
    ("fixed", "gelungen", "#008300", "check"),
    ("partly", "teilweise gelungen", "#eda100", "dash"),
    ("postponed", "vertagt", "#2a78d6", "arrow"),
    ("failed", "nicht erfolgt", "#e34948", "cross"),
    ("unknown", "keine Information", "#9a9992", "dot"),
]


class DataError(ValueError):
    """The statistics do not add up, the card is not created."""


def cell_value(cell):
    value = cell.get(OFFICE + "date-value") or cell.get(OFFICE + "value")
    if value is None:
        value = " ".join("".join(p.itertext()) for p in cell.iter(TEXT + "p")).strip() or None
    return value


def read_events(path):
    """Reads one dict per dated row of the sheet "Eingabe", other sheets are skipped unread."""
    rows, header, depth, inside = [], None, 0, False
    with zipfile.ZipFile(path) as archive, archive.open("content.xml") as content:
        for event, elem in ET.iterparse(content, events=("start", "end")):
            if elem.tag == TABLE + "table":
                if event == "start":
                    depth += 1
                    inside = depth == 1 and elem.get(TABLE + "name") == SHEET
                else:
                    depth -= 1
                    inside = False
                    elem.clear()
                continue
            if event != "end" or elem.tag != TABLE + "table-row":
                continue
            if not inside:
                elem.clear()
                continue
            values = []
            for cell in elem:
                if cell.tag in (TABLE + "table-cell", TABLE + "covered-table-cell"):
                    repeat = min(int(cell.get(TABLE + "number-columns-repeated", "1")), 64)
                    values += [cell_value(cell)] * repeat
            elem.clear()
            if header is None:
                if "Datum" in values:
                    header = {}
                    for index, name in enumerate(values):
                        if name in COLUMNS and COLUMNS[name] not in header:
                            header[COLUMNS[name]] = index
                continue
            rows.append(values)
    if header is None:
        raise DataError(f"Blatt {SHEET} mit der Spalte Datum nicht gefunden")
    events = []
    for values in rows:
        raw = values[header["date"]] if header["date"] < len(values) else None
        try:
            date = dt.date.fromisoformat((raw or "")[:10])
        except ValueError:
            continue
        event = {"date": date, "note": None}
        for field in NUMBERS:
            index = header.get(field)
            value = values[index] if index is not None and index < len(values) else None
            try:
                event[field] = float(value) if value not in (None, "") else None
            except ValueError:
                event[field] = None
                event["note"] = value
        events.append(event)
    return sorted(events, key=lambda e: e["date"])


def number(event, field):
    return int(round(event.get(field) or 0))


def check(event):
    """Stops with a message if the numbers of a date do not add up."""
    registered, processed, no_show = (number(event, f) for f in ("registered", "processed", "no_show"))
    results = sum(number(event, field) for field, *_ in RESULTS) + number(event, "aborted")
    problems = []
    if registered != processed + no_show:
        problems.append(f"angemeldet {registered} ist nicht bearbeitet {processed} plus nicht erschienen {no_show}")
    if results != processed:
        problems.append(f"die Ergebnisse ergeben {results}, bearbeitet sind {processed}")
    if event.get("spontaneous") is not None and number(event, "spontaneous") > processed:
        problems.append(f"spontan {number(event, 'spontaneous')} ist mehr als bearbeitet {processed}")
    if problems:
        raise DataError(f"{event['date']}: " + ", ".join(problems))


def summarize(events, date, metric="registered"):
    """Collects everything the card shows for one date."""
    event = next((e for e in events if e["date"] == date), None)
    if event is None:
        raise DataError(f"Kein Termin am {date} in der Tabelle")
    check(event)
    start = date.replace(year=date.year - 3) if not (date.month == 2 and date.day == 29) else date.replace(
        year=date.year - 3, day=28)
    window = [e for e in events if start <= e["date"] < date and number(e, "processed") > 0]
    values = [number(e, metric) for e in window]
    today = number(event, metric)
    at_most = sum(v <= today for v in values)
    following = [e for e in events if e["date"] > date and e["note"] is None]
    processed = number(event, "processed")
    return {
        "date": date,
        "registered": number(event, "registered"),
        "processed": processed,
        "no_show": number(event, "no_show"),
        "spontaneous": None if event.get("spontaneous") is None else number(event, "spontaneous"),
        "results": {field: number(event, field) + (number(event, "aborted") if field == "failed" else 0)
                    for field, *_ in RESULTS},
        "donations": event.get("donations") or 0.0,
        "per_device": (event.get("donations") or 0.0) / processed if processed else None,
        "metric": metric,
        "today": today,
        "values": values,
        "window_start": start,
        "at_most": at_most,
        "rank": round(100 * at_most / len(values)) if values else None,
        "next": following[0]["date"] if following else None,
    }


def long_date(date):
    return f"{WEEKDAYS[date.weekday()]}, {date.day}. {MONTHS[date.month - 1]} {date.year}"


def euro(value):
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{text} €"


def counts_line(s):
    line = f"{s['registered']} angemeldet, {s['processed']} bearbeitet, {s['no_show']} nicht erschienen"
    if s["spontaneous"] is not None:
        line += f", davon {s['spontaneous']} spontan"
    return line


def rank_text(s):
    noun = "angemeldete" if s["metric"] == "registered" else "bearbeitete"
    return (f"der {len(s['values'])} Termine der letzten drei Jahre hatten höchstens {s['today']} {noun} "
            f"Geräte")


def alt_text(s, highlight=None):
    parts = [f"Sharecard des Repair Café Gütersloh vom {long_date(s['date'])}.", counts_line(s) + "."]
    results = ", ".join(f"{s['results'][field]} {label}" for field, label, *_ in RESULTS if s["results"][field])
    parts.append(f"Ergebnisse {results}.")
    if s["rank"] is not None:
        parts.append(f"{s['rank']} Prozent {rank_text(s)}.")
    parts.append(f"Spenden {euro(s['donations'])}" + (f", {euro(s['per_device'])} je Gerät." if s["per_device"]
                                                     else "."))
    if highlight:
        parts.append(highlight.rstrip(".") + ".")
    if s["next"]:
        parts.append(f"Nächster Termin {long_date(s['next'])}.")
    parts.append("Gefördert durch die Deutsche Stiftung für Engagement und Ehrenamt.")
    return " ".join(parts)


def text(x, y, content, size, ink="primary", weight=400, anchor="start", style=None):
    extra = f' font-style="{style}"' if style else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{INK[ink]}" '
            f'text-anchor="{anchor}"{extra}>{escape(content)}</text>')


def glyph(kind, x, y, size, colour):
    """A small symbol inside a square, so colour never carries the result alone."""
    c, s = (x + size / 2, y + size / 2), size * 0.22
    stroke = f'stroke="{colour}" stroke-width="{size * 0.09:.1f}" stroke-linecap="round" fill="none"'
    if kind == "check":
        return (f'<path {stroke} stroke-linejoin="round" d="M{c[0] - s:.1f},{c[1]:.1f} L{c[0] - s * 0.25:.1f},'
                f'{c[1] + s * 0.8:.1f} L{c[0] + s * 1.1:.1f},{c[1] - s * 0.9:.1f}"/>')
    if kind == "dash":
        return f'<path {stroke} d="M{c[0] - s:.1f},{c[1]:.1f} H{c[0] + s:.1f}"/>'
    if kind == "arrow":
        return (f'<path {stroke} stroke-linejoin="round" d="M{c[0] - s:.1f},{c[1]:.1f} H{c[0] + s:.1f} '
                f'M{c[0] + s * 0.3:.1f},{c[1] - s * 0.7:.1f} L{c[0] + s:.1f},{c[1]:.1f} '
                f'L{c[0] + s * 0.3:.1f},{c[1] + s * 0.7:.1f}"/>')
    if kind == "cross":
        return (f'<path {stroke} d="M{c[0] - s * 0.8:.1f},{c[1] - s * 0.8:.1f} L{c[0] + s * 0.8:.1f},'
                f'{c[1] + s * 0.8:.1f} M{c[0] + s * 0.8:.1f},{c[1] - s * 0.8:.1f} L{c[0] - s * 0.8:.1f},'
                f'{c[1] + s * 0.8:.1f}"/>')
    return f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{s * 0.45:.1f}" fill="{colour}"/>'


def square(x, y, size, fill=None, kind=None):
    if fill is None:
        return (f'<rect x="{x + 1.5:.1f}" y="{y + 1.5:.1f}" width="{size - 3:.1f}" height="{size - 3:.1f}" rx="6" '
                f'fill="none" stroke="{INK["axis"]}" stroke-width="3"/>')
    mark = "#0b0b0b" if fill == "#eda100" else "#ffffff"
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" rx="6" fill="{fill}"/>'
            + glyph(kind, x, y, size, mark))


def png_size(path):
    with open(path, "rb") as handle:
        head = handle.read(24)
    return struct.unpack(">II", head[16:24])


def estimate(content, size, weight=400):
    """Rough width of a text line, enough to wrap and to keep clear of the logo."""
    return len(content) * size * (0.6 if weight >= 600 else 0.53)


def wrap(content, size, width, weight=400):
    lines, line = [], ""
    for word in content.split():
        candidate = f"{line} {word}".strip()
        if line and estimate(candidate, size, weight) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + [line] if line else lines


def render(s, highlight=None, signup="Anmeldung per Mail, Telefon oder Formular"):
    """Lays the card out in fixed bands from top to bottom, footer last so it never moves."""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" '
           f'font-family="{FONT}">',
           f"<title>{escape(alt_text(s, highlight))}</title>",
           f'<rect width="{SIZE}" height="{SIZE}" fill="{INK["surface"]}"/>']
    width = SIZE - 2 * MARGIN
    y = MARGIN + 30
    out.append(text(MARGIN, y, "Repair Café Gütersloh", 34, "secondary", 600))
    y += 62
    out.append(text(MARGIN, y, long_date(s["date"]), 52, "primary", 700))
    for line in wrap(counts_line(s), 28, width):
        y += 44
        out.append(text(MARGIN, y, line, 28, "secondary"))

    # Grid, one square per registered device, results first in fixed order, no-shows last and empty.
    y += 30
    cells = [(colour, kind) for field, _, colour, kind in RESULTS for _ in range(s["results"][field])]
    cells += [(None, None)] * s["no_show"]
    gap = 8
    columns = 13 if len(cells) <= 26 else max(13, math.ceil(len(cells) / 3))
    size = min(64, (width - (columns - 1) * gap) / columns)
    rows = max(1, math.ceil(len(cells) / columns))
    for index, (fill, kind) in enumerate(cells):
        cx = MARGIN + (index % columns) * (size + gap)
        cy = y + (index // columns) * (size + gap)
        out.append(square(cx, cy, size, fill, kind))
    y += rows * (size + gap) + 30

    # Legend with counts, it carries the names so colour is never the only channel.
    legend = [(colour, kind, f"{s['results'][field]} {label}") for field, label, colour, kind in RESULTS
              if s["results"][field]]
    if s["no_show"]:
        legend.append((None, None, f"{s['no_show']} nicht erschienen"))
    x, line_y = MARGIN, y
    for colour, kind, label in legend:
        item_w = 44 + estimate(label, 28)
        if x > MARGIN and x + item_w > SIZE - MARGIN:
            x, line_y = MARGIN, line_y + 46
        out.append(square(x, line_y - 26, 34, colour, kind))
        out.append(text(x + 44, line_y, label, 28, "primary"))
        x += item_w + 28
    y = line_y

    if highlight:
        for line in wrap(f"„{highlight}“", 28, width):
            y += 44
            out.append(text(MARGIN, y, line, 28, "primary", style="italic"))

    # Footer first, so the dot plot knows how much room is left above it.
    footer_top = SIZE - MARGIN - 128
    if s["next"]:
        out.append(text(MARGIN, footer_top, f"Nächster Termin {long_date(s['next'])}, 11 bis 14 Uhr", 28,
                        "primary", 600))
        out.append(text(MARGIN, footer_top + 40, signup, 26, "secondary"))
    donations = f"{euro(s['donations'])} Spenden" + (f", {euro(s['per_device'])} je Gerät" if s["per_device"] else "")
    out.append(text(MARGIN, SIZE - MARGIN - 4, donations, 30, "primary", 600))
    if LOGO.exists():
        logo_w, logo_h = png_size(LOGO)
        height = 110
        width_logo = height * logo_w / logo_h
        data = base64.b64encode(LOGO.read_bytes()).decode()
        out.append(f'<image x="{SIZE - MARGIN - width_logo:.1f}" y="{SIZE - MARGIN - height + 6:.1f}" '
                   f'width="{width_logo:.1f}" height="{height}" href="data:image/png;base64,{data}"/>')

    # Dot plot of the last three years, the date itself as the one accented dot.
    if s["rank"] is not None:
        y += 82
        out.append(text(MARGIN, y, f"{s['rank']} %", 60, "primary", 700))
        lines = wrap(rank_text(s), 28, width - 210)
        for index, line in enumerate(lines[:2]):
            out.append(text(MARGIN + 210, y - 30 + index * 36, line, 28, "secondary"))
        values = s["values"] + [s["today"]]
        low, high = min(values), max(values)
        step = width / (high - low + 1)
        radius = min(10, step / 2 - 1)
        counts = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        tallest = max(counts.values())
        base = min(footer_top - 76, y + 56 + 2 * radius + (tallest - 1) * (2 * radius + 3))
        room = base - (y + 40) - 2 * radius
        spacing = min(2 * radius + 3, room / max(tallest - 1, 1))
        stacks = {}
        for value in sorted(s["values"]):
            level = stacks.get(value, 0)
            stacks[value] = level + 1
            cx = MARGIN + (value - low + 0.5) * step
            out.append(f'<circle cx="{cx:.1f}" cy="{base - radius - level * spacing:.1f}" r="{radius:.1f}" '
                       f'fill="{INK["dot"]}" stroke="{INK["surface"]}" stroke-width="2"/>')
        level = stacks.get(s["today"], 0)
        cx = MARGIN + (s["today"] - low + 0.5) * step
        cy = base - radius - level * spacing
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius + 3:.1f}" fill="{INK["accent"]}" '
                   f'stroke="{INK["surface"]}" stroke-width="2"/>')
        out.append(f'<line x1="{MARGIN}" x2="{SIZE - MARGIN}" y1="{base + 4:.1f}" y2="{base + 4:.1f}" '
                   f'stroke="{INK["axis"]}" stroke-width="1"/>')
        for tick in range(math.ceil(low / 5) * 5, high + 1, 5):
            tx = MARGIN + (tick - low + 0.5) * step
            out.append(text(tx, base + 32, str(tick), 22, "muted", anchor="middle"))
        out.append(text(cx, cy - radius - 12, str(s["today"]), 26, "primary", 700, anchor="middle"))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("statistics", type=Path)
    parser.add_argument("--date", required=True, type=dt.date.fromisoformat)
    parser.add_argument("--highlight")
    parser.add_argument("--signup", default="Anmeldung per Mail, Telefon oder Formular")
    parser.add_argument("--metric", choices=["registered", "processed"], default="registered")
    parser.add_argument("--out", type=Path, default=Path("sharecard/cards"))
    args = parser.parse_args()
    try:
        summary = summarize(read_events(args.statistics), args.date, args.metric)
    except DataError as error:
        sys.exit(f"Keine Karte erzeugt, {error}")
    args.out.mkdir(parents=True, exist_ok=True)
    stem = args.out / args.date.isoformat()
    svg = render(summary, args.highlight, args.signup)
    stem.with_suffix(".svg").write_text(svg, encoding="utf-8")
    stem.with_suffix(".txt").write_text(alt_text(summary, args.highlight) + "\n", encoding="utf-8")
    written = [stem.with_suffix(".svg"), stem.with_suffix(".txt")]
    if shutil.which("rsvg-convert"):
        subprocess.run(["rsvg-convert", "-w", str(SIZE), "-h", str(SIZE), "-o", str(stem.with_suffix(".png")),
                        str(stem.with_suffix(".svg"))], check=True)
        written.append(stem.with_suffix(".png"))
    print("geschrieben", *written)


if __name__ == "__main__":
    main()
