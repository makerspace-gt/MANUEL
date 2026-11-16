"""Reads an export of zammad/export_tickets.py for the enrichment test, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

Only tickets of a device count. Statistics tickets, tickets tagged abgelehnt or obsolete (the request
was settled) and EUReCA (repairs of members outside the Repair Café) are left out. The text of a ticket
holds every article of guests and volunteers in order, without the automatic ones of Zammad, because
those repeat house rules and appointment texts. The fields are those of the old Zammad, so the values
volunteers kept serve as reference.
"""

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

# Old field, new field in zammad/objects.rb, how values are compared in score.py
FIELDS = {
    "marke": ("brand", "name"),
    "bezeichnung": ("device_model", "name"),
    "baujahr": ("year_of_manufacture", "exact"),
    "stromversorgung": ("power_supply", "exact"),
    "notiz": ("problem_reported", "text"),
    "hack": ("solution", "text"),
    "ergebnis": ("repair_result", "result"),
}
POWER = ["230 V", "mit Netzteil", "Akku", "Batterie", "ohne Kabel (Mechanik)"]
SKIP_TAGS = {"abgelehnt", "obsolete", "EUReCA"}
ARTICLE_CHARS = 3000
TICKET_CHARS = 16000


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.skip += 1
        if tag in ("br", "p", "div", "li", "tr", "blockquote"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain(article):
    body = article.get("body") or ""
    if article.get("content_type") == "text/html":
        parser = _Text()
        parser.feed(re.sub(r"data:[^\"')\s]+", "", body))
        body = "".join(parser.parts)
    body = html.unescape(body)
    body = re.sub(r"[ \t\xa0]+", " ", body)
    return re.sub(r"\n\s*\n+", "\n\n", body).strip()


def load(export_dir):
    path = Path(export_dir).expanduser() / "tickets.json"
    tickets = json.loads(path.read_text(encoding="utf-8"))
    return path, [t for t in tickets if is_device(t)]


def is_device(ticket):
    if ticket["title"].strip().lower().startswith("statistik"):
        return False
    return not SKIP_TAGS.intersection(ticket.get("tags") or [])


def human(ticket, field):
    """The value volunteers kept, empty as None."""
    value = ticket.get(field)
    if value in (None, "", False):
        return None
    return value


def text(ticket):
    """All articles of guests and volunteers, oldest first, each and the whole cut to a fixed length."""
    parts = [f"Betreff: {ticket['title']}"]
    for article in sorted(ticket.get("articles") or [], key=lambda a: a["created_at"]):
        if article.get("sender") == "System":
            continue
        body = plain(article)[:ARTICLE_CHARS]
        if body:
            who = "Gast" if article.get("sender") == "Customer" else "Team"
            kind = {"note": "Notiz", "phone": "Anruf", "email": "E-Mail", "web": "Formular"}.get(article.get("type"), article.get("type"))
            parts.append(f"--- {who}, {kind}, {article['created_at'][:10]}\n{body}")
    return "\n\n".join(parts)[:TICKET_CHARS]


def results(tickets):
    """Values of the old result field, as Zammad stores them with :: between the levels."""
    return sorted({t["ergebnis"] for t in tickets if t.get("ergebnis")})
