"""Reads an export of zammad/export_tickets.py for the enrichment test, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

Only tickets of a device count. Statistics tickets, tickets tagged abgelehnt or obsolete (the request
was settled) and EUReCA (repairs of members outside the Repair Café) are left out. Articles come without
the automatic ones of Zammad, because those repeat house rules and appointment texts, and can be cut at
the appointment. The prompts are built as Zammad builds those of its AI agents. The fields are those of
the old Zammad, so the values volunteers kept serve as reference.
"""

import html
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

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



def appointment(ticket):
    """Day of the first appointment, from the date tags, else a month tag as its first day, else the
    pending time. None for tickets that never had one."""
    days = sorted(t for t in ticket.get("tags") or [] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t))
    if days:
        return date.fromisoformat(days[0])
    months = sorted(t for t in ticket.get("tags") or [] if re.fullmatch(r"\d{4}-\d{2}", t))
    if months:
        return date.fromisoformat(months[0] + "-01")
    if ticket.get("pending_time"):
        return date.fromisoformat(ticket["pending_time"][:10])
    return None


def articles(ticket, until=None):
    """Articles of guests and volunteers, oldest first, without the automatic ones of Zammad.

    until="first" keeps the first article, as the categorizer sees a new ticket. until="appointment"
    keeps the articles written before the day of the appointment, what MANUEL knows a week before.
    Without any, for example a guest who came without notice, the first article stays.
    """
    found = [a for a in sorted(ticket.get("articles") or [], key=lambda a: a["created_at"])
             if a.get("sender") != "System" and plain(a)]
    if until == "first":
        return found[:1]
    if until == "appointment":
        day = appointment(ticket)
        before = [a for a in found if day is None or date.fromisoformat(a["created_at"][:10]) < day]
        return before or found[:1]
    return found


def zammad_user_prompt(ticket, chosen, attributes=None):
    """The user prompt of an AI agent as ai_agent.txt.erb in quellen/zammad builds it, with the guest
    and the team as sender names and without addresses."""
    lines = ["<ticket>"]
    for name, (label, value) in (attributes or {}).items():
        lines += [f"  <{name}>", f"    <label>{label}</label>", f"    <value>{value}</value>", f"  </{name}>"]
    lines.append("")
    for article in chosen:
        guest = article.get("sender") == "Customer"
        lines += ["  <article>", f"    <sender_type>{article.get('sender')}</sender_type>",
                  f"    <sender_name>{'Gast' if guest else 'Team'}</sender_name>",
                  f"    <visibility>{'internal' if article.get('internal') else 'public'}</visibility>"]
        if article.get("subject"):
            lines.append(f"    <subject>{article['subject']}</subject>")
        lines += [f"    <text>{plain(article)[:ARTICLE_CHARS]}</text>", "  </article>"]
    lines.append("</ticket>")
    return "\n".join(lines)[:TICKET_CHARS] + "\n"


def zammad_system_prompt(role, instruction, result_structure):
    """The system prompt of an AI agent as ai_agent.txt.erb builds it, without options."""
    return (f"{role}\n\n{instruction}\n\n\nReply with a plain JSON object only. Do not wrap the response in code "
            "fences, markdown, or any additional formatting. Do not include ```json or ``` in the output.\n\n"
            + json.dumps(result_structure, indent=2) + "\n")
