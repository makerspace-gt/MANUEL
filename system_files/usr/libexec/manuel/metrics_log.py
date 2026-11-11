#!/usr/bin/env python3
"""Logs load, memory, GPU, temperatures and power of the mini PC as one CSV row per call.

A systemd timer runs it once a minute, see manuel-metrics.timer. The rows go to
/var/log/manuel/metrics-YYYY-MM.csv. Power comes from a NOUS A1T plug with Tasmota, whose
address is set in /etc/manuel/metrics.env as NOUS_URL, for example NOUS_URL=http://192.0.2.10.
If the web interface of the plug has a password, NOUS_USER and NOUS_PASSWORD go there as well.
Without NOUS_URL the power columns stay empty. Only the standard library is used.
"""

import csv
import datetime as dt
import glob
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

LOG_DIR = Path(os.environ.get("MANUEL_METRICS_DIR", "/var/log/manuel"))
COLUMNS = [
    "time", "cpu_percent", "load_1m", "mem_used_gib", "mem_available_gib",
    "gpu_busy_percent", "vram_used_gib", "gtt_used_gib", "gpu_power_w",
    "cpu_temp_c", "gpu_temp_c", "nvme_temp_c", "plug_power_w", "plug_total_kwh",
]
GIB = 1024 ** 3


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return ""


def cpu_times():
    fields = [int(x) for x in read("/proc/stat").splitlines()[0].split()[1:]]
    idle = fields[3] + fields[4]
    return idle, sum(fields)


def cpu_percent(interval=1.0):
    idle1, total1 = cpu_times()
    time.sleep(interval)
    idle2, total2 = cpu_times()
    busy = (total2 - total1) - (idle2 - idle1)
    return round(100 * busy / max(total2 - total1, 1), 1)


def memory():
    info = {}
    for line in read("/proc/meminfo").splitlines():
        key, value = line.split(":", 1)
        info[key] = int(value.split()[0]) * 1024
    used = info["MemTotal"] - info["MemAvailable"]
    return round(used / GIB, 2), round(info["MemAvailable"] / GIB, 2)


def gpu():
    """Busy percent, VRAM and GTT in use and power of the first amdgpu card."""
    for device in sorted(glob.glob("/sys/class/drm/card*/device")):
        busy = read(f"{device}/gpu_busy_percent")
        if not busy:
            continue
        vram = read(f"{device}/mem_info_vram_used")
        gtt = read(f"{device}/mem_info_gtt_used")
        power = ""
        for name in ("power1_average", "power1_input"):
            values = [read(p) for p in glob.glob(f"{device}/hwmon/hwmon*/{name}")]
            values = [v for v in values if v]
            if values:
                power = round(int(values[0]) / 1e6, 1)
                break
        return (int(busy), round(int(vram) / GIB, 2) if vram else "",
                round(int(gtt) / GIB, 2) if gtt else "", power)
    return "", "", "", ""


def temperatures():
    """First temperature of k10temp (CPU), amdgpu (GPU) and nvme in degrees Celsius."""
    found = {}
    for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = read(f"{hwmon}/name")
        value = read(f"{hwmon}/temp1_input")
        if name in ("k10temp", "amdgpu", "nvme") and value and name not in found:
            found[name] = round(int(value) / 1000, 1)
    return found.get("k10temp", ""), found.get("amdgpu", ""), found.get("nvme", "")


def plug():
    """Power in watts and total energy in kWh from the Tasmota plug, empty if not reachable."""
    url = os.environ.get("NOUS_URL", "").rstrip("/")
    if not url:
        return "", ""
    query = {"cmnd": "Status 8"}
    if os.environ.get("NOUS_PASSWORD"):
        query["user"] = os.environ.get("NOUS_USER", "admin")
        query["password"] = os.environ["NOUS_PASSWORD"]
    try:
        with urllib.request.urlopen(f"{url}/cm?{urllib.parse.urlencode(query)}", timeout=5) as response:
            energy = json.load(response)["StatusSNS"]["ENERGY"]
        return energy.get("Power", ""), energy.get("Total", "")
    except (OSError, ValueError, KeyError):
        return "", ""


def main():
    now = dt.datetime.now().astimezone()
    row = [now.isoformat(timespec="seconds"), cpu_percent(), read("/proc/loadavg").split()[0],
           *memory(), *gpu(), *temperatures(), *plug()]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"metrics-{now:%Y-%m}.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new:
            writer.writerow(COLUMNS)
        writer.writerow(row)


if __name__ == "__main__":
    main()
