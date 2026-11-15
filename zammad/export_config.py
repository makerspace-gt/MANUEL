#!/usr/bin/env python3
"""Exports the configuration of an existing Zammad as JSON files, reading only.

Fetches fields, triggers, overviews, macros, core workflows, scheduled jobs, text modules, templates,
groups, roles, SLAs, calendars, signatures, postmaster filters, webhooks, tags, AI agents and text tools
through the REST API. Nothing in Zammad is changed. The files stay on this computer, because triggers,
text modules and signatures can hold names, email addresses and phone numbers, see
docs/adr/0048-keine-personenbezogenen-daten-nach-aussen-geben.adoc.

The address and the token come from an env file, by default ~/.config/manuel/zammad.env:
    ZAMMAD_URL=https://helpdesk.example.org
    ZAMMAD_TOKEN=...
The token is never printed. It needs the admin permissions of the parts to export, for example
admin.trigger, admin.overview and admin.object. Zammad cannot restrict a token to reading, so delete it
after the export.

Run in the repository root:
    python3 zammad/export_config.py [--env FILE] [--out DIR]
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ENDPOINTS = {
    "object_manager_attributes": "object_manager_attributes",
    "triggers": "triggers",
    "overviews": "overviews",
    "macros": "macros",
    "core_workflows": "core_workflows",
    "jobs": "jobs",
    "text_modules": "text_modules",
    "templates": "templates",
    "groups": "groups",
    "roles": "roles",
    "slas": "slas",
    "calendars": "calendars",
    "signatures": "signatures",
    "postmaster_filters": "postmaster_filters",
    "webhooks": "webhooks",
    "tags": "tag_list",
    "ticket_states": "ticket_states",
    "ticket_priorities": "ticket_priorities",
    "ai_agents": "ai_agents",
    "ai_text_tools": "ai_text_tools",
    # full=true brings the items of each template
    "checklist_templates": "checklist_templates?full=true",
    "translations_customized": "translations/customized",
}
PER_PAGE = 500


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get(url, token):
    request = urllib.request.Request(url, headers={"Authorization": f"Token token={token}", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def fetch(base, path, token):
    """All records of an endpoint, page by page where the endpoint pages."""
    if "/" in path or path == "tag_list" or "?" in path:
        return get(f"{base}/api/v1/{path}", token)
    records, page = [], 1
    while True:
        data = get(f"{base}/api/v1/{path}?expand=true&per_page={PER_PAGE}&page={page}", token)
        if not isinstance(data, list):
            return data
        records.extend(data)
        if len(data) < PER_PAGE:
            return records
        page += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", type=Path, default=Path("~/.config/manuel/zammad.env").expanduser())
    parser.add_argument("--out", type=Path, default=Path(f"~/bench/zammad-export/{date.today()}").expanduser())
    args = parser.parse_args()

    env = read_env(args.env)
    base, token = env.get("ZAMMAD_URL", "").rstrip("/"), env.get("ZAMMAD_TOKEN", "")
    if not base or not token:
        sys.exit(f"ZAMMAD_URL und ZAMMAD_TOKEN fehlen in {args.env}")
    args.out.mkdir(parents=True, exist_ok=True)

    for name, path in ENDPOINTS.items():
        try:
            data = fetch(base, path, token)
        except urllib.error.HTTPError as error:
            print(f"{name}: HTTP {error.code}, übersprungen")
            continue
        except urllib.error.URLError as error:
            sys.exit(f"{base} nicht erreichbar: {error.reason}")
        (args.out / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        count = len(data) if isinstance(data, list) else "1 Objekt"
        print(f"{name}: {count}")
    print(f"Gespeichert in {args.out}")


if __name__ == "__main__":
    main()
