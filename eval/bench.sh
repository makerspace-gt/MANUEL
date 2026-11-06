#!/bin/bash
# Benchmark der Engines auf dem Mini-PC. Alle Engines laufen im Container,
# das Betriebssystem bleibt unverändert. Ablauf siehe docs/inbetriebnahme.md.
#
# Aufruf im Verzeichnis ~/bench neben ollama-bench:
#   ./bench.sh <Lauf> <Variante> [<Variante> ...]
#
# Varianten: llamacpp-vulkan ollama-vulkan ollama-cpu
#
# Einstellbar über die Umgebung:
#   MODEL=qwen3.6:35b-a3b EPOCHS=10 WARMUP=2 PROMPTS="512 4096" PASSES=2
#   GGUF=/pfad/modell.gguf   eigene Datei für llama.cpp statt der Datei von Ollama
#   LLAMA_ARGS="..."         zusätzliche Flags für llama-server, zum Beispiel für MTP
#   KEEP=600                 Sekunden, die Ollama das Modell geladen hält, 0 lädt es pro Anfrage neu.
#                            Das gilt nur für den Server. Das Flag -k von ollama-bench bleibt ungenutzt,
#                            weil es nach jedem Lauf so lange wartet, bis das Modell entladen ist.
#   IMG_OLLAMA=...           anderes Image für Ollama, zum Beispiel für Modelle, die eine neuere Version brauchen
#   MAXT=200                 höchstens erzeugte Tokens
#   WAIT=300                 Sekunden, die eine Engine zum Starten hat

set -u

RUN=$1
shift
VARIANTS=("$@")

MODEL=${MODEL:-qwen3.6:35b-a3b}
EPOCHS=${EPOCHS:-10}
WARMUP=${WARMUP:-2}
PROMPTS=${PROMPTS:-512 4096}
PASSES=${PASSES:-2}
GGUF=${GGUF:-}
LLAMA_ARGS=${LLAMA_ARGS:-}
KEEP=${KEEP:-0}
MAXT=${MAXT:-200}
WAIT=${WAIT:-300}
CTX=32768
ENGINE=bench-engine
VOLUME=ollama

IMG_OLLAMA=${IMG_OLLAMA:-docker.io/ollama/ollama:latest}
IMG_LLAMA_VULKAN=${IMG_LLAMA_VULKAN:-ghcr.io/ggml-org/llama.cpp:server-vulkan}

OUT=results/$RUN
mkdir -p "$OUT"

# Pfad der GGUF-Datei im Volume von Ollama, damit beide Engines dieselbe Datei nutzen
model_blob() {
    local name=${MODEL%%:*} tag=${MODEL##*:} root digest
    root=$(sudo podman volume inspect "$VOLUME" --format '{{.Mountpoint}}')
    digest=$(sudo jq -r '.layers[] | select(.mediaType == "application/vnd.ollama.image.model") | .digest' \
        "$root/models/manifests/registry.ollama.ai/library/$name/$tag")
    echo "${digest/:/-}"
}

stop_engine() {
    sudo podman rm -f -t 5 "$ENGINE" >/dev/null 2>&1
}

start_ollama() {
    local image=$1
    shift
    sudo podman run -d --name "$ENGINE" --security-opt label=disable \
        -e OLLAMA_CONTEXT_LENGTH=$CTX -e OLLAMA_KEEP_ALIVE=$KEEP \
        -v "$VOLUME:/root/.ollama" -p 127.0.0.1:11434:11434 "$@" "$image" >/dev/null
}

# MTP-Flags aus dem Ollama-Lauf desselben Modells. Manche Modelle brauchen eine eigene
# Draft-Datei und andere Werte, zum Beispiel Gemma 4 mit --spec-draft-model.
ollama_spec() {
    local log=$OUT/ollama-vulkan/pass1/engine.log
    [ -f "$log" ] || return 0
    grep -m1 -o 'cmd="[^"]*"' "$log" | tr -d '"' | tr ' ' '\n' |
        awk '/^--/{on=($0 ~ /^--spec-/)} on' | sed 's|^/root/.ollama/models/blobs/|/models/|' | tr '\n' ' '
}

start_llamacpp() {
    local image=$1
    shift
    local dir file spec args=$LLAMA_ARGS
    spec=$(ollama_spec)
    [ -n "$spec" ] && [ -z "$GGUF" ] && args="${args%%--spec-type*} $spec"
    if [ -n "$GGUF" ]; then
        dir=$(dirname "$(realpath "$GGUF")")
        file=$(basename "$GGUF")
    else
        dir=$(sudo podman volume inspect "$VOLUME" --format '{{.Mountpoint}}')/models/blobs
        file=$(model_blob)
    fi
    # shellcheck disable=SC2086
    sudo podman run -d --name "$ENGINE" --security-opt label=disable \
        -v "$dir:/models:ro" -p 127.0.0.1:8080:8080 "$@" "$image" \
        -m "/models/$file" -ngl 99 -c $CTX --parallel 1 \
        --host 0.0.0.0 --port 8080 $args >/dev/null
}

start_engine() {
    case $1 in
    ollama-vulkan)
        start_ollama "$IMG_OLLAMA" --device /dev/dri --cap-add PERFMON -e OLLAMA_IGPU_ENABLE=1
        ;;
    ollama-cpu)
        start_ollama "$IMG_OLLAMA" -e OLLAMA_VULKAN=0
        ;;
    llamacpp-vulkan)
        start_llamacpp "$IMG_LLAMA_VULKAN" --device /dev/dri
        ;;
    *)
        echo "Unbekannte Variante $1" >&2
        return 1
        ;;
    esac
}

wait_ready() {
    local url=$1 i
    for i in $(seq 1 "$WAIT"); do
        curl -fsS --max-time 2 "$url" >/dev/null 2>&1 && return 0
        sudo podman container exists "$ENGINE" || return 1
        [ "$(sudo podman inspect "$ENGINE" --format '{{.State.Running}}')" = true ] || return 1
        sleep 1
    done
    return 1
}

system_info() {
    uname -r
    rpm-ostree status --booted | sed -n 3,5p
    sudo podman inspect "$ENGINE" --format 'image {{.ImageName}} {{.ImageDigest}}'
    cat /sys/class/drm/card*/device/mem_info_vram_total /sys/class/drm/card*/device/mem_info_gtt_total
    cat /sys/module/ttm/parameters/pages_limit
}

# Schreibt alle 2 Sekunden GPU-Last, GPU-Speicher, Temperatur, Taktdaten und freien Arbeitsspeicher mit
sampler() {
    local dev
    dev=$(dirname "$(ls /sys/class/drm/card*/device/gpu_busy_percent | head -1)")
    echo "time,gpu_busy,vram_used,gtt_used,temp_mc,cpu_khz,mem_available_kb" >"$1"
    while :; do
        printf '%s,%s,%s,%s,%s,%s,%s\n' "$(date +%s)" \
            "$(cat "$dev/gpu_busy_percent")" "$(cat "$dev/mem_info_vram_used")" \
            "$(cat "$dev/mem_info_gtt_used")" "$(cat /sys/class/thermal/thermal_zone0/temp)" \
            "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)" \
            "$(awk '/MemAvailable/{print $2}' /proc/meminfo)" >>"$1"
        sleep 2
    done
}

run_variant() {
    local variant=$1 pass=$2 dir=$OUT/$variant/pass$pass args
    mkdir -p "$dir"
    echo "=== $(date +%T) $variant Durchgang $pass"

    stop_engine
    if ! start_engine "$variant"; then
        echo "FEHLER Start von $variant" | tee "$dir/failed"
        return
    fi

    case $variant in
    ollama-*)
        wait_ready http://127.0.0.1:11434/api/version
        args=(-num-ctx $CTX)
        ;;
    llamacpp-*)
        wait_ready http://127.0.0.1:8080/health
        args=(-openai http://127.0.0.1:8080/v1)
        ;;
    esac
    if [ $? -ne 0 ]; then
        echo "FEHLER $variant wurde nicht bereit" | tee "$dir/failed"
        sudo podman logs "$ENGINE" >"$dir/engine.log" 2>&1
        stop_engine
        return
    fi

    system_info >"$dir/system.txt" 2>&1
    sampler "$dir/samples.csv" &
    local sampler_pid=$!

    local tokens
    for tokens in $PROMPTS; do
        ./ollama-bench -model "$MODEL" -epochs "$EPOCHS" -warmup "$WARMUP" -max-tokens "$MAXT" \
            -prompt-tokens "$tokens" -temperature 0 -seed 42 -timeout 900 -format csv \
            -output "$dir/p$tokens.csv" "${args[@]}" 2>"$dir/p$tokens.err" ||
            echo "FEHLER $variant p$tokens" | tee -a "$dir/failed"
    done

    kill "$sampler_pid" 2>/dev/null
    wait "$sampler_pid" 2>/dev/null
    sudo podman logs "$ENGINE" >"$dir/engine.log" 2>&1
    stop_engine
    sleep 60
}

sudo podman stop -t 5 ollama >/dev/null 2>&1

for pass in $(seq 1 "$PASSES"); do
    for variant in "${VARIANTS[@]}"; do
        run_variant "$variant" "$pass"
    done
done

stop_engine
echo "=== $(date +%T) Fertig"
