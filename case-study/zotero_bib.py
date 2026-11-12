#!/usr/bin/env python3
"""Keeps literatur.bib in sync with the Zotero group makerspace-gt-MANUEL.

The group leads, see docs/adr/0046-literatur-in-einer-zotero-gruppe-pflegen.adoc.

    python3 zotero_bib.py export          # group -> literatur.bib (default)
    python3 zotero_bib.py export --check  # exit 1 if literatur.bib differs from the group
    python3 zotero_bib.py seed            # literatur.bib -> empty group, run once
    python3 zotero_bib.py merge           # fold items saved with the Zotero Connector into the group

merge looks at every item without a pinned key. If an item with the same URL exists, its
attachments such as the snapshot move there, empty fields are filled and the duplicate is deleted. A duplicate without attachments waits ten minutes,
because the Connector may still be uploading, and is folded without attachments afterwards. Otherwise the item gets a key of its own.
Afterwards every item is sorted into a collection. Snapshots are kept only for sources the repo
uses, cited in the Fallstudie or linked in ADRs, PLAN and docs. Other sources keep their link to
the Internet Archive, and their HTML snapshots are deleted to save storage. PDFs and other
attachments stay. "Mit Anhang" holds items with an attachment, "Inbox" holds used sources still
without one, which a member saves with the Connector. Repositories and the collection
"IT-Infrastruktur" stay out of both.

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
import subprocess
import sys
import time
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
    # The Connector stores timestamps like 2024-01-08T20:39:55+00:00, biblatex wants the date only
    match = re.match(r"\d{4}(-\d{2}(-\d{2})?)?", date)
    date = match.group(0) if match else (re.findall(r"\b(\d{4})\b", date) or [""])[-1]
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
TAG = "Snapshot fehlt"  # replaced by the collections below, removed on every merge
INBOX, ATTACHED, IT = "Inbox", "Mit Anhang", "IT-Infrastruktur"
REPO = Path(__file__).resolve().parent.parent
KEEP_SNAPSHOT = {"wolf-ki-impuls"}  # the snapshot is the document itself


def repo_usage():
    """Cited keys and the text of all files in the repo that may link a source."""
    files = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True,
                           text=True, check=True).stdout.split()
    text = ""
    for name in files:
        if name.startswith("quellen/") or name.endswith("literatur.bib"):
            continue
        if re.search(r"\.(adoc|md|py|yml|json|sh)$", name):
            text += (REPO / name).read_text(encoding="utf-8", errors="ignore")
    cited = {k.strip().split("(")[0] for group in re.findall(r"cite[pt]?:\[([^\]]+)\]", text)
             for k in group.split(",")}
    return cited, norm_url(text)


def needed(item, usage):
    cited, text = usage
    url = norm_url(item.get("url", ""))
    return pinned_key(item) in cited or pinned_key(item) in KEEP_SNAPSHOT or (url and url in text)


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


def domain(url):
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    return ".".join(host.split(".")[-2:]).lower()


def same_source(new, old):
    """Same URL, or same domain with one title starting like the other."""
    if not new.get("url") or not old.get("url"):
        return False
    if norm_url(new["url"]) == norm_url(old["url"]):
        return True
    a, b = slug(new.get("title", ""), 99), slug(old.get("title", ""), 99)
    return (domain(new["url"]) == domain(old["url"]) and min(len(a), len(b)) >= 6
            and (a.startswith(b) or b.startswith(a)))


def best_match(new, pinned, inbox):
    """The pinned item a Connector save belongs to.

    Saves are made for items in the Inbox, so an Inbox item on the same domain wins
    over an exact URL match elsewhere. Redirects like ifixit.com/api to /api-docs
    would otherwise attach the snapshot to an unused neighbour where it gets pruned.
    """
    if not new.get("url"):
        return None
    waiting = [o for o in pinned if inbox in o.get("collections", []) and o.get("url")
               and domain(o["url"]) == domain(new["url"])]
    exact = [o for o in pinned if o.get("url") and norm_url(o["url"]) == norm_url(new["url"])]
    for group in ([o for o in waiting if o in exact], [o for o in waiting if same_source(new, o)],
                  waiting if len(waiting) == 1 else [], exact,
                  [o for o in pinned if same_source(new, o)]):
        if group:
            return group[0]
    return None


def fold(dup, old, key):
    """Move the attachments of dup to old, fill empty fields of old and delete dup."""
    for child in fetch_all(f"/items/{dup['key']}/children", key):
        child["parentItem"] = old["key"]
        request("/items", [child], key=key)
    for field in FILL:
        if dup.get(field) and field in old and not old[field]:
            old[field] = dup[field]
    if not old.get("creators") and dup.get("creators"):
        old["creators"] = dup["creators"]
    tags = {t["tag"] for t in old.get("tags", [])}
    old["tags"] = old.get("tags", []) + [t for t in dup.get("tags", []) if t["tag"] not in tags]
    request("/items", [old], key=key)
    request(f"/items/{dup['key']}", key=key, method="DELETE",
            extra_headers={"If-Unmodified-Since-Version": str(dup["version"])})


def merge(key):
    items = [d for d in fetch_all("/items/top", key) if d["itemType"] not in ("attachment", "note")]
    pinned = [d for d in items if "Citation Key:" in d.get("extra", "")]
    used = {pinned_key(d) for d in pinned}
    inbox = collection_keys(key)[0]
    moved, changed, deleted, keyed, waiting = [], {}, [], [], []
    for d in items:
        if d in pinned:
            continue
        old = best_match(d, pinned, inbox)
        if old is None:
            pin(d, new_key(d, used))
            keyed.append(d)
            continue
        children = fetch_all(f"/items/{d['key']}/children", key)
        age = time.time() - time.mktime(time.strptime(d["dateModified"], "%Y-%m-%dT%H:%M:%SZ")) + time.timezone
        if not children and age < 600:
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
        changed[old["key"]] = old
        d["target"] = pinned_key(old)
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
        print(f"zusammengeführt: {d.get('title', '')[:60]} -> {d['target']}")
    for d in keyed:
        print(f"neu: {d['citationKey']} {d.get('title', '')[:60]}")
    for d in waiting:
        print(f"wartet, noch ohne Anhang: {d.get('title', '')[:60]}")
    if not deleted and not keyed and not waiting:
        print("nichts zusammenzuführen")
    sort_collections(key)


def collection_keys(key):
    found = {c["name"]: c["key"] for c in fetch_all("/collections", key)}
    missing = [{"name": n} for n in (INBOX, ATTACHED) if n not in found]
    if missing:
        result, _ = request("/collections", missing, key=key)
        for c in result["successful"].values():
            found[c["data"]["name"]] = c["key"]
    return found[INBOX], found[ATTACHED]


def prune_snapshots(items, usage, key):
    """Delete HTML snapshots of sources the repo does not use."""
    unused = {d["key"] for d in items if not needed(d, usage)}
    doomed = [a for a in fetch_all("/items?itemType=attachment", key)
              if a.get("parentItem") in unused and a.get("contentType") == "text/html"
              and a.get("linkMode") in ("imported_url", "imported_file")]
    for start in range(0, len(doomed), 50):
        _, headers = request("/items?limit=1", key=key)
        request("/items?itemKey=" + ",".join(a["key"] for a in doomed[start:start + 50]), key=key,
                method="DELETE", extra_headers={"If-Unmodified-Since-Version":
                                                headers["Last-Modified-Version"]})
    if doomed:
        print(f"{len(doomed)} Snapshots ungenutzter Quellen gelöscht")


def sort_collections(key):
    inbox, attached = collection_keys(key)
    it = {c["name"]: c["key"] for c in fetch_all("/collections", key)}.get(IT)
    usage = repo_usage()
    items = [d for d in fetch_all("/items/top", key) if d["itemType"] not in ("attachment", "note")]
    prune_snapshots(items, usage, key)
    parents = {a.get("parentItem") for a in fetch_all("/items?itemType=attachment", key)}
    updates = []
    for d in items:
        if it in d.get("collections", []):
            continue
        cols = set(d.get("collections", [])) - {inbox, attached}
        if d["key"] in parents:
            cols.add(attached)
        elif d["itemType"] != "computerProgram" and needed(d, usage):
            cols.add(inbox)
        tags = [t for t in d.get("tags", []) if t["tag"] != TAG]
        if cols != set(d.get("collections", [])) or tags != d.get("tags", []):
            d["collections"], d["tags"] = sorted(cols), tags
            updates.append(d)
    for start in range(0, len(updates), 50):
        result, _ = request("/items", updates[start:start + 50], key=key)
        if result.get("failed"):
            sys.exit(json.dumps(result["failed"], ensure_ascii=False, indent=1))
    in_inbox = sum(1 for d in fetch_all(f"/collections/{inbox}/items/top", key))
    in_attached = sum(1 for d in fetch_all(f"/collections/{attached}/items/top", key))
    print(f"{len(updates)} Einträge einsortiert, {INBOX} {in_inbox}, {ATTACHED} {in_attached}")


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
