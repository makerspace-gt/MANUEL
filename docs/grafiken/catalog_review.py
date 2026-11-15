#!/usr/bin/env python3
"""Draws how the catalog was reviewed as an SVG, from the form of the anstiftung to the list MANUEL chooses from.

The numbers come from eval/categorizer/abc.tsv before and after the review of 15.11.2026, see
docs/adr/0055-katalog-in-bloecken-durchsehen.adoc. Same style as request_flow.py.

Run in the repository root:
    python3 docs/grafiken/catalog_review.py docs/grafiken/katalog-durchsicht.svg
"""

import sys

W = 1000
ROLE = {
    'mensch': ('#e4f2e4', '#008300'),
    'manuel': ('#e3eefb', '#2a78d6'),
    'regel':  ('#efefec', '#8a8984'),
    'offen':  ('#ffffff', '#8a8984'),
}
INK, INK2 = '#1b1b1a', '#4a4945'
out = []


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;')


def box(x, y, w, h, role, title, sub='', adr=''):
    fill, stroke = ROLE[role]
    dash = ' stroke-dasharray="5 4"' if role == 'offen' else ''
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>')
    cy = y + (h / 2 + 6 if not sub else 26)
    out.append(f'<text x="{x + w / 2}" y="{cy}" text-anchor="middle" font-size="17" font-weight="600" fill="{INK}">{esc(title)}</text>')
    for i, line in enumerate(sub.split('\n') if sub else []):
        out.append(f'<text x="{x + w / 2}" y="{y + 47 + i * 18}" text-anchor="middle" font-size="13.5" fill="{INK2}">{esc(line)}</text>')
    if adr:
        out.append(f'<text x="{x + w - 8}" y="{y + h - 7}" text-anchor="end" font-size="11" fill="{INK2}">{esc(adr)}</text>')


def arrow(points, dashed=False, label='', lx=None, ly=None, anchor='start', head=True):
    d = 'M ' + ' L '.join(f'{x} {y}' for x, y in points)
    da = ' stroke-dasharray="6 5"' if dashed else ''
    out.append(f'<path d="{d}" fill="none" stroke="#5f5e5a" stroke-width="2"{da}/>')
    if not head:
        return
    # Arrowheads are drawn as triangles, because the PDF renderer of asciidoctor-pdf ignores SVG markers.
    (x1, y1), (x2, y2) = points[-2], points[-1]
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    bx, by = x2 - 10 * ux, y2 - 10 * uy
    out.append(f'<path d="M {x2} {y2} L {bx - 5 * uy} {by + 5 * ux} L {bx + 5 * uy} {by - 5 * ux} Z" fill="#5f5e5a"/>')
    if label:
        out.append(f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" font-size="13" font-style="italic" fill="{INK2}">{esc(label)}</text>')


lx = 20
for role, name, step in (('mensch', 'Mensch entscheidet', 190), ('manuel', 'MANUEL wählt aus', 175),
                         ('regel', 'Daten und feste Regeln', 205), ('offen', 'später', 0)):
    fill, stroke = ROLE[role]
    dash = ' stroke-dasharray="5 4"' if role == 'offen' else ''
    out.append(f'<rect x="{lx}" y="14" width="22" height="16" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>')
    out.append(f'<text x="{lx + 30}" y="27" font-size="14" fill="{INK}">{esc(name)}</text>')
    lx += step

box(20, 60, 440, 72, 'regel', 'Laufzettel der anstiftung', '1.208 Kategorien, viele doppelt oder sehr selten')
arrow([(460, 96), (538, 96)])
box(540, 60, 440, 72, 'mensch', 'Katalog', '1.089 Einträge nach den Zusammenfassungen', 'ADR 7, 8')
arrow([(760, 132), (760, 150), (500, 150), (500, 168)])

out.append(f'<text x="500" y="186" text-anchor="middle" font-size="14" fill="{INK2}">Einteilung nach der Zahl der Reparaturen in den deutschen Open Repair Data</text>')
box(20, 198, 300, 72, 'regel', 'A, 114 Einträge', '80 Prozent der Reparaturen')
box(350, 198, 300, 72, 'regel', 'B, 251 Einträge', '15 Prozent der Reparaturen')
box(680, 198, 300, 72, 'regel', 'C, 724 Einträge', '5 Prozent der Reparaturen')

arrow([(170, 270), (170, 290), (335, 290), (335, 308)])
arrow([(500, 270), (500, 290), (335, 290)], head=False)
box(20, 310, 630, 90, 'mensch', 'Durchsicht in neun Blöcken am 15.11.2026',
    'Beschreibung und Synonyme auf Deutsch und Englisch, Gefahren, Gruppen geprüft\n36 Doppelungen zusammengefasst, Begründung in equivalents.tsv', 'ADR 55, 56')
arrow([(830, 270), (830, 308)])
box(680, 310, 300, 90, 'regel', 'C bleibt Entwurf', 'Name, ORA-Gruppe und\nIDs des Laufzettels')

arrow([(335, 400), (335, 428)])
box(20, 430, 630, 72, 'manuel', 'MANUEL wählt aus 347 Einträgen', 'nur Klassen A und B, mit Beschreibungen im Prompt', 'ADR 40, 54')
arrow([(830, 400), (830, 428)])
box(680, 430, 300, 72, 'mensch', 'Nur von Hand wählbar', 'das Feld im Ticket hat\nalle 1.053 Einträge')

arrow([(335, 502), (335, 530), (500, 530), (500, 548)])
arrow([(830, 502), (830, 530), (500, 530)], head=False)
box(180, 550, 640, 72, 'offen', 'Nach etwa einem Jahr Echtbetrieb', 'Welche C-Einträge haben Engagierte von Hand gewählt?\nHäufige kommen in die Liste, für sie folgt eine Durchsicht')
arrow([(180, 586), (120, 586), (120, 504)], dashed=True, label='neue Einträge für die Liste', lx=130, ly=545, anchor='start')

out.append(f'<text x="20" y="655" font-size="13.5" fill="{INK2}">Die Zahlen der Klassen stammen vom Stand vor der Durchsicht. Nach den Zusammenfassungen sind es 113 A-, 234 B- und 706 C-Einträge.</text>')
H = 675
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'font-family="Source Sans 3, Source Sans Pro, Noto Sans, Liberation Sans, Arial, DejaVu Sans, sans-serif" role="img" '
       f'aria-label="Vom Laufzettel über die Einteilung in A, B und C zur Liste, aus der MANUEL wählt">'
       f'<title>Durchsicht des Katalogs</title>'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + ''.join(out) + '</svg>')
open(sys.argv[1], 'w', encoding='utf-8').write(svg)
