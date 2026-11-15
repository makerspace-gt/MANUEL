#!/usr/bin/env python3
"""Deletes old mails from the folders of a mailbox, independent of the mail provider.

Folders and days come from retention.tsv next to this script. Without --apply the script only counts
what it would delete. With --apply it marks mails older than the limit as deleted and expunges the
folder. The date is the internal date of the server, so it uses only standard IMAP. Access data come
from an env file and are never printed, see docs/adr/0065-postfach-archivieren-und-aufbewahrung-begrenzen.adoc.

The env file holds:
    IMAP_HOST=mail.example.org
    IMAP_USER=repair@example.org
    IMAP_PASSWORD=...
    IMAP_PORT=993

Run:
    python3 mail/imap_retention.py --env ~/.config/manuel/imap.env [--apply]
"""

import argparse
import csv
import datetime as dt
import imaplib
import sys
from pathlib import Path

RETENTION = Path(__file__).with_name("retention.tsv")


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def read_rules(path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    return [(row["folder"], int(row["days"])) for row in csv.DictReader(lines, delimiter="\t")]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", type=Path, default=Path("~/.config/manuel/imap.env").expanduser())
    parser.add_argument("--rules", type=Path, default=RETENTION)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--starttls", action="store_true", help="plain connection with STARTTLS instead of SSL")
    parser.add_argument("--today", help="date to compute from, for tests, YYYY-MM-DD")
    args = parser.parse_args()

    env = read_env(args.env)
    for key in ("IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"):
        if not env.get(key):
            sys.exit(f"{key} fehlt in {args.env}")
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    port = int(env.get("IMAP_PORT") or (143 if args.starttls else 993))
    if args.starttls:
        imap = imaplib.IMAP4(env["IMAP_HOST"], port)
        imap.starttls()
    else:
        imap = imaplib.IMAP4_SSL(env["IMAP_HOST"], port)
    imap.login(env["IMAP_USER"], env["IMAP_PASSWORD"])
    try:
        for folder, days in read_rules(args.rules):
            status, _ = imap.select(f'"{folder}"')
            if status != "OK":
                print(f"{folder}: Ordner nicht gefunden")
                continue
            before = (today - dt.timedelta(days=days)).strftime("%d-%b-%Y")
            _, data = imap.search(None, "BEFORE", before)
            ids = data[0].split()
            print(f"{folder}: {len(ids)} Mails vor {before}, {'gelöscht' if args.apply and ids else 'Probelauf' if ids else 'nichts zu tun'}")
            if args.apply and ids:
                for start in range(0, len(ids), 500):
                    imap.store(b",".join(ids[start:start + 500]).decode(), "+FLAGS", "\\Deleted")
                imap.expunge()
            imap.close()
    finally:
        imap.logout()


if __name__ == "__main__":
    main()
