#!/usr/bin/env python3
"""Runs one task of MANUEL with one model on the device tickets of an export, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

Each task gets the input MANUEL would have at its moment and never the field values volunteers kept,
so score.py can compare the answers with them. The prompts are built as Zammad builds those of its AI
agents (quellen/zammad, ai_agent.txt.erb), so a result holds for the agents in Zammad as well.

    category     Ticket Categorizer of Zammad with the A and B entries of the catalog, first article only,
                 as eval/categorizer/vorabtest.py. Reference is the target of the team, eval/categorizer
    category-d3  check of the device type after docs/adr/0068-art-des-geraets-mit-d3-pruefen.adoc, bge-m3
                 shortlist and the decision model, first article only. MODEL is the decision model
    device       brand and model from the articles before the appointment, prompts/device.*
    problem      the defect as the guest describes it, articles before the appointment, prompts/problem.*
    solution     the solution agent of zammad/prompts/solution_approach.*, articles before the
                 appointment with device type, brand and model as the agent sees them. judge.py rates it

The answers hold real ticket content and stay local, by default in
~/bench/manuel-enrich/<date>/<task>/<model>/answers.jsonl next to lauf.json after
docs/adr/0027-laeufe-reproduzierbar-festhalten.adoc. A second run continues where the first stopped.

Run in the repository root, Ollama from OLLAMA_URL (default http://manuel:11434):
    python3 -I eval/enrich/enrich.py TASK EXPORT_DIR MODEL [--limit N] [--seed 1] [--think no]
        [--targets ~/bench/vorabtest/soll.tsv] [--out DIR]
--limit takes a fixed random sample, the same for every model and task with the same seed.
Every answer keeps its start and end as Unix time, so eval/strom/energy.py can add the energy from a
recording of eval/strom/sample.py.
"""

import argparse
import csv
import json
import os
import random
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "eval" / "categorizer"))

import tickets as source  # noqa: E402
from lauf import write_run  # noqa: E402

URL = os.environ.get("OLLAMA_URL", "http://manuel:11434").rstrip("/")
TASKS = ["category", "category-d3", "device", "problem", "solution"]
SOLUTION_PROMPTS = ROOT / "zammad" / "prompts"


def prompt(name):
    return (HERE / "prompts" / name).read_text(encoding="utf-8").strip()


def chat(model, system, user, think):
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": "json", "stream": False, "options": {"temperature": 0, "seed": 1}, "keep_alive": 600}
    if think is not None:
        body["think"] = think
    request = urllib.request.Request(f"{URL}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        answer = json.load(response)
    return json.loads(answer["message"]["content"] or "{}"), answer


class Task:
    """Builds the prompts of a task and turns an answer into fields."""

    def __init__(self, name, model, think, targets):
        self.name, self.model, self.think, self.targets = name, model, think, targets
        self.inputs = []
        if name == "category":
            import vorabtest
            self.items = vorabtest.options("ab")
            self.system = vorabtest.system_prompt(self.items)
            self.vorabtest = vorabtest
            self.inputs = [vorabtest.ABC, vorabtest.CATALOG, ROOT / "eval/categorizer/vorabtest.py"]
        elif name == "category-d3":
            os.environ.setdefault("OLLAMA_URL", URL)
            os.environ["DECISION_MODEL"] = model
            os.environ.setdefault("CACHE", str(Path("~/bench/manuel-enrich/category_check_vectors.json").expanduser()))
            sys.path.insert(0, str(ROOT / "category_check"))
            import server
            self.checker = server.Catalog()
            self.inputs = [ROOT / "category_check/server.py", ROOT / "katalog/kategorien.tsv"]
        else:
            folder, stem = (SOLUTION_PROMPTS, "solution_approach") if name == "solution" else (HERE / "prompts", name)
            role = (folder / f"{stem}.role.md").read_text(encoding="utf-8").strip()
            instruction = (folder / f"{stem}.instruction.md").read_text(encoding="utf-8").strip()
            structure = {"device": {"brand": "string", "device_model": "string"}, "problem": {"problem": "string"},
                         "solution": {"note": "string"}}[name]
            self.system = source.zammad_system_prompt(role, instruction, structure)
            self.inputs = [folder / f"{stem}.role.md", folder / f"{stem}.instruction.md"]

    def wanted(self, ticket):
        return self.name not in ("category", "category-d3") or str(ticket["number"]) in self.targets

    def run(self, ticket, names):
        if self.name == "category":
            first = source.articles(ticket, "first")
            message = source.plain(first[0])[:source.ARTICLE_CHARS] if first else ""
            fields, answer = chat(self.model, self.system, self.vorabtest.user_prompt(ticket["title"], message), False)
            value = fields.get(self.vorabtest.FIELD, "")
            return {"device_type": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}, answer
        if self.name == "category-d3":
            first = source.articles(ticket, "first")
            text = f"{ticket['title']}\n{source.plain(first[0]) if first else ''}"[:2000]
            result = self.checker.check(text, ticket["title"])
            return {"device_type": result["key"], "p": result["p"]}, {}
        attributes = None
        if self.name == "solution":
            # What the agent sees a week before: the device type the team set and the fields kept by then
            key = self.targets.get(str(ticket["number"]))
            attributes = {"device_type": ("Art des Geräts", names.get(key, "")),
                          "brand": ("Marke", ticket.get("marke") or ""),
                          "device_model": ("Bezeichnung", ticket.get("bezeichnung") or "")}
        user = source.zammad_user_prompt(ticket, source.articles(ticket, "appointment"), attributes)
        return chat(self.model, self.system, user, self.think)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("task", choices=TASKS)
    parser.add_argument("export", type=Path)
    parser.add_argument("model")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--think", choices=["yes", "no"])
    parser.add_argument("--targets", type=Path, default=Path("~/bench/vorabtest/soll.tsv").expanduser())
    parser.add_argument("--out", type=Path, default=Path(f"~/bench/manuel-enrich/{date.today()}").expanduser())
    args = parser.parse_args()

    tickets_file, tickets = source.load(args.export)
    targets = {}
    if args.targets.exists():
        targets = {row["ticket"]: row["key"] for row in csv.DictReader(args.targets.open(encoding="utf-8"), delimiter="\t")}
    names = {row["key"]: row["name"] for row in csv.DictReader((ROOT / "katalog/kategorien.tsv").open(encoding="utf-8"), delimiter="\t")}
    think = None if args.think is None else args.think == "yes"
    task = Task(args.task, args.model, think, targets)

    if args.limit:
        tickets = sorted(random.Random(args.seed).sample(tickets, min(args.limit, len(tickets))), key=lambda t: t["id"])
    tickets = [t for t in tickets if task.wanted(t)]

    folder = args.out / args.task / args.model.replace(":", "-").replace("/", "-")
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "answers.jsonl"
    done = set()
    if output.exists():
        done = {json.loads(line)["ticket"] for line in output.read_text(encoding="utf-8").splitlines() if line.strip()}

    with output.open("a", encoding="utf-8") as handle:
        for index, ticket in enumerate(tickets, 1):
            if ticket["id"] in done:
                continue
            started, wall = time.monotonic(), time.time()
            try:
                fields, answer = task.run(ticket, names)
                error = None
            except (OSError, ValueError, KeyError) as exc:
                fields, answer, error = {}, {}, f"{type(exc).__name__}: {exc}"[:300]
            handle.write(json.dumps({"task": args.task, "ticket": ticket["id"], "number": ticket["number"], "fields": fields,
                                     "error": error, "seconds": round(time.monotonic() - started, 1),
                                     "start": round(wall, 3), "end": round(time.time(), 3),
                                     "eval_count": answer.get("eval_count"), "prompt_eval_count": answer.get("prompt_eval_count")},
                                    ensure_ascii=False) + "\n")
            handle.flush()
            if index % 25 == 0:
                print(f"{index} von {len(tickets)} Tickets", flush=True)

    inputs = [tickets_file, HERE / "tickets.py", HERE / "enrich.py", *task.inputs]
    if args.task in ("category", "category-d3", "solution") and args.targets.exists():
        inputs.append(args.targets)
    write_run(output, inputs=inputs, outputs=[output], models=[args.model], ollama_url=URL,
              zammad=args.task != "category-d3",
              extra={"task": args.task, "limit": args.limit, "seed": args.seed, "think": args.think, "tickets": len(tickets)})
    print(f"{args.task}: {len(tickets)} Tickets mit {args.model} in {output}")


if __name__ == "__main__":
    main()
