#!/usr/bin/env python3
"""Proposes a group from ora-gruppen.tsv for each category of the form.

The decision model sees top category and category and chooses one of the 46 groups. The result
is a draft that people check. The category list belongs to anstiftung and is not in the repo.

Usage:
    python3 groups.py <formular.csv> <ora-gruppen.tsv> <output.jsonl> <model>
"""

import csv
import json
import sys
import time

from decision import post


def groups(path):
    found = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        _, name, text = line.rstrip("\n").split("\t")
        found[name] = text
    return found


def main():
    csv_file, groups_file, output, model = sys.argv[1:5]
    criteria = groups(groups_file)
    with open(csv_file, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with open(output, "w", encoding="utf-8") as out:
        for row in rows:
            state = f"Oberkategorie: {row['Oberkategorie']}. Gerät oder Gegenstand: {row['Unterkategorie']}"
            result = {"ober": row["Oberkategorie"], "kategorie": row["Unterkategorie"], "id": row["id"], "fehler": None}
            start = time.monotonic()
            try:
                answer = post("/v1/systemone", {
                    "model": model, "keep_alive": 600, "state": state,
                    "questions": {"gruppe": {
                        "type": "choice",
                        "instructions": "Zu welcher Gruppe gehört dieser Gegenstand?",
                        "criteria": criteria,
                    }},
                })["answers"]["gruppe"]
                ranked = sorted(answer["probabilities"].items(), key=lambda item: -item[1])
                result["gruppe"] = answer["choice"]
                result["p"] = answer["probabilities"][answer["choice"]]
                result["zweite"] = ranked[1][0]
                result["zweite_p"] = ranked[1][1]
            except Exception as problem:  # An error must not stop the rest of the run
                detail = problem.read().decode() if hasattr(problem, "read") else ""
                result["fehler"] = f"{problem} {detail}"[:300]
            result["sekunden"] = round(time.monotonic() - start, 3)
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
