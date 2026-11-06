#!/bin/bash
# Alle Modelle nacheinander an den erfundenen Tickets. Decision-Modelle mit deutschen und
# englischen Anweisungen, weil die Modellkarten kein Deutsch nennen, Sprachmodelle als Vergleich.
# Aufruf im Verzeichnis ~/bench/decision neben tickets.tsv. Das Modell bleibt zwischen den
# Tickets geladen. Der erste Lauf je Modell zählt nicht, er misst nur das Laden.

DECISION="tev1:0.8b d3:2b tev1:4b-q4_K_M d3:4b d3:9b nimble:9b-q4_K_M clef-flash:9b-q8_0 d3:27b clef:27b-q4_K_M"
CHAT="lfm3:1.7b gpt-oss:20b qwen3.6:35b-a3b qwen3.8:27b"
IMAGE=docker.io/ollama/ollama:0.40.15
ENGINE=dec-engine
OUT=results
mkdir -p "$OUT"

sudo podman stop -t 5 ollama >/dev/null 2>&1
sudo podman rm -f "$ENGINE" >/dev/null 2>&1
sudo podman run -d --name "$ENGINE" --security-opt label=disable --device /dev/dri --cap-add PERFMON \
    -e OLLAMA_IGPU_ENABLE=1 -e OLLAMA_KEEP_ALIVE=600 -v ollama:/root/.ollama \
    -p 127.0.0.1:11434:11434 "$IMAGE" >/dev/null
for _ in $(seq 1 60); do curl -fs http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done

peak() {
    local dev max=0 value
    dev=$(dirname "$(ls /sys/class/drm/card*/device/mem_info_gtt_used | head -1)")
    while :; do
        value=$(cat "$dev/mem_info_gtt_used")
        [ "$value" -gt "$max" ] && { max=$value; echo "$max" >"$1"; }
        sleep 2
    done
}

unload() {
    curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$1\",\"keep_alive\":0}" >/dev/null
    sleep 5
}

measure() {
    local kind=$1 model=$2 lang=$3 name=${2//[:\/]/-}-$3
    echo "=== $(date +%T) $kind $model $lang"
    peak "$OUT/$name.gtt" &
    local pid=$!
    python3 decision.py "$OUT/$name.jsonl" "$kind" "$model" "$lang"
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
}

for model in $DECISION; do
    measure decision "$model" de
    measure decision "$model" en
    unload "$model"
done
for model in $CHAT; do
    measure chat "$model" de
    unload "$model"
done

sudo podman rm -f "$ENGINE" >/dev/null 2>&1
sudo podman start ollama >/dev/null 2>&1
echo "### DECISION FERTIG $(date '+%F %T')"
