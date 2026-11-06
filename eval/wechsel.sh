#!/bin/bash
# Misst den Wechsel zwischen Decision- und Sprachmodell und ob mehrere Modelle zusammen passen.
# Aufruf im Verzeichnis ~/bench mit dem Namen des Laufs.

NAME=$1
OUT=results/$NAME-wechsel
mkdir -p "$OUT"
ENGINE=bench-engine
IMAGE=docker.io/ollama/ollama:0.40.15
SPRACHE=qwen3.6:35b-a3b
DECISION=d3:9b
EMBEDDING=bge-m3

start() {
    sudo podman rm -f "$ENGINE" >/dev/null 2>&1
    sudo podman run -d --name "$ENGINE" --security-opt label=disable --device /dev/dri --cap-add PERFMON \
        -e OLLAMA_IGPU_ENABLE=1 -e OLLAMA_CONTEXT_LENGTH=32768 -e OLLAMA_KEEP_ALIVE=600 \
        -e OLLAMA_MAX_LOADED_MODELS="$1" -v ollama:/root/.ollama \
        -p 127.0.0.1:11434:11434 "$IMAGE" >/dev/null
    for _ in $(seq 1 60); do curl -fs http://127.0.0.1:11434/api/version >/dev/null && break; sleep 1; done
}

chat() {
    curl -s -o /dev/null -w '%{time_total}' http://127.0.0.1:11434/api/generate \
        -d "{\"model\":\"$SPRACHE\",\"prompt\":\"Sag Hallo.\",\"stream\":false,\"think\":false,\"options\":{\"num_predict\":5}}"
}

entscheiden() {
    curl -s -o /dev/null -w '%{time_total}' http://127.0.0.1:11434/v1/systemone \
        -d "{\"model\":\"$DECISION\",\"state\":\"Die Mikrowelle funkt innen.\",\"questions\":{\"s\":{\"type\":\"noul\",\"instructions\":\"Ist das sicherheitsrelevant?\",\"criteria\":{}}}}"
}

einbetten() {
    curl -s -o /dev/null -w '%{time_total}' http://127.0.0.1:11434/api/embed \
        -d "{\"model\":\"$EMBEDDING\",\"input\":\"Die Mikrowelle funkt innen.\"}"
}

zustand() {
    sudo podman exec "$ENGINE" ollama ps
    cat /sys/class/drm/card*/device/mem_info_vram_used /sys/class/drm/card*/device/mem_info_gtt_used
    awk '/MemAvailable/{print $1, $2}' /proc/meminfo
}

sudo podman stop -t 5 ollama >/dev/null 2>&1

echo "=== $(date +%T) Wechsel nacheinander"
start 1
sudo podman exec "$ENGINE" ollama pull "$EMBEDDING" >/dev/null 2>&1
{
    echo "lauf,chat_s,decision_s"
    for run in 1 2 3 4 5; do
        echo "$run,$(chat),$(entscheiden)"
    done
} >"$OUT/wechsel.csv"

echo "=== $(date +%T) Zusammen geladen"
start 3
{
    echo "chat $(chat)"
    zustand
    echo "decision $(entscheiden)"
    zustand
    echo "embedding $(einbetten)"
    zustand
    echo "chat warm $(chat)"
    echo "decision warm $(entscheiden)"
    echo "embedding warm $(einbetten)"
    zustand
} >"$OUT/zusammen.txt" 2>&1

sudo podman rm -f "$ENGINE" >/dev/null 2>&1
