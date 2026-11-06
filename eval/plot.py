#!/usr/bin/env python3
"""Erzeugt die Grafiken für docs/benchmarks.md aus den Rohdaten in eval/results.

Balken zeigen den Mittelwert, Fehlerbalken die Standardabweichung aller Läufe
einer Variante über alle Durchgänge. Das Skript braucht nur die Standardbibliothek.

Aufruf im Wurzelverzeichnis des Repos:
    python3 eval/plot.py
"""

import csv
import statistics
from collections import defaultdict
from html import escape
from pathlib import Path

RESULTS = Path("eval/results")
OUTPUT = Path("docs/grafiken")

# Reihenfolge und Slot sind fest. Eine Variante behält immer ihre Farbe.
VARIANTS = [
    ("runde1/llamacpp-vulkan", "llama.cpp GPU", 1),
    ("runde1/ollama-vulkan", "Ollama GPU", 2),
    ("runde1-cpu/ollama-cpu", "Ollama CPU", 3),
]
FAIR = [
    ("fair-llamacpp-mtp/llamacpp-vulkan", "llama.cpp MTP", 1),
    ("fair-llamacpp-mtp-ub1024/llamacpp-vulkan", "+ ub1024", 4),
    ("fair-ollama-warm/ollama-vulkan", "Ollama GPU", 2),
    ("fair-ollama-cpu/ollama-cpu", "Ollama CPU", 3),
]
PROMPTS = [512, 4096]

# Ein Modell pro Zeile. Die Tags mit -mtp nutzen dieselbe Datei und entfallen deshalb,
# gemma4 nimmt den Tag mit -mtp, weil llama.cpp nur dort lief.
MODELS = [
    ("lfm3:1.7b", "r2-lfm3-1-7b/ollama-vulkan", "r2-lfm3-1-7b/llamacpp-vulkan"),
    ("qwen3.6:35b-a3b", "r2-qwen3-6-35b-a3b/ollama-vulkan", "r2-qwen3-6-35b-a3b/llamacpp-vulkan"),
    ("gemma4:26b", "r2-gemma4-26b-a4b-it-mtp-q4_K_M/ollama-vulkan",
     "r2-gemma4-26b-a4b-it-mtp-q4_K_M/llamacpp-vulkan"),
    ("nemotron-3-nano:30b-a3b", "r2-nemotron-3-nano-30b-a3b/ollama-vulkan",
     "r2-nemotron-3-nano-30b-a3b/llamacpp-vulkan"),
    ("gpt-oss:20b", "r2-gpt-oss-20b/ollama-vulkan", "r2-gpt-oss-20b/llamacpp-vulkan"),
    ("mimo-v2.6:9b", "r2-mimo-v2-6-9b/ollama-vulkan", "r2-mimo-v2-6-9b/llamacpp-vulkan"),
    ("qwen3.8:27b", "r2-qwen3-8-27b/ollama-vulkan", "r2-qwen3-8-27b/llamacpp-vulkan"),
    ("qwen3.6:27b", "r2-qwen3-6-27b/ollama-vulkan", "r2-qwen3-6-27b/llamacpp-vulkan"),
    ("gemma4:31b", "r2-gemma4-31b/ollama-vulkan", "r2-gemma4-31b/llamacpp-vulkan"),
    ("Unsloth Qwen3.8 UD-Q4_K_XL", None, "r2-unsloth-38-mtp/llamacpp-vulkan"),
    ("mistral-small3.2:24b", "r2-mistral-small3-2-24b/ollama-vulkan", None),
]
MODEL_SERIES = [("Ollama", 2), ("llama.cpp", 1)]

LONG = [
    ("qwen3.6:35b-a3b", "lang-qwen36/llamacpp-vulkan", "lang-qwen36-mtp/llamacpp-vulkan"),
    ("Unsloth Qwen3.8 UD-Q4_K_XL", "lang-unsloth-38/llamacpp-vulkan",
     "lang-unsloth-38-mtp/llamacpp-vulkan"),
]
LONG_SERIES = [("ohne MTP", 0), ("mit MTP", 1)]

STYLE = """
.bg { fill: #fcfcfb; } .primary { fill: #0b0b0b; } .secondary { fill: #52514e; }
.grid { stroke: #e4e3df; } .axis { stroke: #b5b4ae; } .err { stroke: #0b0b0b; }
.s0 { fill: #9a9992; } .s1 { fill: #2a78d6; } .s2 { fill: #eb6834; } .s3 { fill: #1baf7a; }
.s4 { fill: #eda100; }
@media (prefers-color-scheme: dark) {
  .bg { fill: #1a1a19; } .primary { fill: #f0efec; } .secondary { fill: #c3c2b7; }
  .grid { stroke: #3a3a37; } .axis { stroke: #5c5b55; } .err { stroke: #f0efec; }
  .s0 { fill: #75746e; } .s1 { fill: #3987e5; } .s2 { fill: #d95926; } .s3 { fill: #199e70; }
  .s4 { fill: #c98500; }
}
text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
"""


def read_runs(paths):
    """Liefert {(Variante, Prompt): {Messgröße: [Werte]}}."""
    data = defaultdict(lambda: defaultdict(list))
    for path in paths:
        for file in sorted((RESULTS / path).glob("pass*/p*.csv")):
            prompt = int(file.stem[1:])
            rows = defaultdict(list)
            with file.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(line for line in handle if not line.startswith("#")):
                    rows[row["STEP"]].append(row)
            run = data[(path, prompt)]
            run["generate"] += [float(r["TOKEN_PER_SEC"]) for r in rows["generate"]]
            run["prefill"] += [float(r["TOKEN_PER_SEC"]) for r in rows["prefill"]]
            totals = [int(r["NS_PER_COUNT"]) / 1e9 for r in rows["total"]]
            loads = [int(r["NS_PER_COUNT"]) / 1e9 for r in rows["load"]] or [0.0] * len(totals)
            run["answer"] += [total - load for total, load in zip(totals, loads)]
    return data


def nice_max(value):
    """Rundet auf eine glatte Obergrenze der Achse."""
    magnitude = 10 ** (len(str(int(value))) - 1)
    for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if step * magnitude >= value:
            return step * magnitude
    return 10 * magnitude


def intervals(top):
    """Wählt die Einteilung der Achse so, dass nur glatte Werte entstehen."""
    for count in (5, 4, 6):
        step = top / count
        magnitude = 10 ** (len(str(int(step))) - 1)
        if step / magnitude in (1, 2, 2.5, 5):
            return count
    return 4


def number(value, unit_digits):
    return f"{value:.{unit_digits}f}".replace(".", ",")


def bar(x, y, width, base):
    """Balken mit 4 px gerundetem Ende an der Datenseite, an der Grundlinie eckig."""
    radius = min(4, width / 2, base - y)
    return (
        f"M{x:.1f},{base:.1f} V{y + radius:.1f} Q{x:.1f},{y:.1f} {x + radius:.1f},{y:.1f} "
        f"H{x + width - radius:.1f} Q{x + width:.1f},{y:.1f} {x + width:.1f},{y + radius:.1f} "
        f"V{base:.1f} Z"
    )


def summary(values):
    """Mittelwert, Standardabweichung und Anzahl der Läufe."""
    spread = statistics.stdev(values) if len(values) > 1 else 0.0
    return statistics.fmean(values), spread, len(values)


def chart(data, variants, metric, title, unit, digits, filename):
    width, height = 720, 400
    left, right, top, bottom = 64, 24, 96, 48
    plot_w = width - left - right
    plot_h = height - top - bottom
    base = top + plot_h

    stats = {}
    for path, _, _ in variants:
        for prompt in PROMPTS:
            stats[(path, prompt)] = summary(data[(path, prompt)][metric])

    top_value = nice_max(max(mean + spread for mean, spread, _ in stats.values()) * 1.15)
    scale = plot_h / top_value
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
        f"<style>{STYLE}</style>",
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="primary" x="{left}" y="28" font-size="18" font-weight="600">{escape(title)}</text>',
        f'<text class="secondary" x="{left}" y="48" font-size="13">'
        f"Mittelwert mit Standardabweichung, {escape(unit)}</text>",
    ]

    legend_x = left
    for path, label, slot in variants:
        runs = stats[(path, PROMPTS[0])][2]
        text = f"{label} (n={runs})"
        out.append(f'<rect class="s{slot}" x="{legend_x}" y="62" width="12" height="12" rx="2"/>')
        out.append(
            f'<text class="secondary" x="{legend_x + 18}" y="73" font-size="13">{escape(text)}</text>'
        )
        legend_x += 26 + len(text) * 7.2

    count = intervals(top_value)
    for index in range(count + 1):
        value = top_value * index / count
        y = base - value * scale
        css = "axis" if index == 0 else "grid"
        out.append(f'<line class="{css}" x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}"/>')
        label = number(value, 0 if value == int(value) else 1)
        out.append(
            f'<text class="secondary" x="{left - 8}" y="{y + 4:.1f}" font-size="12" '
            f'text-anchor="end">{label}</text>'
        )

    group_w = plot_w / len(PROMPTS)
    bar_w, gap = 72, 2
    total_w = len(variants) * bar_w + (len(variants) - 1) * gap
    for group, prompt in enumerate(PROMPTS):
        start = left + group * group_w + (group_w - total_w) / 2
        for index, (path, label, slot) in enumerate(variants):
            mean, spread, _ = stats[(path, prompt)]
            x = start + index * (bar_w + gap)
            y = base - mean * scale
            center = x + bar_w / 2
            high = base - (mean + spread) * scale
            low = base - max(mean - spread, 0) * scale
            out.append(f"<path class=\"s{slot}\" d=\"{bar(x, y, bar_w, base)}\"/>")
            out.append(
                f'<path class="err" fill="none" stroke-width="1.5" '
                f'd="M{center:.1f},{low:.1f} V{high:.1f} M{center - 6:.1f},{low:.1f} H{center + 6:.1f} '
                f'M{center - 6:.1f},{high:.1f} H{center + 6:.1f}"/>'
            )
            out.append(
                f'<text class="primary" x="{center:.1f}" y="{high - 7:.1f}" font-size="13" '
                f'text-anchor="middle">{number(mean, digits)}</text>'
            )
        out.append(
            f'<text class="secondary" x="{start + total_w / 2:.1f}" y="{base + 24}" font-size="13" '
            f'text-anchor="middle">Prompt mit {prompt} Tokens</text>'
        )

    out.append("</svg>")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / filename).write_text("\n".join(out) + "\n", encoding="utf-8")


def hchart(data, rows, series, prompt, metric, title, unit, digits, filename):
    """Liegende Balken für viele Modelle. rows enthält (Name, Pfad je Reihe)."""
    width = 720
    left, right, top, bottom = 196, 64, 84, 36
    bar_h, gap, row_gap = 13, 2, 12
    row_h = len(series) * bar_h + (len(series) - 1) * gap + row_gap
    height = top + row_h * len(rows) + bottom
    plot_w = width - left - right
    base = height - bottom

    stats = {
        path: summary(data[(path, prompt)][metric]) for _, *paths in rows for path in paths if path
    }
    top_value = nice_max(max(mean + spread for mean, spread, _ in stats.values()) * 1.02)
    scale = plot_w / top_value
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(title)}">',
        f"<title>{escape(title)}</title>",
        f"<style>{STYLE}</style>",
        f'<rect class="bg" width="{width}" height="{height}"/>',
        f'<text class="primary" x="16" y="28" font-size="18" font-weight="600">{escape(title)}</text>',
        f'<text class="secondary" x="16" y="48" font-size="13">'
        f"Mittelwert mit Standardabweichung, {escape(unit)}</text>",
    ]

    legend_x = 16
    for label, slot in series:
        out.append(f'<rect class="s{slot}" x="{legend_x}" y="58" width="12" height="12" rx="2"/>')
        out.append(
            f'<text class="secondary" x="{legend_x + 18}" y="69" font-size="13">{escape(label)}</text>'
        )
        legend_x += 34 + len(label) * 7.2

    count = intervals(top_value)
    for index in range(count + 1):
        value = top_value * index / count
        x = left + value * scale
        css = "axis" if index == 0 else "grid"
        out.append(f'<line class="{css}" x1="{x:.1f}" x2="{x:.1f}" y1="{top - 6}" y2="{base}"/>')
        label = number(value, 0 if value == int(value) else 1)
        out.append(
            f'<text class="secondary" x="{x:.1f}" y="{base + 18}" font-size="12" '
            f'text-anchor="middle">{label}</text>'
        )

    for index, (name, *paths) in enumerate(rows):
        y0 = top + index * row_h
        out.append(
            f'<text class="primary" x="{left - 10}" y="{y0 + (row_h - row_gap) / 2 + 4:.1f}" '
            f'font-size="12" text-anchor="end">{escape(name)}</text>'
        )
        for position, (path, (_, slot)) in enumerate(zip(paths, series)):
            if not path:
                continue
            mean, spread, _ = stats[path]
            y = y0 + position * (bar_h + gap)
            x1 = left + mean * scale
            high = left + (mean + spread) * scale
            low = left + max(mean - spread, 0) * scale
            center = y + bar_h / 2
            radius = min(4, bar_h / 2, x1 - left)
            out.append(
                f'<path class="s{slot}" d="M{left},{y:.1f} H{x1 - radius:.1f} '
                f'Q{x1:.1f},{y:.1f} {x1:.1f},{y + radius:.1f} V{y + bar_h - radius:.1f} '
                f'Q{x1:.1f},{y + bar_h:.1f} {x1 - radius:.1f},{y + bar_h:.1f} H{left} Z"/>'
            )
            out.append(
                f'<path class="err" fill="none" stroke-width="1.5" '
                f'd="M{low:.1f},{center:.1f} H{high:.1f} M{low:.1f},{center - 4:.1f} V{center + 4:.1f} '
                f'M{high:.1f},{center - 4:.1f} V{center + 4:.1f}"/>'
            )
            out.append(
                f'<text class="primary" x="{high + 7:.1f}" y="{center + 4:.1f}" font-size="12">'
                f"{number(mean, digits)}</text>"
            )

    out.append("</svg>")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / filename).write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    paths = [path for path, _, _ in VARIANTS + FAIR]
    paths += [path for _, *row in MODELS + LONG for path in row if path]
    data = read_runs(paths)

    name = "qwen3.6:35b-a3b"
    chart(data, VARIANTS, "generate", f"Generierung mit {name}", "Token pro Sekunde", 1,
          "runde1-generierung.svg")
    chart(data, VARIANTS, "prefill", f"Prompt-Verarbeitung mit {name}", "Token pro Sekunde", 0,
          "runde1-prompt.svg")
    chart(data, VARIANTS, "answer", f"Antwortzeit ohne Laden mit {name}",
          "Sekunden, weniger ist besser", 1, "runde1-antwortzeit.svg")

    chart(data, FAIR, "generate", "Generierung mit gleichen Flags", "Token pro Sekunde", 1,
          "fair-generierung.svg")
    chart(data, FAIR, "prefill", "Prompt-Verarbeitung mit gleichen Flags", "Token pro Sekunde", 0,
          "fair-prompt.svg")
    chart(data, FAIR, "answer", "Antwortzeit ohne Laden mit gleichen Flags",
          "Sekunden, weniger ist besser", 1, "fair-antwortzeit.svg")

    hchart(data, MODELS, MODEL_SERIES, 4096, "generate", "Generierung pro Modell",
           "Token pro Sekunde bei 4096 Tokens Prompt", 1, "modelle-generierung.svg")
    hchart(data, MODELS, MODEL_SERIES, 4096, "prefill", "Prompt-Verarbeitung pro Modell",
           "Token pro Sekunde bei 4096 Tokens Prompt", 0, "modelle-prompt.svg")
    hchart(data, MODELS, MODEL_SERIES, 4096, "answer", "Antwortzeit pro Modell",
           "Sekunden bei 4096 Tokens Prompt, weniger ist besser", 1,
           "modelle-antwortzeit.svg")
    hchart(data, LONG, LONG_SERIES, 512, "answer", "Lange Antworten mit und ohne MTP",
           "Sekunden für 800 Tokens Antwort, weniger ist besser", 1, "mtp-lange-antworten.svg")


if __name__ == "__main__":
    main()
