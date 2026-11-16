#!/usr/bin/env python3
"""Compares the answers of enrich.py with the reference of each task, one row per ticket and field, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

    category, category-d3  device_type against the target of the team. hit is the same entry of the
                           catalog, top_hit the same ORA group
    device                 brand and device_model against the old fields marke and bezeichnung. hit if
                           equal in lower case without spaces and punctuation, or one contains the other
    problem                problem_reported against the old field notiz, cosine similarity with bge-m3
    solution               the verdict of judge.py against the old field hack. hit is yes, top_hit yes
                           or partly, unclear counts as not compared
    baseline               a folder without answers.jsonl, what volunteers kept in all device tickets

human says whether a reference exists, model whether the model answered. The rows hold no content and go
to score/scores.tsv in the folder of the run, summary.R counts them.

Run in the repository root, Ollama from OLLAMA_URL (default http://manuel:11434):
    python3 -I eval/enrich/score.py EXPORT_DIR RUN_DIR [RUN_DIR ...] [--targets ~/bench/vorabtest/soll.tsv]
"""

import argparse
import csv
import json
import math
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import tickets as source  # noqa: E402
from lauf import write_run  # noqa: E402

URL = os.environ.get("OLLAMA_URL", "http://manuel:11434").rstrip("/")
EMBED = "bge-m3"
BASELINE = {"marke": "brand", "bezeichnung": "device_model", "baujahr": "year_of_manufacture",
            "stromversorgung": "power_supply", "notiz": "problem_reported", "hack": "solution", "ergebnis": "repair_result"}


def embed(texts):
    body = json.dumps({"model": EMBED, "input": texts, "keep_alive": 600}).encode()
    request = urllib.request.Request(f"{URL}/api/embed", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)["embeddings"]


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def norm(value):
    return re.sub(r"[\W_]+", "", str(value).lower())


def same_name(human, model):
    a, b = norm(human), norm(model)
    return int(bool(a and b) and (a == b or (min(len(a), len(b)) >= 2 and (a in b or b in a))))


def row(ticket, task, field, human, model, hit="", top_hit="", error=False):
    return {"ticket": ticket["id"], "year": ticket["created_at"][:4], "task": task, "field": field,
            "human": int(human), "model": int(model), "error": int(error), "hit": hit, "top_hit": top_hit, "similarity": ""}


def score(task, answers, by_id, targets, catalog, judged):
    rows, pairs = [], []
    for answer in answers:
        ticket = by_id.get(answer["ticket"])
        if ticket is None:
            continue
        fields, error = answer.get("fields") or {}, bool(answer.get("error"))
        if task in ("category", "category-d3"):
            target, value = targets.get(str(ticket["number"])), (fields.get("device_type") or "").strip()
            hit = top = ""
            if target and value:
                hit = int(value == target)
                top = int(hit or (value in catalog and catalog[value]["ora_group"] == catalog.get(target, {}).get("ora_group")))
            rows.append(row(ticket, task, "device_type", bool(target), bool(value), hit, top, error))
        elif task == "device":
            for old, new in (("marke", "brand"), ("bezeichnung", "device_model")):
                human, value = source.human(ticket, old), (fields.get(new) or "").strip()
                hit = same_name(human, value) if human and value else ""
                rows.append(row(ticket, task, new, bool(human), bool(value), hit, "", error))
        elif task == "problem":
            human, value = source.human(ticket, "notiz"), (fields.get("problem") or "").strip()
            r = row(ticket, task, "problem_reported", bool(human), bool(value), "", "", error)
            if human and value:
                pairs.append((r, str(human), value))
            rows.append(r)
        elif task == "solution":
            human, value = source.human(ticket, "hack"), (fields.get("note") or "").strip()
            verdict = judged.get(ticket["id"], "")
            hit = top = ""
            if human and value and verdict in ("yes", "partly", "no"):
                hit, top = int(verdict == "yes"), int(verdict in ("yes", "partly"))
            rows.append(row(ticket, task, "solution", bool(human), bool(value), hit, top, error))
    for start in range(0, len(pairs), 32):
        chunk = pairs[start:start + 32]
        vectors = embed([h for _, h, _ in chunk] + [m for _, _, m in chunk])
        for i, (r, _, _) in enumerate(chunk):
            r["similarity"] = round(cosine(vectors[i], vectors[len(chunk) + i]), 4)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--targets", type=Path, default=Path("~/bench/vorabtest/soll.tsv").expanduser())
    args = parser.parse_args()

    tickets_file, tickets = source.load(args.export)
    by_id = {t["id"]: t for t in tickets}
    targets = {}
    if args.targets.exists():
        targets = {r["ticket"]: r["key"] for r in csv.DictReader(args.targets.open(encoding="utf-8"), delimiter="\t")}
    catalog = {r["key"]: r for r in csv.DictReader((ROOT / "katalog/kategorien.tsv").open(encoding="utf-8"), delimiter="\t")}

    for run in (r.expanduser() for r in args.runs):
        answers_file = run / "answers.jsonl"
        inputs = [tickets_file, HERE / "score.py", HERE / "tickets.py"]
        if answers_file.exists():
            answers = [json.loads(line) for line in answers_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            task = answers[0]["task"] if answers else run.parent.name
            judge_file = run / "judge" / "answers.jsonl"
            judged = {}
            if judge_file.exists():
                judged = {json.loads(l)["ticket"]: json.loads(l)["verdict"] for l in judge_file.read_text(encoding="utf-8").splitlines() if l.strip()}
                inputs.append(judge_file)
            rows = score(task, answers, by_id, targets, catalog, judged)
            inputs += [answers_file] + ([args.targets] if task.startswith("category") else [])
        else:
            rows = [row(t, "baseline", new, source.human(t, old) is not None, False) for t in tickets for old, new in BASELINE.items()]
        folder = run / "score"
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / "scores.tsv"
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        write_run(folder, inputs=inputs, outputs=[output], models=[EMBED], ollama_url=URL, extra={"step": "score"})
        print(f"{run.parent.name}/{run.name}: {len(rows)} Zeilen in {output}")


if __name__ == "__main__":
    main()
