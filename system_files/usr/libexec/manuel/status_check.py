#!/usr/bin/env python3
"""Checks whether the admins of MANUEL need to act and tells them.

A systemd timer runs it after boot and once a day, see manuel-status.timer. It checks
  - firmware updates offered by fwupd,
  - an image update that is staged and waits for a reboot,
  - the container "ollama" is running,
  - the metrics logger wrote within the last hour.

Every finding goes to the journal and to /run/motd.d/60-manuel.motd, which is shown at login.
If /etc/manuel/notify.env sets SMTP_HOST, SMTP_FROM and NOTIFY_TO, an e-mail goes out as well,
but only when the findings changed since the last run. The channel is still open, see
docs/adr/0044-admins-ueber-wartung-informieren.adoc. Only the standard library is used.

    python3 status_check.py [--dry-run]
"""

import argparse
import hashlib
import json
import os
import smtplib
import subprocess
import time
from email.message import EmailMessage
from pathlib import Path

STATE = Path(os.environ.get("MANUEL_STATE_DIR", "/var/lib/manuel")) / "status.sha256"
MOTD = Path(os.environ.get("MANUEL_MOTD", "/run/motd.d/60-manuel.motd"))
METRICS_DIR = Path(os.environ.get("MANUEL_METRICS_DIR", "/var/log/manuel"))


def run(*command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        return result.returncode, result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def firmware():
    code, out = run("fwupdmgr", "get-upgrades", "--json", "--no-unreported-check")
    if code is None or not out.strip().startswith("{"):
        return []
    findings = []
    for device in json.loads(out).get("Devices", []):
        releases = device.get("Releases") or []
        if releases:
            findings.append(f"Firmware-Update für {device.get('Name', 'unbekanntes Gerät')}: "
                            f"{device.get('Version', '?')} auf {releases[0].get('Version', '?')}")
    return findings


def staged_image():
    code, out = run("rpm-ostree", "status", "--json")
    if code != 0:
        return []
    for deployment in json.loads(out).get("deployments", []):
        if deployment.get("staged"):
            stamp = time.strftime("%d.%m.%Y", time.localtime(deployment.get("timestamp", 0)))
            return [f"Ein neues Image vom {stamp} wartet auf einen Neustart."]
    return []


def ollama():
    code, out = run("podman", "inspect", "-f", "{{.State.Running}}", "ollama")
    if code != 0:
        return ["Den Container ollama gibt es nicht."]
    return [] if out.strip() == "true" else ["Der Container ollama läuft nicht."]


def metrics():
    files = sorted(METRICS_DIR.glob("metrics-*.csv"), key=lambda p: p.stat().st_mtime)
    if not files:
        return []
    age = time.time() - files[-1].stat().st_mtime
    return [] if age < 3600 else [f"Der Logger hat seit {int(age // 3600)} Stunden nichts geschrieben."]


def notify(findings):
    host, sender, recipients = (os.environ.get(k, "") for k in ("SMTP_HOST", "SMTP_FROM", "NOTIFY_TO"))
    if not (host and sender and recipients):
        return "kein Kanal eingerichtet"
    message = EmailMessage()
    message["Subject"] = "MANUEL braucht Aufmerksamkeit" if findings else "MANUEL ist wieder in Ordnung"
    message["From"] = sender
    message["To"] = recipients
    message.set_content("\n".join(f"- {f}" for f in findings) or "Keine offenen Punkte mehr.")
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=30) as smtp:
        smtp.starttls()
        if os.environ.get("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(message)
    return "E-Mail verschickt"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="nur ausgeben, nichts schreiben oder senden")
    args = parser.parse_args()

    findings = firmware() + staged_image() + ollama() + metrics()
    for finding in findings:
        print(finding)
    if not findings:
        print("Keine offenen Punkte.")
    if args.dry_run:
        return

    MOTD.parent.mkdir(parents=True, exist_ok=True)
    MOTD.write_text("".join(f"MANUEL: {f}\n" for f in findings), encoding="utf-8")

    digest = hashlib.sha256("\n".join(findings).encode()).hexdigest()
    previous = STATE.read_text().strip() if STATE.exists() else ""
    if digest != previous:
        print(f"Meldung: {notify(findings)}")
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(digest)


if __name__ == "__main__":
    main()
