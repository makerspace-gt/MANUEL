#!/usr/bin/env python3
"""Rates the solution approaches of a run against what volunteers found at the appointment, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

A fixed judge model gets the approach and the old field hack, the cause and repair the volunteers wrote
down, and answers yes, partly, no or unclear after prompts/judge.*. Tickets without hack are skipped.
The same judge rates every model, so the verdicts compare. A sample is checked by hand, see sample.py.
The verdicts go to judge/answers.jsonl in the folder of the run and stay local, they quote tickets.

Run in the repository root, Ollama from OLLAMA_URL (default http://manuel:11434):
    python3 -I eval/enrich/judge.py EXPORT_DIR RUN_DIR [RUN_DIR ...] [--judge qwen3.6:35b-a3b-64k]
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import tickets as source  # noqa: E402
from enrich import URL, chat  # noqa: E402
from lauf import write_run  # noqa: E402

VERDICTS = {"yes", "partly", "no", "unclear"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export", type=Path)
    parser.add_argument("runs", type=Path, nargs="+")
    parser.add_argument("--judge", default="qwen3.6:35b-a3b-64k")
    args = parser.parse_args()

    tickets_file, tickets = source.load(args.export)
    by_id = {t["id"]: t for t in tickets}
    role = (HERE / "prompts/judge.role.md").read_text(encoding="utf-8").strip()
    instruction = (HERE / "prompts/judge.instruction.md").read_text(encoding="utf-8").strip()
    system = source.zammad_system_prompt(role, instruction, {"verdict": "yes|partly|no|unclear", "reason": "string"})

    for run in (r.expanduser() for r in args.runs):
        answers_file = run / "answers.jsonl"
        folder = run / "judge"
        folder.mkdir(exist_ok=True)
        output = folder / "answers.jsonl"
        done = set()
        if output.exists():
            done = {json.loads(line)["ticket"] for line in output.read_text(encoding="utf-8").splitlines() if line.strip()}
        with output.open("a", encoding="utf-8") as handle:
            for line in answers_file.read_text(encoding="utf-8").splitlines():
                answer = json.loads(line)
                ticket = by_id.get(answer["ticket"])
                note = (answer.get("fields") or {}).get("note") or ""
                found = source.human(ticket, "hack") if ticket else None
                if answer["ticket"] in done or not note or not found:
                    continue
                user = (f"<approach>\n{source.plain({'body': note, 'content_type': 'text/html'})}\n</approach>\n\n"
                        f"<appointment>\n{found}\n</appointment>\n")
                try:
                    fields, _ = chat(args.judge, system, user, False)
                    verdict = str(fields.get("verdict", "")).strip().lower()
                    error = None if verdict in VERDICTS else f"verdict {verdict!r}"
                except (OSError, ValueError, KeyError) as exc:
                    fields, verdict, error = {}, "", f"{type(exc).__name__}: {exc}"[:300]
                handle.write(json.dumps({"ticket": answer["ticket"], "verdict": verdict, "reason": fields.get("reason", ""),
                                         "error": error}, ensure_ascii=False) + "\n")
                handle.flush()
        write_run(folder, inputs=[tickets_file, answers_file, HERE / "prompts/judge.role.md", HERE / "prompts/judge.instruction.md"],
                  outputs=[output], models=[args.judge], ollama_url=URL, extra={"step": "judge"})
        print(f"{run.parent.name}/{run.name}: Urteile in {output}")


if __name__ == "__main__":
    main()
