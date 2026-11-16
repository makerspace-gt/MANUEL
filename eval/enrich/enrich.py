#!/usr/bin/env python3
"""Lets a model fill the fields of each device ticket from its articles, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

The model sees the articles only, never the field values volunteers kept, so score.py can compare its
answers with them. Every ticket gets the same prompt from prompt.de.md and the same JSON schema. The
answers hold real ticket content and stay local, by default in ~/bench/manuel-enrich/<date>/<model>/answers.jsonl, next to
lauf.json after docs/adr/0027-laeufe-reproduzierbar-festhalten.adoc. A second run with the same
output continues where the first stopped.

Run in the repository root, Ollama from OLLAMA_URL (default http://manuel:11434):
    python3 -I eval/enrich/enrich.py EXPORT_DIR MODEL [--limit N] [--seed 1] [--think no] [--out DIR]
EXPORT_DIR is a folder of zammad/export_tickets.py. --limit takes a fixed random sample, the same for
every model with the same seed.
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import tickets as source  # noqa: E402
from lauf import write_run  # noqa: E402

URL = os.environ.get("OLLAMA_URL", "http://manuel:11434")


def schema(results):
    def choice(values):
        return {"type": "string", "enum": [""] + values}

    properties = {
        "marke": {"type": "string"},
        "bezeichnung": {"type": "string"},
        "baujahr": {"type": "string"},
        "stromversorgung": choice(source.POWER),
        "notiz": {"type": "string"},
        "hack": {"type": "string"},
        "ergebnis": choice(results),
    }
    return {"type": "object", "properties": properties, "required": list(properties)}


def chat(model, prompt, fmt, think):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "format": fmt, "stream": False,
            "options": {"temperature": 0, "seed": 1}, "keep_alive": 600}
    if think is not None:
        body["think"] = think
    request = urllib.request.Request(f"{URL}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path)
    parser.add_argument("model")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--think", choices=["yes", "no"])
    parser.add_argument("--out", type=Path, default=Path(f"~/bench/manuel-enrich/{date.today()}").expanduser())
    args = parser.parse_args()

    tickets_file, tickets = source.load(args.export)
    if args.limit:
        tickets = sorted(random.Random(args.seed).sample(tickets, min(args.limit, len(tickets))), key=lambda t: t["id"])
    template = (HERE / "prompt.de.md").read_text(encoding="utf-8")
    fmt = schema(source.results(source.load(args.export)[1]))
    think = None if args.think is None else args.think == "yes"

    folder = args.out / args.model.replace(":", "-").replace("/", "-")
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "answers.jsonl"
    done = set()
    if output.exists():
        done = {json.loads(line)["ticket"] for line in output.read_text(encoding="utf-8").splitlines() if line.strip()}

    with output.open("a", encoding="utf-8") as handle:
        for index, ticket in enumerate(tickets, 1):
            if ticket["id"] in done:
                continue
            started = time.monotonic()
            try:
                answer = chat(args.model, template.replace("{text}", source.text(ticket)), fmt, think)
                fields = json.loads(answer["message"]["content"])
                error = None
            except (OSError, ValueError, KeyError) as exc:
                fields, error, answer = {}, f"{type(exc).__name__}: {exc}"[:300], {}
            handle.write(json.dumps({"ticket": ticket["id"], "fields": fields, "error": error,
                                     "seconds": round(time.monotonic() - started, 1),
                                     "eval_count": answer.get("eval_count"), "prompt_eval_count": answer.get("prompt_eval_count")},
                                    ensure_ascii=False) + "\n")
            handle.flush()
            if index % 10 == 0:
                print(f"{index} von {len(tickets)} Tickets", flush=True)

    write_run(output, inputs=[tickets_file, HERE / "prompt.de.md", HERE / "tickets.py"], outputs=[output],
              models=[args.model], ollama_url=URL,
              extra={"limit": args.limit, "seed": args.seed, "think": args.think, "tickets": len(tickets)})
    print(f"{len(tickets)} Tickets mit {args.model} in {output}")


if __name__ == "__main__":
    main()
