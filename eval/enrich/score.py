#!/usr/bin/env python3
"""Compares the answers of enrich.py with the values volunteers kept, one row per ticket and field, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

For every field the row says whether volunteers filled it, whether the model filled it and, where both
did, whether the model hit the value:
    name     brand and model, equal after lower case without spaces and punctuation, or one contains the other
    exact    year and power supply, equal
    result   result of the repair, equal, and in top_hit equal on the first level
    text     defect and solution, no hit, but the cosine similarity of both texts with bge-m3
The rows hold no content and go to score/scores.tsv in the folder of the run, summary.R counts them.
A folder without answers.jsonl gets the starting point, what volunteers kept in all device tickets.

Run in the repository root, Ollama from OLLAMA_URL (default http://manuel:11434):
    python3 -I eval/enrich/score.py EXPORT_DIR RUN_DIR [RUN_DIR ...]
"""

import csv
import json
import math
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import tickets as source  # noqa: E402
from lauf import write_run  # noqa: E402

URL = os.environ.get("OLLAMA_URL", "http://manuel:11434")
EMBED = "bge-m3"


def embed(texts):
    body = json.dumps({"model": EMBED, "input": texts, "keep_alive": 600}).encode()
    request = urllib.request.Request(f"{URL}/api/embed", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.load(response)["embeddings"]


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def norm(value):
    return re.sub(r"[\W_]+", "", str(value).lower())


def compare(kind, human, model):
    """Returns hit and top_hit as 1, 0 or empty."""
    if kind == "name":
        a, b = norm(human), norm(model)
        return int(bool(a and b) and (a == b or (min(len(a), len(b)) >= 2 and (a in b or b in a)))), ""
    if kind == "exact":
        return int(str(human).strip() == str(model).strip()), ""
    if kind == "result":
        return int(human == model), int(human.split("::")[0] == model.split("::")[0])
    return "", ""


def main():
    export, runs = Path(sys.argv[1]), [Path(p).expanduser() for p in sys.argv[2:]]
    tickets_file, tickets = source.load(export)
    by_id = {t["id"]: t for t in tickets}
    for run in runs:
        answers_file = run / "answers.jsonl"
        if answers_file.exists():
            answers = [json.loads(line) for line in answers_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            # Without answers the folder holds the starting point, what volunteers kept in all tickets
            answers_file = None
            answers = [{"ticket": t["id"], "fields": {}} for t in tickets]
        rows, pairs = [], []
        for answer in answers:
            ticket = by_id.get(answer["ticket"])
            if ticket is None:
                continue
            for old, (new, kind) in source.FIELDS.items():
                human = source.human(ticket, old)
                model = (answer["fields"].get(old) or "").strip() or None
                hit, top_hit = compare(kind, human, model) if human is not None and model is not None else ("", "")
                row = {"ticket": ticket["id"], "year": ticket["created_at"][:4], "field": new,
                       "human": int(human is not None), "model": int(model is not None),
                       "error": int(bool(answer.get("error"))), "hit": hit, "top_hit": top_hit, "similarity": ""}
                if kind == "text" and human is not None and model is not None:
                    pairs.append((row, str(human), model))
                rows.append(row)
        for start in range(0, len(pairs), 32):
            chunk = pairs[start:start + 32]
            vectors = embed([h for _, h, _ in chunk] + [m for _, _, m in chunk])
            for i, (row, _, _) in enumerate(chunk):
                row["similarity"] = round(cosine(vectors[i], vectors[len(chunk) + i]), 4)
        folder = run / "score"
        folder.mkdir(parents=True, exist_ok=True)
        output = folder / "scores.tsv"
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        write_run(folder, inputs=[p for p in (tickets_file, answers_file, HERE / "score.py", HERE / "tickets.py") if p], outputs=[output],
                  models=[EMBED], ollama_url=URL, extra={"step": "score"})
        print(f"{run.name}: {len(answers)} Tickets, {len(rows)} Zeilen in {output}")


if __name__ == "__main__":
    main()
