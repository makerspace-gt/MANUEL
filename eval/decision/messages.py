#!/usr/bin/env python3
"""Fetches the title and the guest's first message per ticket from Zammad.

The script only reads. It uses the ticket numbers from the exports tickets-Repair*.xlsx, checks before
fetching that the ticket belongs to the groups Repair Café or Repair Café Anfragen, and saves
title, subject, text and channel in a JSON file. The title is needed because for tickets that
volunteers create themselves, for example after a call, the subject of the message is empty.

The text stays complete, only HTML becomes plain text. It is not pseudonymised and contains
names, addresses and phone numbers. The file therefore does not belong in the repo and stays local or on
the mini PC. It skips tickets already fetched with a title, so an aborted run resumes.

The token comes from the environment and not from the command line:
    read -rs ZAMMAD_TOKEN && export ZAMMAD_TOKEN
    python3 MANUEL/eval/decision/messages.py --url https://zammad.example.org

The token only needs read access to tickets, in Zammad ticket.agent.
"""

import argparse
import glob
import html.parser
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
GROUPS = ("Repair Café", "Repair Café Anfragen")


class Text(html.parser.HTMLParser):
    """Turns the HTML of a message into plain text."""

    BREAK = {"br", "p", "div", "li", "tr"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.skip += 1
        if tag in self.BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script") and self.skip:
            self.skip -= 1
        if tag in self.BREAK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain(body, content_type):
    if "html" not in (content_type or ""):
        return body or ""
    parser = Text()
    parser.feed(body or "")
    return "".join(parser.parts)


def text_of(body, content_type):
    """Converts the message into plain text without leaving anything out."""
    text = plain(body, content_type).replace("\xa0", " ").replace("\r", "")
    lines = [line.rstrip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def sheet_rows(path):
    """Reads the first sheet of an export as a list of rows, without openpyxl."""
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            for item in ElementTree.fromstring(archive.read("xl/sharedStrings.xml")).findall(NS + "si"):
                shared.append("".join(t.text or "" for t in item.iter(NS + "t")))
        sheet = sorted(n for n in archive.namelist() if n.startswith("xl/worksheets/sheet"))[0]
        rows = []
        for row in ElementTree.fromstring(archive.read(sheet)).iter(NS + "row"):
            cells = {}
            for cell in row.findall(NS + "c"):
                value = cell.find(NS + "v")
                if value is None:
                    text = "".join(t.text or "" for t in cell.iter(NS + "t"))
                elif cell.get("t") == "s":
                    text = shared[int(value.text)]
                else:
                    text = value.text
                column = re.match(r"[A-Z]+", cell.get("r")).group()
                index = 0
                for letter in column:
                    index = index * 26 + ord(letter) - 64
                cells[index - 1] = text
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    head = next(i for i, row in enumerate(rows) if row and row[0] == "#")
    return rows[head], rows[head + 1:]


def numbers(pattern):
    """Reads the ticket numbers from the exports, without the statistics tickets."""
    found = []
    for path in sorted(glob.glob(pattern)):
        _, rows = sheet_rows(path)
        for row in rows:
            if len(row) > 1 and row[0] and row[1] and row[1].strip().lower() != "statistik":
                found.append(row[0].split(".")[0])
    return list(dict.fromkeys(found))


class Zammad:
    def __init__(self, url, token, debug=False):
        self.url = url.rstrip("/")
        self.token = token
        self.debug = debug

    def get(self, path):
        request = urllib.request.Request(
            self.url + path, headers={"Authorization": f"Token token={self.token}"}
        )
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        return None

    def ticket_id(self, number):
        """Searches the number field first, then freely. Depending on the version the answer is a list or an object."""
        for term in (f"number:{number}", number):
            query = urllib.parse.quote(term)
            found = self.get(f"/api/v1/tickets/search?query={query}&limit=5&expand=true")
            items = found if isinstance(found, list) else found.get("tickets", [])
            if self.debug:
                keys = sorted(found) if isinstance(found, dict) else "Liste"
                print(f"Suche {term}: {type(found).__name__} {keys} Treffer {len(items)}")
            for item in items:
                if not isinstance(item, dict):
                    return item
                if str(item.get("number")) == number:
                    return item["id"]
        return None

    def ticket(self, ticket):
        return self.get(f"/api/v1/tickets/{ticket}?expand=true")

    def articles(self, ticket):
        return self.get(f"/api/v1/ticket_articles/by_ticket/{ticket}")


def first_message(articles):
    """The guest's first public message, otherwise the first note, for example after a call."""
    visible = [a for a in articles if not a.get("internal")]
    for article in visible:
        if article.get("sender") == "Customer":
            return article, "gast"
    return (visible[0], "engagierte") if visible else (None, "keine")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Adresse von Zammad")
    parser.add_argument("--export", default="tickets-Repair*.xlsx", help="Muster der Exporte")
    parser.add_argument("--ausgabe", default="tickets-nachrichten.json")
    parser.add_argument("--limit", type=int, default=0, help="Höchstens so viele Tickets, zum Testen")
    parser.add_argument("--debug", action="store_true", help="Zeigt Art und Zahl der Suchtreffer")
    args = parser.parse_args()

    token = os.environ.get("ZAMMAD_TOKEN")
    if not token:
        sys.exit("ZAMMAD_TOKEN fehlt in der Umgebung")
    zammad = Zammad(args.url, token, args.debug)

    target = Path(args.ausgabe)
    result = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    # Errors and older entries without a title are fetched again, tickets of other groups are not
    todo = [
        n for n in numbers(args.export)
        if n not in result or ("titel" not in result[n] and result[n].get("fehler") != "andere Gruppe")
    ]
    if args.limit:
        todo = todo[: args.limit]
    print(len(todo), "Tickets offen,", len(result), "schon vorhanden")

    for index, number in enumerate(todo, 1):
        try:
            ticket = zammad.ticket_id(number)
            if ticket is None:
                result[number] = {"fehler": "nicht gefunden"}
                continue
            details = zammad.ticket(ticket)
            if details.get("group") not in GROUPS:
                result[number] = {"fehler": "andere Gruppe"}
                continue
            article, source = first_message(zammad.articles(ticket))
            result[number] = {
                "quelle": source,
                "kanal": article.get("type") if article else None,
                "titel": details.get("title") or "",
                "betreff": (article.get("subject") or "") if article else "",
                "text": text_of(article.get("body"), article.get("content_type")) if article else "",
            }
        except (urllib.error.URLError, TimeoutError, ValueError) as problem:
            result[number] = {"fehler": str(problem)[:200]}
        if index % 25 == 0:
            target.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
            print(index, "von", len(todo))
        time.sleep(0.1)

    target.write_text(json.dumps(result, ensure_ascii=False, indent=0), encoding="utf-8")
    sources = {}
    for entry in result.values():
        key = entry.get("quelle", "fehler")
        sources[key] = sources.get(key, 0) + 1
    print("Fertig:", sources)


if __name__ == "__main__":
    main()
