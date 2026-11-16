#!/usr/bin/env python3
"""Records the power of MANUEL once a second while a test runs, see
docs/adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc.

The logger of docs/inbetriebnahme.md step 8 writes one line a minute, too coarse for a run of a few
seconds per ticket. This script reads the same sources more often: the power at the NOUS A1T plug with
Tasmota (Status 8) and the power of the GPU from amdgpu (power1_average). It writes the Unix time with
milliseconds, both powers in watts and the energy counter of the plug in kWh as CSV to stdout, until it
is stopped or the duration ends. eval/strom/energy.py joins it with the answers of a run.

It runs on MANUEL and reads NOUS_URL, NOUS_USER and NOUS_PASSWORD from the environment, as in
/etc/manuel/metrics.env, which only root can read. From a computer in the tailnet:
    ssh core@manuel.lan 'sudo sh -c "set -a; . /etc/manuel/metrics.env; set +a; python3 - 7200"' \
        < eval/strom/sample.py > power.csv
The argument is the duration in seconds, default 3600. Only the standard library is used.
"""

import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request


def gpu_watts():
    for path in sorted(glob.glob("/sys/class/drm/card*/device/hwmon/hwmon*/power1_average")):
        try:
            return round(int(open(path).read()) / 1e6, 1)
        except (OSError, ValueError):
            continue
    return ""


def plug(url, query):
    if not url:
        return "", ""
    try:
        with urllib.request.urlopen(f"{url}/cm?{query}", timeout=2) as response:
            energy = json.load(response)["StatusSNS"]["ENERGY"]
        return energy.get("Power", ""), energy.get("Total", "")
    except (OSError, ValueError, KeyError):
        return "", ""


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 3600
    url = os.environ.get("NOUS_URL", "").rstrip("/")
    query = {"cmnd": "Status 8"}
    if os.environ.get("NOUS_PASSWORD"):
        query.update(user=os.environ.get("NOUS_USER", "admin"), password=os.environ["NOUS_PASSWORD"])
    query = urllib.parse.urlencode(query)
    print("time,plug_w,gpu_w,plug_kwh", flush=True)
    end = time.time() + duration
    while time.time() < end:
        started = time.time()
        plug_w, total = plug(url, query)
        print(f"{started:.3f},{plug_w},{gpu_watts()},{total}", flush=True)
        time.sleep(max(0.0, 1.0 - (time.time() - started)))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
