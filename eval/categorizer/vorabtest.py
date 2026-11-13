#!/usr/bin/env python3
"""Pre-test of the Ticket Categorizer of Zammad, see docs/adr/0040-mit-dem-ticket-categorizer-von-zammad-beginnen.adoc.

The script rebuilds the prompt the categorizer sends to Ollama and runs it on the tickets the team
checked. Zammad puts role, instruction, the options as XML and the JSON structure into the system
prompt and the ticket with title and articles into the user prompt. It calls /api/generate without
thinking, with temperature 0 and format json. The texts come from quellen/zammad:

- app/models/ai/agent/type/ticket_categorizer.rb for role, instruction and result structure
- app/services/service/ai/feature/prompts/system/ai_agent.txt.erb for the system prompt
- app/services/service/ai/feature/prompts/user/ai_agent.txt.erb for the user prompt
- lib/ai/provider/ollama.rb for the call

Our tickets have a title and the first message, pseudonymised. Zammad would also send later articles
and the real name of the sender. The options are either catalog entries with the key as value and the
name as label, as a select field shows them, or the groups of the Open Repair Alliance.

Lists:
    a     the A entries of eval/categorizer/abc.tsv
    ab    the A and B entries
    ora   the 46 groups of eval/decision/ora-gruppen.tsv

Every answer counts as correct, same ORA group, empty or wrong, measured against the target of the team.
The results contain real ticket texts and stay local, lauf.json and the summary only hold counts and checksums.

Usage, in the repository root:
    python3 eval/categorizer/vorabtest.py targets --checks ../tickets-kontrolle-d3.xlsx --out soll.tsv
    python3 eval/categorizer/vorabtest.py run --list a --tickets tickets.json --messages nachrichten.json \\
        --targets soll.tsv --out ergebnis-a.jsonl [--model qwen3.6:35b-a3b] [--url http://manuel:11434] [--limit 20]
"""

import argparse
import collections
import csv
import importlib.util
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
from lauf import write_run  # noqa: E402

CATALOG = ROOT / "katalog" / "kategorien.tsv"
ABC = ROOT / "eval" / "categorizer" / "abc.tsv"
ORA_GROUPS = ROOT / "eval" / "decision" / "ora-gruppen.tsv"
FIELD = "art_des_geraets"
LABEL = "Art des Geräts"

# Texts of app/models/ai/agent/type/ticket_categorizer.rb, with the placeholder replaced by FIELD
ROLE = ("You are a ticket categorization specialist who analyzes ticket content and assigns tickets to the most "
        "appropriate category based on the topic, content, and context of the ticket.")
INSTRUCTION = f"""Apply the following principles to identify the correct category:

- Ignore irrelevant information (e.g. personal anecdotes, small talk, signatures, out-of-office notifications).
- Exclude segments that don't contribute any meaningful content (e.g. greetings, farewells).
- Never insert personal opinions about the conversation or elaborate on the answer.
- Never explain your given answer.
- Only use the provided options for categorization, never add new options.
- If the content does not match any of the provided options, always return an empty value.
- Only answer with the value in the "{FIELD}" field inside the JSON structure."""
JSON_HINT = ("Reply with a plain JSON object only. Do not wrap the response in code fences, markdown, or any "
             "additional formatting. Do not include ```json or ``` in the output.")


def backfill():
    spec = importlib.util.spec_from_file_location("backfill", ROOT / "eval" / "restarters" / "backfill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def catalog():
    return {row["key"]: row for row in csv.DictReader(CATALOG.open(encoding="utf-8"), delimiter="\t")}


def options(name):
    """Value and label of every option of a list."""
    if name == "ora":
        lines = [line.split("\t") for line in ORA_GROUPS.read_text(encoding="utf-8").splitlines()
                 if line and not line.startswith("#")]
        return [(group, group) for _, group, *_ in lines]
    classes = {"a": {"A"}, "ab": {"A", "B"}}[name]
    rows = csv.DictReader(ABC.open(encoding="utf-8"), delimiter="\t")
    return [(row["key"], row["name"]) for row in rows if row["class"] in classes]


def system_prompt(items):
    """Like ai_agent.txt.erb for one object attribute, with ERB trim mode."""
    lines = [ROLE, "", INSTRUCTION, "",
             f'The available options from "{LABEL}" are defined inside the XML format:', f"<{FIELD}>"]
    for value, label in items:
        lines += ["  <option>", f"    <value>{value}</value>", f"    <label>{label}</label>", "  </option>"]
    lines += [f"</{FIELD}>", "", JSON_HINT, "", json.dumps({FIELD: "string"}, indent=2)]
    return "\n".join(lines) + "\n"


def user_prompt(title, message):
    """Like the user prompt ai_agent.txt.erb with the title as object attribute and one article."""
    return "\n".join([
        "<ticket>", "  <title>", "    <label>Title</label>", f"    <value>{title}</value>", "  </title>", "",
        "  <article>", "    <sender_type>Customer</sender_type>", "    <sender_name>Gast</sender_name>",
        "    <visibility>public</visibility>", f"    <subject>{title}</subject>", f"    <text>{message}</text>",
        "  </article>", "</ticket>"]) + "\n"


def generate(url, model, system, prompt):
    body = json.dumps({"model": model, "system": system, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": 0.0}, "format": "json"}).encode()
    req = urllib.request.Request(f"{url.rstrip('/')}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as response:
        return json.load(response)


def wilson(hits, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return round(centre - margin, 3), round(centre + margin, 3)


def targets(args):
    """Target catalog key per ticket number from the check sheet of the team."""
    module = backfill()
    index = module.catalog_index()
    written = unknown = 0
    with args.out.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter="\t", lineterminator="\n")
        writer.writerow(["ticket", "key"])
        for row in module.xlsx_rows(args.checks, module.TARGET_COLUMNS, "Kontrolle"):
            if not row.get("Ticket"):
                continue
            target = (row.get("Kategorie richtig") or row.get("Kategorie") or "").strip()
            entry = index.get(target.lower()) if target and target != "??" else None
            if entry is None:
                unknown += 1
                continue
            writer.writerow([row["Ticket"].split(".")[0], entry["key"]])
            written += 1
    print(f"{written} Sollwerte geschrieben, {unknown} ohne Eintrag im Katalog")


def run(args):
    entries = catalog()
    items = options(args.list)
    allowed = {value for value, _ in items}
    system = system_prompt(items)
    tickets = {str(t["id"]): t for t in json.load(args.tickets.open(encoding="utf-8"))}
    messages = json.load(args.messages.open(encoding="utf-8")) if args.messages else {}
    soll = {row["ticket"]: row["key"] for row in csv.DictReader(args.targets.open(encoding="utf-8"), delimiter="\t")}
    done = set()
    if args.out.exists():
        done = {json.loads(line)["ticket"] for line in args.out.open(encoding="utf-8") if line.strip()}
    todo = [number for number in soll if number in tickets and number not in done][: args.limit or None]
    print(f"Liste {args.list} mit {len(items)} Optionen, Prompt {len(system)} Zeichen, {len(todo)} Tickets offen")
    with args.out.open("a", encoding="utf-8") as out:
        for number in todo:
            ticket = tickets[number]
            target = entries[soll[number]]
            message = messages.get(number) or {}
            if isinstance(message, dict):  # nachrichten-pseudonym.json holds betreff, text, kanal and quelle
                message = message.get("text", "")
            start = time.time()
            try:
                answer = generate(args.url, args.model, system, user_prompt(ticket["titel"], message))
                value = json.loads(answer.get("response") or "{}").get(FIELD, "")
            except (OSError, ValueError) as error:
                answer, value = {}, f"FEHLER {error}"
            value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            if args.list == "ora":
                verdict = ("leer" if not value else "richtig" if value == target["ora_group"] else "falsch")
            elif not value:
                verdict = "leer"
            elif value == target["key"]:
                verdict = "richtig"
            elif value in entries and entries[value]["ora_group"] == target["ora_group"]:
                verdict = "gleiche ORA-Gruppe"
            else:
                verdict = "falsch"
            out.write(json.dumps({"ticket": number, "target": target["key"], "target_in_list": (
                target["ora_group"] if args.list == "ora" else target["key"]) in allowed, "value": value,
                "valid": value in allowed, "verdict": verdict, "seconds": round(time.time() - start, 1),
                "prompt_tokens": answer.get("prompt_eval_count")}, ensure_ascii=False) + "\n")
            out.flush()
    summarize(args, len(items))


def summarize(args, options_count):
    rows = [json.loads(line) for line in args.out.open(encoding="utf-8") if line.strip()]
    counts = collections.Counter(row["verdict"] for row in rows)
    n = len(rows)
    filled = n - counts["leer"]
    wrong = counts["falsch"] + counts["gleiche ORA-Gruppe"]
    summary = {
        "list": args.list, "options": options_count, "model": args.model, "tickets": n,
        "counts": dict(counts), "target_in_list": sum(row["target_in_list"] for row in rows),
        "invalid_values": sum(1 for row in rows if row["value"] and not row["valid"]),
        "correct_share": round(counts["richtig"] / n, 3) if n else 0, "correct_wilson": wilson(counts["richtig"], n),
        "wrong_share_of_filled": round(wrong / filled, 3) if filled else 0,
        "wrong_wilson_of_filled": wilson(wrong, filled),
        "median_seconds": sorted(row["seconds"] for row in rows)[n // 2] if n else 0,
    }
    path = args.out.with_suffix(".summary.json")
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_run(args.out, inputs=[p for p in (args.tickets, args.messages, args.targets, ABC, CATALOG) if p],
              outputs=[args.out, path], models=[args.model], ollama_url=args.url, zammad=True,
              extra={"list": args.list, "inference_host": "MANUEL"})
    print(json.dumps(summary, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    t = commands.add_parser("targets")
    t.add_argument("--checks", type=Path, required=True)
    t.add_argument("--out", type=Path, required=True)
    r = commands.add_parser("run")
    r.add_argument("--list", choices=["a", "ab", "ora"], required=True)
    r.add_argument("--tickets", type=Path, required=True)
    r.add_argument("--messages", type=Path)
    r.add_argument("--targets", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--model", default="qwen3.6:35b-a3b")
    r.add_argument("--url", default="http://manuel:11434")
    r.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    (targets if args.command == "targets" else run)(args)


if __name__ == "__main__":
    main()
