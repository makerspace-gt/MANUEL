#!/usr/bin/env python3
"""Exports the tickets of chosen groups of an existing Zammad, reading only, for the test instance.

Zammad backs up the whole database only. This script asks the REST API for the tickets of the given groups
and nothing else, with their articles, attachments, tags and the users they name. Tickets of other groups
never reach this computer, because the search itself filters by group. Nothing in Zammad is changed.
zammad/import_tickets.rb brings the export into a fresh test instance, see
docs/adr/0069-nur-tickets-des-repair-cafe-in-die-testinstanz-uebernehmen.adoc.

The files hold personal data of guests. They stay on this computer and on MANUEL and never go into a
repository, see docs/adr/0002-echte-ticketdaten-nur-lokal-auswerten.adoc.

The address and the token come from an env file, by default ~/.config/manuel/zammad.env:
    ZAMMAD_URL=https://helpdesk.example.org
    ZAMMAD_TOKEN=...
The token needs the permission ticket.agent and its user read access to the groups. It is never printed.
Zammad cannot restrict a token to reading, so delete it after the export.

Run in the repository root:
    python3 zammad/export_tickets.py --group "Repair Café" [--env FILE] [--out DIR] [--limit N]
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

PER_PAGE = 100


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Api:
    def __init__(self, base, token):
        self.base, self.token = base.rstrip("/"), token

    def request(self, path, body=None, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Token token={self.token}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(f"{self.base}/api/v1/{path}", data=data, headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read() if raw else json.load(response)


def safe_name(name):
    return re.sub(r"[^\w.\-]+", "_", name or "file")[:120]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--group", action="append", required=True, help="name of a group, can be given several times")
    parser.add_argument("--env", type=Path, default=Path("~/.config/manuel/zammad.env").expanduser())
    parser.add_argument("--out", type=Path, default=Path(f"~/bench/zammad-tickets/{date.today()}").expanduser())
    parser.add_argument("--limit", type=int, help="at most this many tickets, for a first test")
    args = parser.parse_args()

    env = read_env(args.env)
    if not env.get("ZAMMAD_URL") or not env.get("ZAMMAD_TOKEN"):
        sys.exit(f"ZAMMAD_URL und ZAMMAD_TOKEN fehlen in {args.env}")
    api = Api(env["ZAMMAD_URL"], env["ZAMMAD_TOKEN"])

    try:
        groups = {g["name"]: g["id"] for g in api.request("groups")}
    except urllib.error.HTTPError as error:
        sys.exit(f"Gruppen nicht lesbar, HTTP {error.code}. Hat der Token ticket.agent?")
    missing = [name for name in args.group if name not in groups]
    if missing:
        sys.exit(f"Gruppe nicht gefunden: {', '.join(missing)}")
    group_ids = [str(groups[name]) for name in args.group]

    tickets, page = [], 1
    while True:
        query = urllib.parse.urlencode({"expand": "true", "page": page, "per_page": PER_PAGE})
        batch = api.request(f"tickets/search?{query}", {
            "condition": {"ticket.group_id": {"operator": "is", "value": group_ids}},
            "sort_by": "id", "order_by": "asc",
        })
        batch = [t for t in batch if str(t.get("group_id")) in group_ids]  # the search filters, this only guards
        tickets.extend(batch)
        if len(batch) < PER_PAGE or (args.limit and len(tickets) >= args.limit):
            break
        page += 1
    tickets = tickets[: args.limit] if args.limit else tickets

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "attachments").mkdir(exist_ok=True)
    user_ids, articles_total, files_total = set(), 0, 0
    for index, ticket in enumerate(tickets, 1):
        ticket["tags"] = api.request(f"tags?{urllib.parse.urlencode({'object': 'Ticket', 'o_id': ticket['id']})}").get("tags", [])
        articles = api.request(f"ticket_articles/by_ticket/{ticket['id']}?expand=true")
        for article in articles:
            for attachment in article.get("attachments", []):
                target = args.out / "attachments" / str(article["id"]) / f"{attachment['id']}_{safe_name(attachment.get('filename'))}"
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(api.request(f"ticket_attachment/{ticket['id']}/{article['id']}/{attachment['id']}", raw=True))
                attachment["file"] = str(target.relative_to(args.out))
                files_total += 1
            user_ids.update(filter(None, [article.get("created_by_id"), article.get("updated_by_id")]))
        ticket["articles"] = articles
        articles_total += len(articles)
        user_ids.update(filter(None, [ticket.get("customer_id"), ticket.get("owner_id")]))
        if index % 50 == 0:
            print(f"{index} von {len(tickets)} Tickets", flush=True)

    users = []
    for user_id in sorted(user_ids):
        try:
            users.append(api.request(f"users/{user_id}?expand=true"))
        except urllib.error.HTTPError as error:
            print(f"Nutzer {user_id} nicht lesbar, HTTP {error.code}")

    (args.out / "tickets.json").write_text(json.dumps(tickets, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out / "users.json").write_text(json.dumps(users, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.out / "export.json").write_text(json.dumps({
        "groups": args.group, "source": env["ZAMMAD_URL"], "date": str(date.today()),
        "tickets": len(tickets), "articles": articles_total, "attachments": files_total, "users": len(users),
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(tickets)} Tickets, {articles_total} Nachrichten, {files_total} Anhänge, {len(users)} Nutzer in {args.out}")


if __name__ == "__main__":
    main()
