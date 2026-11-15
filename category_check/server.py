#!/usr/bin/env python3
"""Checks the device type of a ticket with the decision model d3:9b, see
docs/adr/0068-art-des-geraets-mit-d3-pruefen.adoc.

The chain is the one of ADR 10 and 11: bge-m3 finds the 25 entries of the catalog whose names are most
similar to the text, each under its best name, d3:9b chooses one of them with a probability, and the rules
of eval/decision/follow_up.py say whether MANUEL would ask back. Zammad calls it from
zammad/category_check.rb. Nothing is stored, the text of the ticket only passes through.

POST /check with {"text": "..."} answers {"key", "name", "label", "p", "reason"}.
GET /health answers ok once the names are embedded.

Settings from the environment:
    OLLAMA_URL       http://127.0.0.1:11434
    DECISION_MODEL   d3:9b
    CATALOG          katalog/kategorien.tsv
    FORM             quellen/anstiftung/kategorien.csv
    CACHE            file for the vectors of the names, rebuilt when the names change
    PORT             8090

Run in the repository root:
    python3 category_check/server.py
"""

import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "katalog"), str(ROOT / "eval" / "decision")]

import decision  # noqa: E402
import entries as catalog_entries  # noqa: E402
from follow_up import THRESHOLD, reason  # noqa: E402
from real2 import embed, unit  # noqa: E402

decision.URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("DECISION_MODEL", "d3:9b")
SIZE = 25
QUESTION = "Welche Kategorie beschreibt diesen Gegenstand am besten?"
MAX_TEXT = 2000


class Catalog:
    def __init__(self):
        form = catalog_entries.read_form(os.environ.get("FORM", ROOT / "quellen/anstiftung/kategorien.csv"))
        self.entries = catalog_entries.build(form, catalog=os.environ.get("CATALOG", ROOT / "katalog/kategorien.tsv"))
        self.labels, self.owner = [], []
        for index, entry in enumerate(self.entries):
            for name in entry["namen"]:
                if name not in self.labels:
                    self.labels.append(name)
                    self.owner.append(index)
        self.vectors = self.load_vectors()

    def load_vectors(self):
        digest = hashlib.sha256("\n".join(self.labels).encode()).hexdigest()
        cache = Path(os.environ.get("CACHE", "/tmp/category_check_vectors.json"))
        if cache.exists():
            stored = json.loads(cache.read_text())
            if stored.get("digest") == digest:
                return stored["vectors"]
        vectors = []
        for start in range(0, len(self.labels), 64):
            vectors += [unit(v) for v in embed(self.labels[start:start + 64])]
        cache.write_text(json.dumps({"digest": digest, "vectors": vectors}))
        return vectors

    def shortlist(self, text):
        query = unit(embed([text])[0])
        scored = sorted(((sum(a * b for a, b in zip(query, v)), i) for i, v in enumerate(self.vectors)), reverse=True)
        seen, options = set(), []
        for _, i in scored:
            if self.owner[i] not in seen:
                seen.add(self.owner[i])
                options.append(i)
                if len(options) == SIZE:
                    break
        return options

    def check(self, text, subject=""):
        options = self.shortlist(text)
        labels = [self.labels[i] for i in options]
        answer = decision.post("/v1/systemone", {
            "model": MODEL, "keep_alive": 600, "state": text,
            "questions": {"kategorie": {"type": "choice", "instructions": QUESTION,
                                        "criteria": {label: None for label in labels}}},
        })["answers"]["kategorie"]
        label = answer["choice"]
        entry = self.entries[self.owner[options[labels.index(label)]]]
        p = answer["probabilities"][label]
        return {"key": entry["schluessel"], "name": entry["name"], "label": label, "p": round(p, 4),
                "reason": reason(entry["name"], label.split(" / ", 1)[-1], subject, p, THRESHOLD)}


class Handler(BaseHTTPRequestHandler):
    catalog = None

    def reply(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        self.reply(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})

    def do_POST(self):  # noqa: N802
        if self.path != "/check":
            return self.reply(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            text = str(body.get("text", "")).strip()[:MAX_TEXT]
            if not text:
                return self.reply(400, {"error": "text missing"})
            self.reply(200, self.catalog.check(text, str(body.get("subject", ""))))
        except Exception as problem:  # One failed request must not stop the service
            self.reply(500, {"error": str(problem)[:300]})

    def log_message(self, *args):
        # Requests carry texts of guests, so they are not logged
        pass


def main():
    Handler.catalog = Catalog()
    port = int(os.environ.get("PORT", "8090"))
    print(f"{len(Handler.catalog.entries)} Einträge, {len(Handler.catalog.labels)} Namen, Port {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
