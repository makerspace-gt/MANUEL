#!/usr/bin/env python3
"""Writes lauf.json next to the output of a run, see docs/adr/0027-laeufe-reproduzierbar-festhalten.adoc.

The file names date, command and commit of the repo, path and SHA-256 of every input and output,
name and digest of every model in Ollama, the versions of Ollama and llama.cpp, kernel and memory of
the machine and, for prompts rebuilt from Zammad, the commit of quellen/zammad. Checksums say
nothing about the content, so the file may be public even if the inputs are real tickets.

Use it from a script:

    from lauf import write_run
    write_run("results/vorabtest", inputs=[tickets], outputs=[result], models=["qwen3.6:35b-a3b"],
              ollama_url="http://manuel:11434", zammad=True, extra={"liste": "a"})

Only the standard library is used.
"""

import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args, cwd=ROOT):
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def ollama(url, path):
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}{path}", timeout=20) as response:
            return json.load(response)
    except OSError:
        return {}


def memory():
    """Total memory of this machine and, for an AMD GPU, the reserved VRAM and the GTT limit in GiB."""
    info = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                info["mem_total_gib"] = round(int(line.split()[1]) / 2**20, 1)
    except OSError:
        pass
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]/device")):
        for name, key in (("mem_info_vram_total", "vram_gib"), ("mem_info_gtt_total", "gtt_gib")):
            try:
                info[key] = round(int((card / name).read_text()) / 2**30, 1)
            except (OSError, ValueError):
                pass
    return info


def write_run(target, inputs=(), outputs=(), models=(), ollama_url=None, llama_cpp_version=None,
              llama_cpp_args=None, gguf_files=(), zammad=False, extra=None):
    """Write lauf.json into target, a directory, or next to target if it is a file. Returns the path."""
    target = Path(target)
    folder = target if target.is_dir() else target.parent
    tags = {m["name"]: m["digest"] for m in ollama(ollama_url, "/api/tags").get("models", [])} if ollama_url else {}
    run = {
        "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "command": " ".join([Path(sys.argv[0]).name] + sys.argv[1:]),
        "commit": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "inputs": [{"path": str(p), "sha256": sha256(p)} for p in map(Path, inputs)],
        "outputs": [{"path": str(p), "sha256": sha256(p)} for p in map(Path, outputs) if p.exists()],
        "models": [{"name": m, "digest": tags.get(m, tags.get(f"{m}:latest", ""))} for m in models],
        "ollama": {"url": ollama_url, "version": ollama(ollama_url, "/api/version").get("version")} if ollama_url else None,
        "llama_cpp": {"version": llama_cpp_version, "args": llama_cpp_args,
                      "gguf": [{"path": str(p), "sha256": sha256(p)} for p in map(Path, gguf_files)]}
        if llama_cpp_version or gguf_files else None,
        "host": {"name": platform.node(), "kernel": platform.release(), **memory()},
        "zammad_commit": git("rev-parse", "HEAD", cwd=ROOT / "quellen" / "zammad") if zammad else None,
        **(extra or {}),
    }
    path = folder / "lauf.json"
    path.write_text(json.dumps({k: v for k, v in run.items() if v is not None}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


if __name__ == "__main__":
    sys.exit(__doc__)
