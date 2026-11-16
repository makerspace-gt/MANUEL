#!/usr/bin/env python3
"""Adds the energy of every answer of a run from a recording of eval/strom/sample.py, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

For each answer of answers.jsonl the power between its start and end is integrated with the trapezoid
rule, once at the plug and once for the GPU. The idle power is the median at the plug of all samples
outside any answer, so the extra energy of an answer is what it draws above idle. Readings below 1 W at
the plug count as missing, the plug reports 0 W for a moment when it restarts. The rows hold no content
and go to energy/energy.tsv in the folder of the run, summary.R adds them up.

Run in the repository root:
    python3 -I eval/strom/energy.py POWER_CSV RUN_DIR [RUN_DIR ...]
"""

import csv
import json
import statistics
import sys
from bisect import bisect_left, bisect_right
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lauf import write_run  # noqa: E402


def load(path):
    samples = []
    with open(path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                plug = float(row["plug_w"]) if row["plug_w"] and float(row["plug_w"]) >= 1 else None
            except ValueError:
                plug = None
            gpu = float(row["gpu_w"]) if row.get("gpu_w") else None
            samples.append((float(row["time"]), plug, gpu))
    return samples


def integrate(samples, start, end, column):
    """Energy in Wh between start and end, with the nearest samples just outside as edges."""
    times = [s[0] for s in samples]
    lo, hi = max(0, bisect_left(times, start) - 1), min(len(samples), bisect_right(times, end) + 1)
    points = [(samples[i][0], samples[i][column]) for i in range(lo, hi) if samples[i][column] is not None]
    if len(points) < 2:
        return None, 0
    joules = 0.0
    for (t0, p0), (t1, p1) in zip(points, points[1:]):
        a, b = max(t0, start), min(t1, end)
        if b > a:
            joules += (p0 + p1) / 2 * (b - a)
    return joules / 3600, sum(1 for t, _ in points if start <= t <= end)


def main():
    power_csv, runs = Path(sys.argv[1]).expanduser(), [Path(p).expanduser() for p in sys.argv[2:]]
    samples = load(power_csv)
    for run in runs:
        answers_file = run / "answers.jsonl"
        answers = [json.loads(line) for line in answers_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        answers = [a for a in answers if a.get("start") and samples[0][0] <= a["start"] and a["end"] <= samples[-1][0]]
        busy = [(a["start"], a["end"]) for a in answers]
        idle = [p for t, p, _ in samples if p is not None and not any(s <= t <= e for s, e in busy)]
        idle_w = statistics.median(idle) if idle else None
        rows = []
        for answer in answers:
            plug_wh, n = integrate(samples, answer["start"], answer["end"], 1)
            gpu_wh, _ = integrate(samples, answer["start"], answer["end"], 2)
            seconds = answer["end"] - answer["start"]
            extra = plug_wh - idle_w * seconds / 3600 if plug_wh is not None and idle_w is not None else None
            rows.append({"ticket": answer["ticket"], "task": answer.get("task", ""), "seconds": round(seconds, 2),
                         "samples": n, "plug_wh": round(plug_wh, 5) if plug_wh is not None else "",
                         "plug_extra_wh": round(extra, 5) if extra is not None else "",
                         "gpu_wh": round(gpu_wh, 5) if gpu_wh is not None else "",
                         "idle_w": round(idle_w, 2) if idle_w is not None else "",
                         "eval_count": answer.get("eval_count") or ""})
        if not rows:
            print(f"{run}: keine Antwort liegt in der Aufzeichnung")
            continue
        folder = run / "energy"
        folder.mkdir(exist_ok=True)
        output = folder / "energy.tsv"
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        write_run(folder, inputs=[power_csv, answers_file, Path(__file__)], outputs=[output], extra={"step": "energy"})
        total = sum(r["plug_wh"] for r in rows if r["plug_wh"] != "")
        print(f"{run.name}: {len(rows)} Antworten, {total:.2f} Wh an der Steckdose, "
              f"{total / len(rows) * 1000:.1f} mWh je Ticket, Leerlauf {idle_w} W")


if __name__ == "__main__":
    main()
