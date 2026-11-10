# Inbetriebnahme des Mini-PCs

Der MINISFORUM AI X1 Pro-370 wurde am 05.11.2026 geliefert. Diese Anleitung beschreibt die nötigsten Schritte bis zum Benchmark. Danach geht es mit Phase 1 und 2 im [Plan](../PLAN.md) weiter.

Die Reihenfolge ist wichtig, denn in Schritt 3 wird die vorinstallierte Windows-Installation gelöscht.

| Schritt | Aufgabe | Wer |
|---|---|---|
| 1 | BIOS umstellen | Admin |
| 2 | Windows-Schlüssel sichern | Admin |
| 3 | uCore installieren | Admin |
| 4 | Ersten Prompt testen | Admin |
| 5 | Benchmark durchführen | Claude Code, BIOS-Änderungen durch Admin |
| 6 | Tailscale als Übergang einrichten | Claude Code, Anmeldung im Browser durch Admin |
| 7 | Testumgebung mit Zammad, n8n, Mailpit und Open WebUI | Admin, Backup durch Admin |
| 8 | Logging von System und Strom | Admin |

## Vorbereitung des USB-Sticks

Installiert wird Fedora CoreOS, das beim ersten Start selbstständig auf unser Image auf Basis von uCore wechselt. Ein eigenes ISO von uCore gibt es dafür nicht.

[Ventoy](https://www.ventoy.net/) hat auf dem Mini-PC nicht funktioniert. Im normalen Modus blieb der Start hängen, im Grub2-Modus meldete Ventoy `No bootfile found for UEFI!`. Das ISO kommt deshalb direkt auf den Stick.

1. Das Live-ISO von [Fedora CoreOS](https://fedoraproject.org/coreos/download/?stream=stable) aus dem Stream Stable für Bare Metal und x86_64 herunterladen. Wir haben [44.20261023.3.1](https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/44.20261023.3.1/x86_64/fedora-coreos-44.20261023.3.1-live-iso.x86_64.iso) verwendet.
2. Das ISO mit dem [Fedora Media Writer](https://github.com/FedoraQt/MediaWriter) auf einen USB-Stick schreiben. Dabei wird der Stick gelöscht.
3. `manuel.ign` auf einen zweiten USB-Stick kopieren. Wie die Datei entsteht, steht in [butane/README.md](../butane/README.md).

## 1 BIOS umstellen

Das BIOS lässt sich direkt aus Windows heraus öffnen:

1. In den Einstellungen `System` und dann `Wiederherstellung` öffnen.
2. Bei `Erweiterter Start` auf `Jetzt neu starten` klicken.
3. `Problembehandlung`, dann `Erweiterte Optionen` und `UEFI-Firmwareeinstellungen` wählen.
4. Auf `Neu starten` klicken.

Steckt Windows noch im Einrichtungsassistenten, das Gerät ausschalten, einschalten und direkt mehrfach `Entf` drücken.

Im BIOS haben wir diese Werte eingestellt oder als Ausgangswert notiert:

| Einstellung | Pfad | Wert | Hinweis |
|---|---|---|---|
| Secure Boot | `Security` | `Disabled` | Für den Start vom USB-Stick abgeschaltet |
| Leistungsprofil | `Advanced` → `PowerLimit Setting` | `Performance Mode` | Gilt für alle Messungen im Benchmark |
| Lüfter | `Advanced` → `Hardware Monitor` → Fan Mode | Performance-Modus | Lautstärke im Dauerbetrieb prüfen wir später |
| iGPU Configuration | `Advanced` → `AMD CBS` → `NBIO Common Options` → `GFX Configuration` | `UMA_Specified` | Ausgangswert, nicht geändert |
| UMA Frame Buffer Size | wie iGPU Configuration | `16G` | Ausgangswert war `2G`, Begründung siehe [Benchmarks](benchmarks.md) |
| SmartShift Control | `Advanced` → `AMD CBS` → `SMU Common Options` | `Auto` | Nicht geändert |

Die Pfade können je nach BIOS-Version abweichen. Eine offizielle Beschreibung des BIOS von Minisforum haben wir nicht gefunden. Einen Rundgang durch die Menüs mit Bildern bietet der Artikel [Minisforum AI X1 Pro running Linux: BIOS](https://www.linuxlinks.com/minisforum-ai-x1-pro-running-linux-bios/) von LinuxLinks. Das Gerät ist im [Shop von Minisforum](https://store.minisforum.com/products/minisforum-ai-x1-pro) beschrieben.

## 2 Windows-Schlüssel sichern

Der Mini-PC wird mit Windows geliefert. Der Schlüssel steht normalerweise in der Firmware und übersteht deshalb das Löschen der SSD. Wir sichern ihn trotzdem, falls wir das Gerät einschicken müssen oder Windows wieder brauchen.

1. Den USB-Stick einstecken und in Windows den erweiterten Start wie in Schritt 1 öffnen. Dort `Gerät verwenden` und den USB-Stick wählen.
2. Die Meldungen auf der Konsole abschalten. Das Live-System meldet laufend `Bluetooth hci0 Failed to load firmware`, was harmlos ist, aber die Eingabe verdeckt. Im Log bleiben die Meldungen erhalten. Noch gilt das englische Layout, deshalb steht hier `ß` für `-`. Am Bildschirm erscheint `sudo dmesg -n 1`.

```text
sudo dmesg ßn 1
```

3. Das deutsche Tastaturlayout einstellen, weil das Live-System mit dem englischen Layout startet. `Y` und `Z` sind dort vertauscht, deshalb steht hier `loadkezs`. Am Bildschirm erscheint `sudo loadkeys de`.

```text
sudo loadkezs de
```

4. Den Schlüssel auslesen.

```bash
sudo tail -c 29 /sys/firmware/acpi/tables/MSDM; echo
```

Funktioniert `loadkeys` nicht, lässt sich der Befehl auch mit englischem Layout auf einer deutschen Tastatur eingeben. Dabei ergibt `Ö` das Zeichen `;`, `-` das Zeichen `/`, `ß` das Zeichen `-` und `Z` den Buchstaben `y`.

```text
sudo tail ßc 29 -szs-firmware-acpi-tables-MSDMö echo
```

5. Das Ergebnis in Vaultwarden speichern.

Der Schlüssel darf nicht in dieses öffentliche Repo. Fehlt die Datei `MSDM`, liegt kein Schlüssel in der Firmware. Dann vor Schritt 3 Windows einmal starten, einrichten und in den Einstellungen unter Aktivierung prüfen, ob eine digitale Lizenz vorhanden ist.

## 3 uCore installieren

Dieser Schritt löscht die interne SSD. Vorher im Reiter Actions prüfen, dass der letzte Build des Images durchgelaufen ist, denn die SSH-Schlüssel der Admins kommen aus dem Image.

1. Das Netzwerkkabel anschließen.
2. Im Live-System aus Schritt 2 den zweiten Stick einbinden und Fedora CoreOS mit `manuel.ign` installieren, wie in [butane/README.md](../butane/README.md) beschrieben.
3. Abwarten, bis das System auf unser Image gewechselt hat. Das dauert zwei weitere Neustarts.
4. Per SSH als Benutzer `core` anmelden und das gebootete Image prüfen.

```bash
rpm-ostree status
```

## 4 Ersten Prompt testen

Dieser Test zeigt, dass Ollama im Container die GPU nutzt. Das kleine Modell `gemma3:4b` ist schnell geladen und nur für diesen Test gedacht.

1. Ollama im Container starten. Der Port ist nur an `127.0.0.1` gebunden, weil Ollama keine Anmeldung kennt. `OLLAMA_IGPU_ENABLE=1` ist nötig, weil Ollama die iGPU sonst verwirft und unbemerkt auf der CPU rechnet.

```bash
sudo podman run -d --name ollama \
  --device /dev/dri --cap-add PERFMON \
  --security-opt label=disable \
  -e OLLAMA_IGPU_ENABLE=1 \
  -e OLLAMA_CONTEXT_LENGTH=32768 \
  -v ollama:/root/.ollama \
  -p 127.0.0.1:11434:11434 \
  docker.io/ollama/ollama:latest
```

2. Den ersten Prompt absetzen. Beim ersten Mal lädt Ollama das Modell herunter, das dauert einige Minuten.

```bash
sudo podman exec -it ollama ollama run gemma3:4b "Mein Toaster wird nicht mehr heiß. Was prüfe ich zuerst? Antworte in drei kurzen Sätzen." --verbose
```

3. Prüfen, ob das Modell auf der GPU läuft. In der Spalte `PROCESSOR` muss `100% GPU` stehen.

```bash
sudo podman exec ollama ollama ps
```

Für einen weiteren Kaltstart das Modell vorher entladen.

```bash
sudo podman exec ollama ollama stop gemma3:4b
```

Am 05.11.2026 lieferte der erste Prompt diese Antwort:

> Hier sind drei kurze Sätze, die Ihnen helfen, das Problem zu diagnostizieren:
>
> Zuerst überprüfen Sie, ob der Toaster richtig an einer Steckdose angeschlossen ist und ob die Steckdose funktioniert. Überprüfen Sie dann den Schutzmechanismus, der möglicherweise durch Überhitzung oder eine Fehlfunktion ausgelöst wurde. Schließlich, prüfen Sie, ob die Heizelemente nicht blockiert sind.

Gemessen haben wir mit Ollama 0.40.14 über Vulkan auf der Radeon 890M bei 2 GiB UMA diese Werte:

| Messgröße | Wert |
|---|---|
| Anteil auf der GPU | 100 % |
| Gesamtdauer ohne Download | 8,7 s |
| Ladezeit des Modells | 5,5 s |
| Prompt-Verarbeitung | 121,83 Token pro Sekunde |
| Generierung | 28,25 Token pro Sekunde |

Das ist ein einzelner Kaltstart und kein Benchmark. Die Antwort zeigt auch, warum wir eigene Prompts brauchen, denn ein Sicherheitshinweis fehlt.

## 5 Benchmark durchführen

Den Benchmark führt [Claude Code](https://claude.com/product/claude-code) mit dem Modell Claude Opus 5.5 von einem Admin-Rechner aus per SSH durch. Es richtet die Container ein, lässt die Messungen laufen und wertet sie aus. BIOS-Änderungen macht ein Admin am Gerät, die Ergebnisse prüfen die Admins.

Alle Engines laufen in Containern. Das Betriebssystem bleibt dadurch unverändert. Ollama und llama.cpp binden wir an `127.0.0.1`, weil beide ohne Anmeldung laufen. Auf dem Gerät liegen während des Benchmarks keine echten Ticketdaten.

Eingesetzt werden diese Werkzeuge:

- `ollama-bench` aus dem Submodul `ollama` für alle Messungen über eine Server-Schnittstelle
- [eval/bench.sh](../eval/bench.sh) für den Ablauf der Messungen
- Podman für die Container der Engines
- `tmux`, damit Läufe einen Abbruch der SSH-Verbindung überstehen

Hauptkandidat ist llama.cpp mit Vulkan. ROCm testen wir nicht, weil Vulkan auf der Radeon 890M bei der Textgenerierung [deutlich schneller](https://msf.github.io/blogpost/local-llm-performance-framework13.html) war und wir uns den Aufwand sparen. Verglichen werden diese Engines:

- llama.cpp mit Vulkan
- Ollama mit Vulkan, weil Zammad es direkt ansprechen kann
- CPU allein als Basiswert

Gemessen wird in Runden. Jede Runde ändert nur einen Faktor, der Gewinner geht in die nächste Runde.

| Runde | Vergleich |
|---|---|
| 1 | Engines aus der Liste oben mit `qwen3.6:35b-a3b` |
| 2 | Alle Modelle aus [eval/models-runde2.txt](../eval/models-runde2.txt) und Qwen3.8-27B `UD-Q4_K_XL` von [Unsloth](https://unsloth.ai/docs/models/qwen3.8), falls vorhanden auch mit MTP |
| 3 | UMA im BIOS, GTT-Limit im Kernel und Flags wie `-ub` |
| 4 | Dauertest über etwa 30 Minuten mit dem Gewinner |
| 5 | Einzelversuch mit Qwen3.8-Flash-Next `UD-IQ1_S`, das mit 72,5 GB nicht in den Speicher passt und von der SSD nachlädt |

Runde 2 ist bewusst breit angelegt. Geben die Reparierenden Rückmeldung zur Qualität, können wir ohne neue Messung auf ein anderes Modell ausweichen.

Für jede Variante gelten dieselben Bedingungen:

- Prompts mit 512 und 4096 Tokens, damit auch lange Prompts wie der des Ticket Categorizer abgedeckt sind
- Kontextlänge 32768, Temperatur 0, fester Seed
- 2 Läufe zum Aufwärmen und 10 gemessene Läufe
- gleiches Image per Digest, gleiche Modelldatei und gleiches Leistungsprofil
- `--parallel 1`, weil sonst die Messwerte für MTP nicht vergleichbar sind
- jede Variante zweimal im Wechsel mit der Vergleichsvariante, um Einflüsse der Temperatur zu erkennen

Festgehalten werden Prompt-Verarbeitung und Generierung in Token pro Sekunde, Zeit bis zum ersten Token, Ladezeit, Speicherbedarf und der Anteil auf der GPU. Läufe mit einem Anteil auf der CPU gelten nur in der Vergleichsgruppe CPU. Die Ergebnisse stehen in [benchmarks.md](benchmarks.md).

Der Benchmark misst nur die Geschwindigkeit. Ob ein Modell gut antwortet, zeigt erst der Testsatz aus Phase 3.

### Aufräumen

Container, Images und Modelle liegen unter `/var`, die Messskripte im Verzeichnis `~/bench`. Das GTT-Limit aus Runde 3 ist ein Kernel-Parameter und bleibt gesetzt, bis wir ihn entfernen. Nach dem Benchmark räumen wir deshalb auf und behalten nur, was wir für den Betrieb brauchen.

```bash
sudo podman rm -af
sudo podman image prune -af
rm -rf ~/bench
sudo rpm-ostree kargs --delete=ttm.pages_limit=<Wert>
```

Der letzte Befehl entfällt, wenn der Gewinner aus Runde 3 das Limit braucht. Das Volume mit den Modellen bleibt erhalten. Nicht mehr benötigte Modelle löschen wir einzeln, oder wir entfernen das Volume mit `sudo podman volume rm ollama`.

## 6 Tailscale als Übergang einrichten

Bis NetBird auf der Zugangs-VM läuft, erreichen Admins den Mini-PC über Tailscale, siehe [ADR 42](adr/0042-tailscale-als-uebergang-bis-netbird-nutzen.adoc). Eingerichtet am 10.11.2026. Tailscale ist in uCore enthalten, der Dienst war aber deaktiviert.

1. Im Image den Dienst aktivieren. Das steht in `build_files/build.sh` und gilt ab dem nächsten Build und Update.

```bash
systemctl enable tailscaled.service
```

2. Bis dahin den Dienst direkt auf dem Gerät aktivieren und starten. Die Einstellung liegt unter `/etc` und bleibt bei Updates erhalten.

```bash
sudo systemctl enable --now tailscaled
```

3. In der Verwaltung des Tailnets des Vereins unter Settings, Keys einen Auth-Key erzeugen. Einmalig verwendbar reicht, Ephemeral bleibt aus, sonst verschwindet das Gerät bei einer Trennung. Nie ein persönliches Konto verwenden, sonst hängt der Zugang an einer Person.
4. Das Gerät an der Konsole anmelden. `read -s` zeigt den Schlüssel beim Tippen nicht an, und er landet nicht in der Shell-History.

```bash
read -rsp "Auth-Key: " TS_KEY; echo
sudo tailscale up --hostname=manuel --auth-key="$TS_KEY"
unset TS_KEY
```

   Ohne Auth-Key gibt `sudo tailscale up --hostname=manuel` einen Link aus, über den sich das Gerät im Browser bestätigen lässt.
5. In der Verwaltung des Tailnets beim Gerät `manuel` den Ablauf des Schlüssels abschalten. Sonst muss sich der Mini-PC nach 180 Tagen neu anmelden.
6. Tailscale SSH einschalten. Dann prüft Tailscale beim Anmelden die SSH-Regeln in der Richtlinie des Tailnets, nicht die Schlüssel aus dem Image. Der normale SSH-Dienst auf Port 22 mit den Schlüsseln der Admins bleibt daneben bestehen.

```bash
sudo tailscale set --ssh
```

7. Prüfen, dass das Gerät verbunden ist, und sich von einem anderen Gerät im Tailnet per SSH anmelden.

```bash
tailscale status
ssh core@manuel
```

Ollama bleibt an `127.0.0.1` gebunden und ist über Tailscale nicht erreichbar. Am 10.11.2026 lauschen nach außen nur SSH auf Port 22 und die Namensauflösung LLMNR von systemd-resolved auf Port 5355, geprüft mit `sudo ss -tln`. Sobald NetBird läuft, wird `manuel` aus dem Tailnet entfernt und die Zeile in `build_files/build.sh` wieder gelöscht.

## 7 Testumgebung mit Zammad, n8n, Mailpit und Open WebUI

Entwurf vom 10.11.2026, noch nicht auf MANUEL ausgeführt. Die Entscheidung steht in [ADR 43](adr/0043-eine-testumgebung-auf-manuel-betreiben.adoc). Alle Dienste sind nur an `127.0.0.1` gebunden. Nach außen gibt es nur SSH und Open WebUI über `tailscale serve`.

1. Das Image aktualisieren. Es bringt die Befehle `ollama`, `zammad` und `n8n` mit und aktiviert `podman-restart.service`.

```bash
sudo bootc upgrade
sudo systemctl reboot
```

2. Ollama einen Neustart überstehen lassen. Der Container stammt aus Schritt 4 und hat noch keine Regel für den Neustart.

```bash
sudo podman update --restart=always ollama
ollama list
```

3. Die Compose-Datei von Zammad und dieses Repo holen. Der Commit von `zammad-docker-compose` ist derselbe wie im Submodul des IT-Plans.

```bash
sudo mkdir -p /var/lib/manuel
sudo git clone https://github.com/zammad/zammad-docker-compose /var/lib/manuel/zammad-docker-compose
sudo git -C /var/lib/manuel/zammad-docker-compose checkout 16f43d8
sudo git clone https://github.com/makerspace-gt/MANUEL /var/lib/manuel/MANUEL
```

4. Einen Befehl für Compose festlegen. Er nutzt `docker-compose` über den Socket von Podman, weil die Compose-Datei von Zammad Compose ab Version 2.24 verlangt. Die Version vorher mit `docker-compose version` prüfen.

```bash
cd /var/lib/manuel/zammad-docker-compose
compose() {
  sudo DOCKER_HOST=unix:///run/podman/podman.sock docker-compose -p zammad \
    -f docker-compose.yml -f /var/lib/manuel/MANUEL/testumgebung/compose.override.yml "$@"
}
```

5. Das Backup bereitlegen. Die beiden Dateien `*_zammad_db.psql.gz` und `*_zammad_files.tar.gz` liefert ein Admin aus der Sicherung. Niemand greift dafür auf das laufende Zammad zu.

```bash
compose create zammad-backup
backup=$(sudo podman volume inspect zammad_zammad-backup --format '{{.Mountpoint}}')
sudo mkdir -p "$backup/restore"
sudo cp ~/backup/*_zammad_db.psql.gz ~/backup/*_zammad_files.tar.gz "$backup/restore/"
```

6. Zammad ohne Scheduler starten und warten, bis die Wiederherstellung fertig ist. Danach ist der Ordner `restore` umbenannt.

```bash
compose up -d zammad-backup zammad-railsserver mailpit
sudo ls "$backup"
```

7. Vor allem anderen alle Wege nach außen abschalten. Das Skript deaktiviert alle Kanäle und Webhooks und leitet Benachrichtigungen an Mailpit.

```bash
zammad "$(cat /var/lib/manuel/MANUEL/testumgebung/disable_outbound.rb)"
```

8. Den Rest starten und die Version prüfen.

```bash
compose up -d
zammad 'puts Version.get'
```

9. Als Admin über einen SSH-Tunnel arbeiten. Zammad liegt dann unter http://localhost:8080, Mailpit unter http://localhost:8025 und n8n unter http://localhost:5678.

```bash
ssh -L 8080:127.0.0.1:8080 -L 8025:127.0.0.1:8025 -L 5678:127.0.0.1:5678 core@manuel
```

10. Open WebUI für Testende starten und im Tailnet bereitstellen. Es nutzt das Netz des Hosts, um Ollama auf `127.0.0.1` zu erreichen, und hört selbst nur auf `127.0.0.1:3000`.

```bash
sudo podman run -d --name open-webui --restart=always --network host \
  -e PORT=3000 -e HOST=127.0.0.1 -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:v0.13.3
sudo tailscale serve --bg 3000
```

11. In der Verwaltung des Tailnets MANUEL mit den Testenden teilen und in der Richtlinie für sie nur Port 443 erlauben. Prüfen, dass sie Open WebUI erreichen, aber nicht SSH.
12. Nach dem Test die Instanz mit allen Daten löschen.

```bash
compose down -v
```

## 8 Logging von System und Strom

Entwurf vom 10.11.2026. Das Image bringt den Logger `/usr/libexec/manuel/metrics_log.py` und den Timer `manuel-metrics.timer` mit. Er schreibt jede Minute eine Zeile mit Auslastung, Speicher, GPU, Temperaturen und Strom nach `/var/log/manuel/metrics-JJJJ-MM.csv`.

1. Die Adresse der Steckdose NOUS A1T mit Tasmota eintragen. Sie steht nur auf dem Gerät, nicht im Repo. Ohne sie bleiben die Spalten für Strom leer.

```bash
sudo mkdir -p /etc/manuel
echo 'NOUS_URL=http://<adresse-der-steckdose>' | sudo tee /etc/manuel/metrics.env
```

2. Prüfen, dass der Timer läuft und Zeilen ankommen.

```bash
systemctl status manuel-metrics.timer
tail -n 3 /var/log/manuel/metrics-$(date +%Y-%m).csv
```

3. Die Werte der Steckdose mit ihrer Weboberfläche vergleichen.

