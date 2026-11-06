#!/bin/bash
# Vergleich mit anderer UMA-Größe. Aufruf im Verzeichnis ~/bench mit dem Namen des Laufs,
# zum Beispiel ./uma.sh uma16. Gleiche Flags wie Runde 2, damit die Werte vergleichbar bleiben.
# Die großen Modelle laufen mit 5 statt 10 Läufen, weil sie sonst zu lange dauern.

cd ~/bench || exit 1
NAME=$1
MTP="--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-backend-sampling"
UB="-ub 1024"
export KEEP=600 PASSES=1 IMG_OLLAMA=docker.io/ollama/ollama:0.40.15
export LLAMA_ARGS="$UB $MTP"

echo "### $NAME Qwen 3.6"
MODEL=qwen3.6:35b-a3b ./bench.sh "$NAME-qwen36" ollama-vulkan llamacpp-vulkan
for model in gemma4:31b qwen3.8:27b; do
    echo "### $NAME $model"
    MODEL=$model EPOCHS=5 WARMUP=1 ./bench.sh "$NAME-${model%%:*}" ollama-vulkan llamacpp-vulkan
done
./wechsel.sh "$NAME"
sudo podman start ollama >/dev/null 2>&1
echo "### $NAME FERTIG $(date '+%F %T')"
