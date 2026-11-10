#!/usr/bin/env python3
"""Let Hermes prepare the Restarters.net device data from the first message of each guest.

Runs on MANUEL as user core. Each message goes to Hermes on its own, with the skill
repaircafe-restarters and without the ticket title. The script checks the answer and
collects everything in one JSON file. It sends nothing to Restarters.net.

    python3 erfassen.py nachrichten.json ergebnis.json            # all open messages
    python3 erfassen.py nachrichten.json ergebnis.json --limit 10
    python3 erfassen.py nachrichten.json ergebnis.json --nur 100001 100002
    python3 erfassen.py nachrichten.json ergebnis.json --klaeren   # answer open questions

Already finished tickets are skipped, so a run can be stopped and continued.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

IMAGE = "docker.io/nousresearch/hermes-agent:latest"
CONTAINER = "hermes-rc"
SKILL = "repaircafe-restarters"
HOME = pathlib.Path.home()
WORK = HOME / "repaircafe" / "anfragen"

# Categories of Restarters.net, see quellen/restarters/kategorien.csv
CATEGORIES = {
    6: ("Games console", True), 7: ("Watch/clock", True), 8: ("Sewing machine", True), 9: ("Iron", True),
    10: ("Coffee maker", True), 11: ("Desktop computer", True), 12: ('Flat screen 15-17"', True),
    13: ('Flat screen 19-20"', True), 14: ('Flat screen 22-24"', True), 15: ("Laptop large", True),
    16: ("Laptop medium", True), 17: ("Laptop small", True), 18: ("Paper shredder", True),
    19: ("PC accessory", True), 20: ("Printer/scanner", True), 21: ("Digital compact camera", True),
    22: ("DSLR/video camera", True), 23: ("Handheld entertainment device", True), 24: ("Headphones", True),
    25: ("Mobile", True), 26: ("Tablet", True), 27: ('Flat screen 26-30"', True), 28: ('Flat screen 32-37"', True),
    29: ("Hi-Fi integrated", True), 30: ("Hi-Fi separates", True), 31: ("Musical instrument", True),
    32: ("Portable radio", True), 33: ("Projector", True), 34: ("TV and gaming-related accessories", True),
    35: ("Aircon/dehumidifier", True), 36: ("Decorative or safety lights", True), 37: ("Fan", True),
    38: ("Hair & beauty item", True), 39: ("Kettle", True), 40: ("Lamp", True), 41: ("Power tool", True),
    42: ("Small kitchen item", True), 43: ("Toaster", True), 44: ("Toy", True), 45: ("Vacuum", True),
    46: ("Misc", True), 47: ("Furniture", False), 48: ("Bicycle", False), 49: ("Clothing/textile", False),
    50: ("Misc", False), 51: ("Hand tool", False), 52: ("Jewellery", False),
}
STATUS = {"fertig", "rueckfrage", "kein_geraet"}
CONFIDENCE = {"hoch", "mittel", "niedrig"}


def podman(*args, check=True, **kwargs):
    return subprocess.run(["podman", *args], check=check, text=True, **kwargs)


def ensure_container():
    """One long-running container, so each message saves the start of a new one."""
    state = podman("container", "inspect", "-f", "{{.State.Running}}", CONTAINER,
                   check=False, capture_output=True)
    if state.returncode == 0 and state.stdout.strip() == "true":
        return
    podman("rm", "-f", CONTAINER, check=False, capture_output=True)
    podman("run", "-d", "--name", CONTAINER, "--network", "host",
           "-v", f"{HOME}/.hermes:/opt/data:Z", "-v", f"{WORK}:/anfragen:ro,z",
           IMAGE, "sleep", "infinity", capture_output=True)
    time.sleep(15)  # first start syncs the bundled skills


def ask_hermes(query, session=None, reasoning="low"):
    """Run one turn and return (final text, session id)."""
    with tempfile.NamedTemporaryFile("w", dir=WORK, suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(query)
    os.chmod(f.name, 0o644)
    try:
        cmd = ["exec", CONTAINER, "/opt/hermes/bin/hermes", "chat", "--query-file",
               f"/anfragen/{pathlib.Path(f.name).name}", "-Q", "-s", SKILL, "-t", "clarify",
               "--reasoning", reasoning]
        if session:
            cmd += ["--resume", session]
        out = podman(*cmd, check=False, capture_output=True, timeout=3600).stdout
    finally:
        os.unlink(f.name)
    match = re.search(r"^session_id:\s*(\S+)", out, re.M)
    text = out[:match.start()] if match else out
    lines = [ln for ln in text.splitlines() if not re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ (WARNING|INFO)", ln)]
    return "\n".join(lines).strip(), match.group(1) if match else None


def parse_answer(text):
    """Take the JSON object from the answer, tolerating a Markdown fence."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("keine JSON-Antwort")
    return json.loads(text[start:end + 1])


def check(answer, ticket):
    """Validate and complete the answer. Returns the entry and a list of problems."""
    problems = []
    status = answer.get("status")
    if status not in STATUS:
        problems.append(f"unbekannter Status {status!r}")
    devices = []
    for d in answer.get("devices") or []:
        try:
            cat = int(d.get("category"))
        except (TypeError, ValueError):
            cat = None
        if cat not in CATEGORIES:
            problems.append(f"unbekannte Kategorie {d.get('category')!r}")
        if not (d.get("item_type") or "").strip():
            problems.append("item_type fehlt")
        age = d.get("age")
        if age is not None and not isinstance(age, (int, float)):
            problems.append(f"Alter ist keine Zahl: {age!r}")
            age = None
        name, powered = CATEGORIES.get(cat, (None, None))
        devices.append({
            # fields of the device in the API of Restarters.net, repair_status, spare_parts,
            # barrier and eventid follow after the repair
            "restarters": {
                "category": cat, "item_type": (d.get("item_type") or "").strip() or None,
                "brand": d.get("brand") or None, "model": d.get("model") or None, "age": age,
                "problem": d.get("problem") or None, "notes": None, "repair_status": None,
                "spare_parts": None, "barrier": None, "eventid": None,
            },
            "category_name": name, "powered": powered,
            "confidence": d.get("confidence") if d.get("confidence") in CONFIDENCE else None,
        })
    if status in ("fertig", "rueckfrage") and not devices:
        problems.append("Status ohne Gerät")
    if status == "kein_geraet" and devices:
        problems.append("kein_geraet, aber Geräte angegeben")
    questions = [q for q in answer.get("rueckfragen") or [] if isinstance(q, str) and q.strip()]
    if status == "rueckfrage" and not questions:
        problems.append("Rückfrage ohne Frage")
    if str(answer.get("ticket")) != ticket:
        problems.append(f"falsche Ticketnummer {answer.get('ticket')!r}")
    if problems or any(d["confidence"] != "hoch" for d in devices):
        if status == "fertig":
            status = "rueckfrage"
    return {"status": status, "devices": devices, "rueckfragen": questions,
            "begruendung": answer.get("begruendung")}, problems


def message_query(ticket, message):
    # Without the title of the team, see SKILL.md
    data = {"ticket": ticket, "quelle": message.get("quelle"), "kanal": message.get("kanal"),
            "betreff": message.get("betreff"), "text": message.get("text")}
    return ("Nutze den Skill repaircafe-restarters für diese eine Nachricht.\n\nNachricht:\n"
            + json.dumps(data, ensure_ascii=False, indent=1))


def process(ticket, query, session, reasoning, previous=None):
    started = time.time()
    text, new_session = ask_hermes(query, session, reasoning)
    entry = {"session": new_session or session, "dauer_s": round(time.time() - started, 1),
             "zeit": datetime.datetime.now().isoformat(timespec="seconds")}
    try:
        checked, problems = check(parse_answer(text), ticket)
        entry.update(checked)
        entry["probleme"] = problems
    except (ValueError, json.JSONDecodeError) as exc:
        entry.update({"status": "fehler", "devices": [], "rueckfragen": [], "probleme": [str(exc)],
                      "antwort_roh": text[-2000:]})
    if previous:
        entry["antworten"] = previous.get("antworten", [])
    return entry


def save(result, path):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def read_answer():
    print("Antwort eingeben, leere Zeile beendet. Nur Enter überspringt, q beendet.")
    lines = []
    while True:
        line = input("> ")
        if not line:
            return "\n".join(lines)
        if line == "q" and not lines:
            return None
        lines.append(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("nachrichten", type=pathlib.Path)
    ap.add_argument("ergebnis", type=pathlib.Path)
    ap.add_argument("--nur", nargs="+", metavar="TICKET")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--neu", action="store_true", help="auch fertige Tickets neu bearbeiten")
    ap.add_argument("--klaeren", action="store_true", help="offene Rückfragen beantworten")
    ap.add_argument("--reasoning", default="low", help="none, low, medium oder high, Standard low")
    args = ap.parse_args()

    messages = json.loads(args.nachrichten.read_text(encoding="utf-8"))
    result = (json.loads(args.ergebnis.read_text(encoding="utf-8")) if args.ergebnis.exists()
              else {"hinweis": "Vorschau, nichts ist an Restarters.net gesendet", "tickets": {}})
    tickets = result["tickets"]
    WORK.mkdir(parents=True, exist_ok=True)
    WORK.chmod(0o755)
    WORK.parent.chmod(0o700)
    ensure_container()

    if args.klaeren:
        todo = [t for t in (args.nur or tickets) if tickets.get(t, {}).get("status") in ("rueckfrage", "fehler")]
        for n, ticket in enumerate(todo, 1):
            entry, message = tickets[ticket], messages[ticket]
            print(f"\n=== {n}/{len(todo)} Ticket {ticket} ({message.get('kanal')}) ===")
            print(f"Betreff: {message.get('betreff')}\n{message.get('text')}\n")
            for d in entry["devices"]:
                r = d["restarters"]
                print(f"Vorschlag: {r['category']} {d['category_name']} | {r['item_type']} | {r['brand']} | "
                      f"{r['model']} | Alter {r['age']} | {r['problem']} | {d['confidence']}")
            for q in entry["rueckfragen"] + entry.get("probleme", []):
                print(f"? {q}")
            answer = read_answer()
            if answer is None:
                break
            if not answer:
                continue
            entry.setdefault("antworten", []).append(answer)
            if entry.get("session") and entry["status"] != "fehler":
                query, session = "Antwort des Teams auf deine Rückfragen:\n" + answer, entry["session"]
            else:
                query, session = message_query(ticket, message) + "\n\nHinweis des Teams:\n" + answer, None
            tickets[ticket] = process(ticket, query, session, args.reasoning, entry)
            new = tickets[ticket]
            print(f"-> {new['status']}: " + "; ".join(
                f"{d['restarters']['category']} {d['category_name']} {d['restarters']['item_type']}" for d in new["devices"]))
            for q in new["rueckfragen"] + new.get("probleme", []):
                print(f"? {q}")
            save(result, args.ergebnis)
        return

    todo = [t for t in (args.nur or messages) if t in messages and (args.neu or args.nur or t not in tickets)]
    if args.limit:
        todo = todo[:args.limit]
    for n, ticket in enumerate(todo, 1):
        tickets[ticket] = process(ticket, message_query(ticket, messages[ticket]), None, args.reasoning)
        e = tickets[ticket]
        print(f"{n}/{len(todo)} {ticket} {e['status']} {e['dauer_s']} s " + "; ".join(
            f"{d['restarters']['category']} {d['restarters']['item_type']}" for d in e["devices"]), flush=True)
        save(result, args.ergebnis)
    counts = {}
    for e in tickets.values():
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    print("Stand:", counts)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
