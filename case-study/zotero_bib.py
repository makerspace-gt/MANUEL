#!/usr/bin/env python3
"""Keeps literatur.bib in sync with the Zotero group makerspace-gt-MANUEL.

The group leads, see docs/adr/0046-literatur-in-einer-zotero-gruppe-pflegen.adoc.

    python3 zotero_bib.py export          # group -> literatur.bib (default)
    python3 zotero_bib.py export --check  # exit 1 if literatur.bib differs from the group
    python3 zotero_bib.py seed            # literatur.bib -> empty group, run once
    python3 zotero_bib.py merge           # fold items saved with the Zotero Connector into the group

merge looks at every item without a pinned key. If an item with the same URL exists, its
attachments such as the snapshot move there, empty fields are filled, the tag "Snapshot fehlt"
is removed and the duplicate is deleted. A duplicate without attachments waits for the next run,
because the Connector may still be uploading. Otherwise the item gets a key of its own.

Reading works without a key because the group is public. Writing needs ZOTERO_API_KEY,
taken from the environment or from ~/.config/manuel/zotero.env. Every item needs a
citation key in the Zotero field "Citation Key". Biblatex fields without a Zotero field
go into Extra as lines like "tex.note: ...". The key is pinned in Extra as "Citation Key: ..."
because Better BibTeX in a synced Zotero overwrites the field otherwise. Only the standard
library is used.
"""

import argparse
import json
import os
import re
import secrets
import sys
import unicodedata
import urllib.request
from pathlib import Path

GROUP = 6759593
API = f"https://api.zotero.org/groups/{GROUP}"
BIB = Path(__file__).with_name("literatur.bib")
HEADER = """% Literatur der Fallstudie. Diese Datei wird erzeugt, bitte nicht von Hand bearbeiten.
% Quelle ist die Zotero-Gruppe makerspace-gt-MANUEL, https://www.zotero.org/groups/{group}
% Neu erzeugen mit: python3 case-study/zotero_bib.py export
% Siehe docs/adr/0046-literatur-in-einer-zotero-gruppe-pflegen.adoc
"""

# Zotero item type -> biblatex entry type
ENTRY = {
    "webpage": "online", "blogPost": "online", "preprint": "online", "document": "misc",
    "report": "report", "book": "book", "journalArticle": "article",
    "conferencePaper": "inproceedings", "thesis": "thesis", "computerProgram": "software",
}
# biblatex field -> Zotero field, per Zotero item type
FIELDS = {
    "report": {"institution": "institution", "address": "place", "type": "reportType"},
    "book": {"publisher": "publisher", "address": "place"},
    "thesis": {"institution": "university", "type": "thesisType"},
    "journalArticle": {"journal": "publicationTitle", "volume": "volume", "number": "issue",
                       "pages": "pages", "doi": "DOI"},
    "conferencePaper": {"booktitle": "proceedingsTitle", "series": "series", "volume": "volume",
                        "pages": "pages", "doi": "DOI"},
    "computerProgram": {"version": "versionNumber"},
}
ORDER = ["author", "title", "subtitle", "type", "version", "booktitle", "journal", "series",
         "volume", "number", "pages", "publisher", "institution", "address", "howpublished",
         "date", "year", "doi", "eprint", "eprinttype", "url", "urldate", "note"]


def api_key():
    key = os.environ.get("ZOTERO_API_KEY")
    env = Path.home() / ".config/manuel/zotero.env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ZOTERO_API_KEY="):
                key = line.split("=", 1)[1].strip()
    return key


def request(path, data=None, key=None, method=None, extra_headers=None):
    headers = {"Zotero-API-Version": "3", **(extra_headers or {})}
    if key:
        headers["Zotero-API-Key"] = key
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
        headers["Zotero-Write-Token"] = secrets.token_hex(16)
    req = urllib.request.Request(API + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
        return (json.loads(raw) if raw else {}), response.headers


def fetch_all(path, key=None):
    """All raw item data from a listing such as /items/top, page by page."""
    items, start = [], 0
    sep = "&" if "?" in path else "?"
    while True:
        page, headers = request(f"{path}{sep}format=json&limit=100&start={start}", key=key)
        items += [i["data"] for i in page]
        start += 100
        if start >= int(headers.get("Total-Results", 0)):
            return items


def pinned_key(item):
    for line in item.get("extra", "").splitlines():
        if line.startswith("Citation Key:"):
            return line.split(":", 1)[1].strip()
    return item.get("citationKey", "")


def fetch_items(key=None):
    items, start = [], 0
    while True:
        page, headers = request(f"/items/top?format=json&limit=100&start={start}", key=key)
        for i in page:
            if i["data"]["itemType"] not in ("attachment", "note"):
                i["data"]["citationKey"] = pinned_key(i["data"])
                items.append(i["data"])
        start += 100
        if start >= int(headers.get("Total-Results", 0)):
            return items


# --- Zotero -> biblatex -------------------------------------------------------------

def tex(value):
    return re.sub(r"(?<!\\)([&%#])", r"\\\1", value)


def creator(c):
    if c.get("name"):
        return "{" + tex(c["name"]) + "}"
    return f"{tex(c['lastName'])}, {tex(c['firstName'])}".rstrip(", ")


def to_entry(item):
    kind = item["itemType"]
    fields = {}
    authors = [c for c in item.get("creators", []) if c["creatorType"] in ("author", "programmer")]
    if authors:
        fields["author"] = " and ".join(creator(c) for c in authors)
    title, _, subtitle = item["title"].partition(": ")
    fields["title"] = tex(title)
    if subtitle:
        fields["subtitle"] = tex(subtitle)
    for bib_field, zotero_field in FIELDS.get(kind, {}).items():
        if item.get(zotero_field):
            value = item[zotero_field]
            fields[bib_field] = value.replace("-", "--") if bib_field == "pages" else tex(value)
    if kind == "preprint" and item.get("archiveID"):
        fields["eprint"] = item["archiveID"].split(":", 1)[-1]
        fields["eprinttype"] = item.get("repository") or "arXiv"
    date = item.get("date", "")
    if re.fullmatch(r"\d{4}", date):
        fields["year"] = date
    elif date:
        fields["date"] = date
    if item.get("url"):
        fields["url"] = item["url"]
    if item.get("accessDate"):
        fields["urldate"] = item["accessDate"][:10]
    for line in item.get("extra", "").splitlines():
        match = re.match(r"tex\.(\w+):\s*(.*)", line)
        if match:
            fields[match.group(1)] = tex(match.group(2))
    width = max(len(f) for f in fields)
    lines = [f"  {f.ljust(width)} = {{{fields[f]}}}," for f in sorted(fields, key=lambda f: (
        ORDER.index(f) if f in ORDER else len(ORDER), f))]
    return f"@{ENTRY.get(kind, 'misc')}{{{item['citationKey']},\n" + "\n".join(lines) + "\n}\n"


def render(items):
    missing = [i["title"] for i in items if not i.get("citationKey")]
    if missing:
        sys.exit("Ohne Citation Key: " + "; ".join(missing))
    keys = [i["citationKey"] for i in items]
    doubles = {k for k in keys if keys.count(k) > 1}
    if doubles:
        sys.exit("Doppelte Citation Keys: " + ", ".join(sorted(doubles)))
    body = "\n".join(to_entry(i) for i in sorted(items, key=lambda i: i["citationKey"]))
    return HEADER.format(group=GROUP) + "\n" + body


# --- biblatex -> Zotero, only for the first upload -----------------------------------

def parse_bib(text):
    for match in re.finditer(r"@(\w+)\{([^,\s]+),(.*?)\n\}", text, re.S):
        fields = {}
        for name, value in re.findall(r"^\s*(\w+)\s*=\s*\{(.*?)\},?\s*$", match.group(3), re.M):
            fields[name.lower()] = value
        yield match.group(1).lower(), match.group(2), fields


def untex(value):
    return value.replace("\\&", "&").replace("\\%", "%").replace("{", "").replace("}", "")


def to_item(kind, key, f):
    if kind == "online":
        zotero_type = "preprint" if "eprint" in f else "webpage"
    else:
        zotero_type = {v: k for k, v in ENTRY.items() if k not in ("blogPost", "preprint")}[kind]
    item = {"itemType": zotero_type, "citationKey": key, "creators": []}
    for name in re.split(r"\s+and\s+", f.pop("author", "")) if f.get("author") else []:
        if name.startswith("{"):
            item["creators"].append({"creatorType": "author", "name": untex(name)})
        else:
            last, _, first = name.partition(", ")
            item["creators"].append({"creatorType": "author", "lastName": untex(last),
                                     "firstName": untex(first)})
    item["title"] = untex(f.pop("title")) + (": " + untex(f.pop("subtitle")) if "subtitle" in f else "")
    for bib_field, zotero_field in FIELDS.get(zotero_type, {}).items():
        if bib_field in f:
            item[zotero_field] = untex(f.pop(bib_field)).replace("--", "-")
    if zotero_type == "preprint":
        item["repository"] = f.pop("eprinttype", "arXiv")
        item["archiveID"] = f"{item['repository']}:{f.pop('eprint')}"
    item["date"] = f.pop("date", f.pop("year", ""))
    item["url"] = f.pop("url", "")
    if "urldate" in f:
        item["accessDate"] = f.pop("urldate") + "T00:00:00Z"
    item["extra"] = "\n".join([f"Citation Key: {key}"] + [f"tex.{k}: {untex(v)}" for k, v in f.items()])
    return item


def post(items, key):
    for start in range(0, len(items), 50):
        result, _ = request("/items", items[start:start + 50], key=key)
        if result.get("failed"):
            sys.exit(json.dumps(result["failed"], ensure_ascii=False, indent=1))
        print(f"{len(result['successful'])} Einträge angelegt")


# --- Items from the Zotero Connector --------------------------------------------------

FILL = ("abstractNote", "websiteTitle", "blogTitle", "publicationTitle", "date", "language",
        "shortTitle", "websiteType", "publisher")
TAG = "Snapshot fehlt"


def norm_url(url):
    url = re.sub(r"^https?://(www\.)?", "", url.split("#")[0]).rstrip("/")
    return url.lower()


def slug(text, words=3):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    skip = {"the", "a", "an", "and", "of", "for", "der", "die", "das", "und", "im", "in", "mit"}
    return "-".join([w for w in re.split(r"[^a-z0-9]+", text) if w and w not in skip][:words])


def new_key(item, used):
    host = re.sub(r"^https?://(www\.)?", "", item.get("url", "")).split("/")[0].split(".")
    site = host[-2] if len(host) > 1 else (host[0] or "quelle")
    base = re.sub(r"-+", "-", f"{site}-{slug(item.get('title', ''))}").strip("-")
    key, n = base, 2
    while key in used:
        key, n = f"{base}-{n}", n + 1
    used.add(key)
    return key


def pin(item, citation_key):
    extra = [l for l in item.get("extra", "").splitlines() if not l.startswith("Citation Key:")]
    item["extra"] = "\n".join([f"Citation Key: {citation_key}"] + extra)
    item["citationKey"] = citation_key


def merge(key):
    items = [d for d in fetch_all("/items/top", key) if d["itemType"] not in ("attachment", "note")]
    pinned = [d for d in items if "Citation Key:" in d.get("extra", "")]
    by_url = {norm_url(d["url"]): d for d in pinned if d.get("url")}
    used = {pinned_key(d) for d in pinned}
    moved, changed, deleted, keyed, waiting = [], {}, [], [], []
    for d in items:
        if d in pinned:
            continue
        old = by_url.get(norm_url(d.get("url", ""))) if d.get("url") else None
        if old is None:
            pin(d, new_key(d, used))
            keyed.append(d)
            continue
        children = fetch_all(f"/items/{d['key']}/children", key)
        if not children:
            # The Connector may still be uploading the snapshot, try again later
            waiting.append(d)
            continue
        for child in children:
            child["parentItem"] = old["key"]
            moved.append(child)
        for field in FILL:
            if d.get(field) and field in old and not old[field]:
                old[field] = d[field]
        if not old.get("creators") and d.get("creators"):
            old["creators"] = d["creators"]
        tags = {t["tag"] for t in old.get("tags", [])}
        old["tags"] += [t for t in d.get("tags", []) if t["tag"] not in tags and t["tag"] != TAG]
        if any(c["itemType"] == "attachment" for c in children):
            old["tags"] = [t for t in old["tags"] if t["tag"] != TAG]
        changed[old["key"]] = old
        deleted.append(d)
    for batch in (moved, list(changed.values()), keyed):
        for start in range(0, len(batch), 50):
            result, _ = request("/items", batch[start:start + 50], key=key)
            if result.get("failed"):
                sys.exit(json.dumps(result["failed"], ensure_ascii=False, indent=1))
    for d in deleted:
        request(f"/items/{d['key']}", key=key, method="DELETE",
                extra_headers={"If-Unmodified-Since-Version": str(d["version"])})
    for d in deleted:
        print(f"zusammengeführt: {d.get('title', '')[:60]} -> {pinned_key(by_url[norm_url(d['url'])])}")
    for d in keyed:
        print(f"neu: {d['citationKey']} {d.get('title', '')[:60]}")
    for d in waiting:
        print(f"wartet, noch ohne Anhang: {d.get('title', '')[:60]}")
    if not deleted and not keyed and not waiting:
        print("nichts zusammenzuführen")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", nargs="?", default="export", choices=["export", "seed", "merge"])
    parser.add_argument("--check", action="store_true", help="nur vergleichen, nichts schreiben")
    args = parser.parse_args()

    if args.command == "merge":
        key = api_key()
        if not key:
            sys.exit("ZOTERO_API_KEY fehlt")
        merge(key)
        return

    if args.command == "seed":
        key = api_key()
        if not key:
            sys.exit("ZOTERO_API_KEY fehlt")
        if fetch_items(key):
            sys.exit("Die Gruppe ist nicht leer, seed läuft nur einmal")
        post([to_item(*entry) for entry in parse_bib(BIB.read_text(encoding="utf-8"))], key)
        return

    text = render(fetch_items(api_key()))
    if args.check:
        same = BIB.exists() and BIB.read_text(encoding="utf-8") == text
        print("literatur.bib entspricht der Gruppe" if same else "literatur.bib weicht von der Gruppe ab")
        sys.exit(0 if same else 1)
    BIB.write_text(text, encoding="utf-8")
    print(f"{text.count(chr(10) + '@') + text.startswith('@')} Einträge nach {BIB.name} geschrieben")


if __name__ == "__main__":
    main()
