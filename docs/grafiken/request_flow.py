#!/usr/bin/env python3
"""Draws the flow of a request in the Repair Café as an SVG, from the first contact to the report.

Each station is coloured by who does it: the guest, a human, MANUEL or a fixed rule in Zammad or n8n.

Run in the repository root:
    python3 docs/grafiken/request_flow.py docs/grafiken/weg-einer-anfrage.svg
"""

import sys
W, H = 1000, 1140
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
ins = [('gast', 'E-Mail', ''), ('gast', 'Kontaktformular', 'Kontaktdaten übernommen'),
       ('gast', 'Anrufbeantworter', 'Gast über die Nummer\nTranskript mit Whisper'),
       ('gast', 'Empfang', 'spontan, Vorlage Walk-in'), ('mensch', 'Spam-Ordner', 'Mensch prüft\nin Spam check')]
xs = [20, 214, 408, 602, 796]
for x, (role, t, s) in zip(xs, ins):
    box(x, 56, 184, 74, role, t, s)
CX = 500
for x in xs:
    arrow([(x+92, 130), (x+92, 146), (CX, 146), (CX, 160)]) if x+92 != CX else arrow([(CX, 130), (CX, 160)])
# Ticket
box(250, 162, 500, 72, 'regel', 'Ticket in Zammad', 'ein Ticket je Gerät, Eingangsbestätigung mit Hausordnung\ncontact-check bei abweichenden Kontaktdaten', 'ADR 34, 60, 63')
arrow([(CX, 234), (CX, 262)])
# Einordnen
box(250, 264, 500, 72, 'manuel', 'Einordnen und Felder vorschlagen', 'Kategorie, Marke, Bezeichnung, Defekt\nauch vom Foto des Typenschilds', 'ADR 34, 40')
box(20, 264, 190, 114, 'mensch', 'Aufteilen', 'mehrere Geräte genannt\nHinweis an den Gast\nweitere an späteren Tagen', 'ADR 34, 41')
arrow([(250, 300), (212, 300)])
arrow([(115, 264), (115, 198), (248, 198)], dashed=True, label='je Gerät ein Ticket', lx=124, ly=222, anchor='start')
box(790, 264, 190, 90, 'mensch', 'Nachfrage beim Gast', 'wenn Angaben fehlen\nText von MANUEL', 'ADR 17, 34')
arrow([(750, 290), (788, 290)])
arrow([(885, 264), (885, 198), (752, 198)], dashed=True, label='Antwort des Gastes', lx=876, ly=222, anchor='end')
arrow([(CX, 336), (CX, 364)])
# Terminvorschlag
box(250, 366, 500, 72, 'regel', 'Termin vorschlagen', 'Status Vorschlag, Nachfrage nach 2 Tagen, Absage nach 4\nkurz vor dem Termin nur Nachfrage', 'ADR 26, 60')
arrow([(CX, 438), (CX, 466)], label='bestätigt', lx=CX+8, ly=457)
box(250, 468, 500, 72, 'regel', 'Terminiert', 'Ticket wandert von Requests nach Repairs\nErinnerung, wenn die Vereinbarung lange her ist', 'ADR 60')
arrow([(CX, 540), (CX, 568)])
# Lösungsansatz eine Woche vorher
box(250, 570, 500, 72, 'manuel', 'Lösungsansatz bei next-event', 'eine Woche vorher, interne Notiz mit Schritten, Werkzeug\nund Sicherheit, passende Artikel und Anleitungen', 'ADR 22, 35, 61')
arrow([(CX, 642), (CX, 670)])
# spontan ohne Termin
arrow([(750, 322), (770, 322), (770, 708), (752, 708)], dashed=True, label='spontan', lx=778, ly=560, anchor='start')
# Reparatur
box(250, 672, 500, 72, 'mensch', 'Reparatur am Termin', 'Checkliste mit Hausordnung, Kontaktdaten, Newsletter,\nOwner, Vorschläge von MANUEL geprüft und Ergebnis', 'ADR 17, 32, 60')
arrow([(CX, 744), (CX, 772)])
box(250, 774, 500, 72, 'mensch', 'Ergebnis eintragen', 'gelungen, teilweise gelungen, vertagt,\nnicht erfolgt, abgebrochen, nicht erschienen')
arrow([(750, 810), (860, 810), (860, 402), (752, 402)], dashed=True, label='vertagt', lx=868, ly=610, anchor='start')
arrow([(CX, 846), (CX, 874)])
box(250, 876, 500, 72, 'regel', 'Nachts nach dem Termin', 'Datums-Tag statt next-event\nunbestätigte Vorschläge werden No-show', 'ADR 62')
# Rund um den Termin
out.append(f'<text x="20" y="460" font-size="13" font-style="italic" fill="{INK2}">eine Woche vorher</text>')
box(20, 468, 190, 72, 'gast', 'Erinnerung', 'Mail der anstiftung\nzum nächsten Termin')
arrow([(115, 540), (115, 568)])
box(20, 570, 190, 86, 'regel', 'Presse und Medien', 'Pressemitteilung, Notiz\nfür soziale Medien', 'ADR 66')
arrow([(115, 656), (115, 684)])
box(20, 686, 190, 86, 'regel', 'Statistik-Ticket', 'in Repairs::Events\nSpenden und Bedarf', 'ADR 60')
# Nach dem Termin
arrow([(115, 772), (115, 976)])
arrow([(CX, 962), (200, 962), (200, 976)])
arrow([(CX, 948), (CX, 976)])
arrow([(CX, 962), (835, 962), (835, 976)])
box(20, 978, 290, 90, 'regel', 'Statistik und Sharecard', 'n8n zählt die Ergebnisse, ein Mensch\ngibt Karte und Beiträge frei', 'ADR 32, 33, 66')
box(355, 978, 290, 90, 'regel', 'Meldung an Restarters', 'jedes Gerät per API,\nweiter an die Open Repair Alliance', 'ADR 14, 36')
box(690, 978, 290, 90, 'manuel', 'Anleitung', 'Entwurf aus erfolgreicher Reparatur\nfür die Wissensdatenbank', 'ADR 22')
out.append(f'<text x="20" y="1100" font-size="13.5" fill="{INK2}">Gestrichelt sind Schleifen und Abkürzungen. Ein Mensch prüft jeden Vorschlag von MANUEL, MANUEL schreibt nie selbst an Gäste.</text>')
out.append(f'<text x="20" y="1122" font-size="13.5" fill="{INK2}">Mails an Gäste sind feste Texte in Zammad. n8n, Sharecard, Anleitungen und Suche folgen nach dem Zeitplan im PLAN.</text>')
H = 1140
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
       f'font-family="Source Sans 3, Source Sans Pro, Noto Sans, Liberation Sans, Arial, DejaVu Sans, sans-serif" role="img" '
       f'aria-label="Ablauf einer Anfrage im Repair Café vom Eingang bis zur Meldung">'
       f'<title>Weg einer Anfrage im Repair Café</title>'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + ''.join(out) + '</svg>')
open(sys.argv[1], 'w', encoding='utf-8').write(svg)
