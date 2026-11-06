#!/bin/bash
# Alle Messungen ohne BIOS-Änderung, nacheinander und ohne Aufsicht.
# Schlägt eine Variante fehl, steht das in failed, und es geht mit der nächsten weiter.
# Aufruf im Verzeichnis ~/bench.
#
# Ollama startet intern selbst llama-server und schaltet MTP ein, sobald das Modell
# einen MTP-Kopf hat. Damit der Vergleich fair bleibt, läuft jedes Modell zuerst in
# Ollama, und llama.cpp bekommt danach dieselben Flags.

cd ~/bench || exit 1
MTP="--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-backend-sampling"
UB="-ub 1024"
U38=models/Qwen3.8-27B-UD-Q4_K_XL.gguf
export KEEP=600
# Runde 1 lief mit 0.40.14, ihre Werte für Generierung und Prompt zeigen den Unterschied zur neuen Version
export IMG_OLLAMA=docker.io/ollama/ollama:0.40.15

slug() { echo "$1" | tr ':/.' '---'; }

echo "### Vergleich mit geladenem Modell und gleichen Flags"
./bench.sh fair-ollama-warm ollama-vulkan
LLAMA_ARGS="$MTP" ./bench.sh fair-llamacpp-mtp llamacpp-vulkan
LLAMA_ARGS="$UB $MTP" ./bench.sh fair-llamacpp-mtp-ub1024 llamacpp-vulkan
PASSES=1 ./bench.sh fair-ollama-cpu ollama-cpu

echo "### Runde 2 Modelle"
export PASSES=1
for model in qwen3.6:35b-a3b $(grep -v '^#' models-runde2.txt); do
    run=r2-$(slug "$model")
    MODEL=$model ./bench.sh "$run" ollama-vulkan
    args=$UB
    grep -q -- '--spec-type draft-mtp' "results/$run/ollama-vulkan/pass1/engine.log" && args="$UB $MTP"
    echo "llama.cpp Flags $args"
    MODEL=$model LLAMA_ARGS=$args ./bench.sh "$run" llamacpp-vulkan
done

echo "### Runde 2 Qwen3.8-27B von Unsloth"
MODEL=qwen3.8-27b-ud-q4 GGUF=$U38 LLAMA_ARGS=$UB ./bench.sh r2-unsloth-38 llamacpp-vulkan
MODEL=qwen3.8-27b-ud-q4 GGUF=$U38 LLAMA_ARGS="$UB $MTP" ./bench.sh r2-unsloth-38-mtp llamacpp-vulkan

echo "### MTP bei langen Antworten"
export MAXT=800 PROMPTS=512
MODEL=qwen3.8-27b-ud-q4 GGUF=$U38 LLAMA_ARGS=$UB ./bench.sh lang-unsloth-38 llamacpp-vulkan
MODEL=qwen3.8-27b-ud-q4 GGUF=$U38 LLAMA_ARGS="$UB $MTP" ./bench.sh lang-unsloth-38-mtp llamacpp-vulkan
MODEL=qwen3.6:35b-a3b LLAMA_ARGS=$UB ./bench.sh lang-qwen36 llamacpp-vulkan
MODEL=qwen3.6:35b-a3b LLAMA_ARGS="$UB $MTP" ./bench.sh lang-qwen36-mtp llamacpp-vulkan
unset MAXT PROMPTS PASSES

echo "### Dauertest"
PASSES=1 EPOCHS=90 PROMPTS=4096 ./bench.sh dauertest ollama-vulkan

# Zuletzt, weil das Modell größer als der Arbeitsspeicher ist und das System ausbremsen kann
echo "### Einzelversuch Flash-Next"
F=models/flash/Qwen3.8-Flash-Next-UD-IQ1_S-00001-of-00003.gguf
export PASSES=1 WAIT=1200 EPOCHS=2 WARMUP=0 PROMPTS=512
MODEL=flash-next-iq1 GGUF=$F ./bench.sh flash-gpu llamacpp-vulkan
MODEL=flash-next-iq1 GGUF=$F LLAMA_ARGS="-ngl 0" ./bench.sh flash-cpu llamacpp-vulkan
unset WAIT EPOCHS WARMUP PROMPTS PASSES

sudo podman start ollama
echo "### RUNDEN FERTIG $(date '+%F %T')"
