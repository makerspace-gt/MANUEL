#!/usr/bin/env python3
"""Draws the flow of a request in the Repair Café as an SVG, from the first contact to the report.

Each station is coloured by who does it: the guest, a human, MANUEL or a fixed rule in Zammad or n8n.

Run in the repository root:
    python3 docs/grafiken/request_flow.py docs/grafiken/weg-einer-anfrage.svg
"""

import sys
W, H = 1000, 1010
ROLE = {
    'gast':   ('#ffffff', '#5f5e5a'),
    'mensch': ('#e4f2e4', '#008300'),
    'manuel': ('#e3eefb', '#2a78d6'),
    'regel':  ('#efefec', '#8a8984'),
}
INK, INK2 = '#1b1b1a', '#4a4945'
out = []
def esc(t): return t.replace('&', '&amp;').replace('<', '&lt;')
def box(x, y, w, h, role, title, sub='', adr=''):
    fill, stroke = ROLE[role]
    dash = ' stroke-dasharray="5 4"' if role == 'gast' else ''
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>')
    cy = y + (h/2 + 6 if not sub else 26)
    out.append(f'<text x="{x+w/2}" y="{cy}" text-anchor="middle" font-size="17" font-weight="600" fill="{INK}">{esc(title)}</text>')
    for i, line in enumerate(sub.split('\n') if sub else []):
        out.append(f'<text x="{x+w/2}" y="{y+47+i*18}" text-anchor="middle" font-size="13.5" fill="{INK2}">{esc(line)}</text>')
    if adr:
        out.append(f'<text x="{x+w-8}" y="{y+h-7}" text-anchor="end" font-size="11" fill="{INK2}">{esc(adr)}</text>')
def arrow(points, dashed=False, label='', lx=None, ly=None, anchor='start'):
    d = 'M ' + ' L '.join(f'{x} {y}' for x, y in points)
    da = ' stroke-dasharray="6 5"' if dashed else ''
    out.append(f'<path d="{d}" fill="none" stroke="#5f5e5a" stroke-width="2"{da}/>')
    # Arrowheads are drawn as triangles, because the PDF renderer of asciidoctor-pdf ignores SVG markers.
    (x1, y1), (x2, y2) = points[-2], points[-1]
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    bx, by = x2 - 10 * ux, y2 - 10 * uy
    out.append(f'<path d="M {x2} {y2} L {bx - 5 * uy} {by + 5 * ux} L {bx + 5 * uy} {by - 5 * ux} Z" fill="#5f5e5a"/>')
    if label:
        out.append(f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" font-size="13" font-style="italic" fill="{INK2}">{esc(label)}</text>')

# Legende
lx = 20
for role, name in (('gast', 'Gast'), ('mensch', 'Mensch entscheidet'), ('manuel', 'MANUEL schlägt vor'), ('regel', 'feste Regel in Zammad oder n8n')):
    fill, stroke = ROLE[role]
    dash = ' stroke-dasharray="5 4"' if role == 'gast' else ''
    out.append(f'<rect x="{lx}" y="14" width="22" height="16" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>')
    out.append(f'<text x="{lx+30}" y="27" font-size="14" fill="{INK}">{esc(name)}</text>')
    lx += {'gast': 90, 'mensch': 190, 'manuel': 190}.get(role, 0)

# Eingänge
ins = [('E-Mail', ''), ('Kontaktformular', ''), ('Anrufbeantworter', ''), ('Spontan am Empfang', '')]
xs = [20, 265, 510, 755]
for x, (t, s) in zip(xs, ins):
    box(x, 60, 225, 50, 'gast', t)
CX = 500
for x in xs:
    arrow([(x+112, 110), (x+112, 130), (CX, 130), (CX, 150)]) if x+112 != CX else None
# Ticket
box(250, 152, 500, 72, 'regel', 'Ticket in Zammad', 'ein Ticket je Gerät, Tag mit dem Datum des Termins\nspontan legt der Empfang das Ticket an', 'ADR 34')
arrow([(CX, 224), (CX, 252)])
# Einordnen
box(250, 254, 500, 72, 'manuel', 'Einordnen und Felder vorschlagen', 'Kategorie, Marke, Bezeichnung, Defekt\nauch vom Foto des Typenschilds', 'ADR 34, 40')
# Split
box(20, 254, 190, 90, 'mensch', 'Aufteilen', 'mehrere Geräte genannt\nMANUEL erkennt sie', 'ADR 6, 34')
arrow([(250, 290), (212, 290)])
arrow([(115, 254), (115, 188), (248, 188)], dashed=True, label='je Gerät ein Ticket', lx=124, ly=210, anchor='start')
# Rückfrage
box(790, 254, 190, 90, 'mensch', 'Rückfrage', 'wenn Angaben fehlen\nText von MANUEL', 'ADR 11')
arrow([(750, 290), (788, 290)])
arrow([(885, 254), (885, 188), (752, 188)], dashed=True, label='Antwort des Gastes', lx=876, ly=210, anchor='end')
arrow([(CX, 326), (CX, 354)])
# Lösungsansatz
box(250, 356, 500, 72, 'manuel', 'Lösungsansatz', 'interne Notiz mit Schritten, Werkzeug und Sicherheit\npassende Artikel und Links zu Anleitungen', 'ADR 22, 35')
arrow([(CX, 428), (CX, 456)])
# Termin
box(250, 458, 500, 72, 'regel', 'Termin vorschlagen', 'Kapazität aus den Anmeldungen der Helfenden\nein Mensch bestätigt den Vorschlag', 'ADR 26')
arrow([(CX, 530), (CX, 558)])
# spontan ohne Termin
arrow([(250, 392), (200, 392), (200, 594), (248, 594)], dashed=True, label='spontan', lx=192, ly=500, anchor='end')
# Reparatur
box(250, 560, 500, 72, 'mensch', 'Reparatur am Termin', 'Gast und Engagierte reparieren gemeinsam\nFelder im Ticket prüfen und korrigieren', 'ADR 17')
arrow([(CX, 632), (CX, 660)])
# Ergebnis
box(250, 662, 500, 72, 'mensch', 'Ergebnis eintragen', 'gelungen, teilweise gelungen, vertagt,\nnicht erfolgt, abgebrochen, nicht erschienen')
arrow([(750, 698), (800, 698), (800, 494), (752, 494)], dashed=True, label='vertagt', lx=808, ly=600, anchor='start')
# Nach dem Termin
arrow([(CX, 734), (CX, 760), (150, 760), (150, 786)])
arrow([(CX, 734), (CX, 786)])
arrow([(CX, 760), (850, 760), (850, 786)])
box(20, 788, 290, 90, 'regel', 'Statistik und Sharecard', 'n8n zählt die Ergebnisse\nein Mensch gibt die Karte frei', 'ADR 32, 33')
box(355, 788, 290, 90, 'regel', 'Meldung an Restarters', 'jedes Gerät per API,\nweiter an die Open Repair Alliance', 'ADR 14, 36')
box(690, 788, 290, 90, 'manuel', 'Anleitung', 'Entwurf aus erfolgreicher Reparatur\nfür die Wissensdatenbank', 'ADR 22')
out.append(f'<text x="20" y="915" font-size="13.5" fill="{INK2}">Gestrichelt sind Schleifen und Abkürzungen. Ein Mensch prüft jeden Vorschlag von MANUEL, MANUEL schreibt nie selbst an Gäste.</text>')
out.append(f'<text x="20" y="937" font-size="13.5" fill="{INK2}">Zum Start am 05.12.2026 ordnet der Ticket Categorizer von Zammad ein. n8n, Sharecard, Anleitungen und Suche folgen nach dem Zeitplan im PLAN.</text>')
H = 955
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'font-family="Source Sans 3, Source Sans Pro, Noto Sans, Liberation Sans, Arial, DejaVu Sans, sans-serif" role="img" '
       f'aria-label="Ablauf einer Anfrage im Repair Café vom Eingang bis zur Meldung">'
       f'<title>Weg einer Anfrage im Repair Café</title>'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + ''.join(out) + '</svg>')
open(sys.argv[1], 'w', encoding='utf-8').write(svg)
