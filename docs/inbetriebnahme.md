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
| 9 | Admins über Wartung informieren | Admin |

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
| Neustart nach Stromausfall | noch nicht gefunden | `Power On` oder `Always On` | Offen seit 11.11.2026. Wahrscheinliche Stellen sind `Advanced` → `Onboard Devices setting` oder `Advanced` → `AMD CBS` → `FCH Common Options` → `Ac Power Loss Options`. Bis dahin nach einem Stromausfall den Einschaltknopf drücken |

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

1. Ollama im Container starten. Der Port hört nur auf der Adresse von Tailscale, damit Engagierte Ollama im Tailnet testen können, etwa mit opencode nach 7.4, siehe [ADR 47](adr/0047-dienste-zum-testen-im-tailnet-oeffnen.adoc). Ollama kennt keine Anmeldung. Wer MANUEL im Tailnet erreicht, kann also Modelle nutzen, laden und löschen. `OLLAMA_IGPU_ENABLE=1` ist nötig, weil Ollama die iGPU sonst verwirft und unbemerkt auf der CPU rechnet.

```bash
sudo podman run -d --name ollama \
  --device /dev/dri --cap-add PERFMON \
  --security-opt label=disable \
  -e OLLAMA_IGPU_ENABLE=1 \
  -e OLLAMA_CONTEXT_LENGTH=32768 \
  -v ollama:/root/.ollama \
  -p "$(tailscale ip -4):11434:11434" --restart=always \
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
6. Tailscale SSH ausgeschaltet lassen. Dann nimmt der normale SSH-Dienst auch über Tailscale die Verbindungen an, mit den Schlüsseln aus `build_files/github-users`. Mit Tailscale SSH bräuchte jede Person, mit der MANUEL geteilt ist, eine eigene SSH-Regel in der Richtlinie des Tailnets. Wer es versehentlich eingeschaltet hat, schaltet es so wieder ab.

```bash
sudo tailscale set --ssh=false
```

7. Prüfen, dass das Gerät verbunden ist, und sich von einem anderen Gerät im Tailnet per SSH anmelden.

```bash
tailscale status
ssh core@manuel
```

Ollama bleibt an `127.0.0.1` gebunden und ist über Tailscale nicht erreichbar. Am 10.11.2026 lauschen nach außen nur SSH auf Port 22 und die Namensauflösung LLMNR von systemd-resolved auf Port 5355, geprüft mit `sudo ss -tln`. Sobald NetBird läuft, wird `manuel` aus dem Tailnet entfernt und die Zeile in `build_files/build.sh` wieder gelöscht.

## 7 Testumgebung mit Zammad, n8n, Mailpit und Open WebUI

Die Entscheidung steht in [ADR 43](adr/0043-eine-testumgebung-auf-manuel-betreiben.adoc). Das Image bringt die Compose-Datei von Zammad aus dem Submodul `quellen/zammad-docker-compose` und die Ergänzungen aus `testumgebung/` unter `/usr/share/manuel` mit. Der Befehl `zammad-compose` startet alles damit.

- Elasticsearch läuft nicht, das spart Speicher für die Modelle. Zammad sucht dann nur in der Datenbank.
- Alle Dienste hören nur auf der Adresse von Tailscale, ohne TLS und ohne Reverse Proxy, siehe [ADR 47](adr/0047-dienste-zum-testen-im-tailnet-oeffnen.adoc). `zammad-compose` setzt dafür `MANUEL_BIND_IP` aus `tailscale ip -4`. Aus dem lokalen Netz ist nichts erreichbar.

| Dienst | Adresse |
|---|---|
| Open WebUI | http://manuel:3000 |
| n8n | http://manuel:5678 |
| Mailpit | http://manuel:8025 |
| Zammad | http://manuel:8080 |
| Ollama | http://manuel:11434 |

- Podman bindet die Ports selbst und kann das erst, wenn Tailscale eine Adresse hat. Beim Hochfahren wartet `podman-restart.service` deshalb bis zu 60 Sekunden. Fehlt ein Container danach, ihn mit `sudo podman start <name>` starten, sobald Tailscale läuft.
- In der Richtlinie des Tailnets bekommen Admins alle Ports, wer MANUEL nur geteilt bekommt, erreicht nur Open WebUI und Ollama. Ein Beispiel mit Grants, bei dem MANUEL in der Verwaltung des Tailnets den Tag `tag:manuel` trägt. Vor dem Einsatz mit einem geteilten Konto testen, siehe https://tailscale.com/kb/1324/acl-grants.

```json
{
  "tagOwners": { "tag:manuel": ["autogroup:admin"] },
  "grants": [
    { "src": ["autogroup:admin"], "dst": ["tag:manuel"], "ip": ["*"] },
    { "src": ["autogroup:shared"], "dst": ["tag:manuel"], "ip": ["tcp:3000", "tcp:11434"] }
  ]
}
```

### 7.1 Frisches Zammad und Test mit Mailpit

Bevor echte Daten ins Spiel kommen, zeigt ein frisches Zammad ohne Daten, dass Mails sicher in Mailpit landen.

1. Den Stapel starten. Beim ersten Mal lädt das die Images. Docker Hub begrenzt Downloads ohne Anmeldung. Bricht ein Download ab, etwa von n8n, später erneut starten oder die übrigen Dienste einzeln nennen.

```bash
zammad-compose up -d
zammad-compose ps
```

2. Alle Wege nach außen abschalten und Benachrichtigungen an Mailpit leiten. Danach eine Testmail schicken. Das Testskript bricht ab, wenn noch ein anderer Kanal aktiv ist oder die Mail nicht an Mailpit ginge.

```bash
zammad "$(cat /usr/share/manuel/testumgebung/disable_outbound.rb)"
zammad "$(cat /usr/share/manuel/testumgebung/mail_test.rb)"
```

3. Prüfen, dass die Mail in Mailpit liegt.

```bash
curl -s http://127.0.0.1:8025/api/v1/messages | python3 -m json.tool | grep -E '"Subject"|"Address"'
```

4. Unser Ollama ins Netz des Stapels hängen. Zammad erreicht es dann als Anbieter Ollama unter `http://ollama:11434`, ohne dass ein Port nach außen aufgeht. Das Szenario `add-ollama.yml` von Zammad brauchen wir nicht, es startet eine zweite Ollama ohne GPU.

```bash
sudo podman network connect zammad_default ollama
zammad 'require "net/http"; puts Net::HTTP.get(URI("http://ollama:11434/api/version"))'
```

   Am 11.11.2026 lief so Zammad 7.2.2 ohne Elasticsearch. Nach `disable_outbound.rb` war nur der Kanal für Benachrichtigungen aktiv, die Testmail lag in Mailpit, und Zammad erreichte Ollama 0.40.14.

5. Mit einem echten Testpostfach prüfen, dass Zammad abruft, aber alles Ausgehende in Mailpit landet. Nie mit dem Postfach des Repair Café. Im Netz des Stapels gibt sich Mailpit als `mail.lima-city.de` aus, mit SMTP über SSL auf Port 465 und jeder Anmeldung. Im Einrichtungsassistenten SMTP also wie bei lima-city eintragen, `mail.lima-city.de`, Port 465, aber SSL-Verifizierung auf nein, weil Mailpit ein selbst ausgestelltes Zertifikat hat. Für den Abruf per IMAP die IP-Adresse von lima-city statt des Namens nehmen, am 11.11.2026 `212.83.45.134` mit Port 993, ebenfalls ohne Prüfung des Zertifikats. Mit dem Namen landet der Abruf bei Mailpit, das kein IMAP kann. Direkt danach den Versand aller Kanäle auf Mailpit umleiten, der Abruf bleibt an. Dann von einer eigenen Adresse eine Mail schicken. Das Ticket entsteht in Zammad, die automatische Antwort und Antworten im Ticket erscheinen nur in Mailpit.

```bash
zammad "$(cat /usr/share/manuel/testumgebung/redirect_outbound.rb)"
```

   Danach die Gegenprobe für den Fall mit Backup. Mit einer Mail „Test 1“ prüfen, dass Zammad abruft. Dann `disable_outbound.rb` ausführen, eine Mail „Test 2“ schicken und einige Minuten warten. „Test 2“ muss im Postfach bleiben, und eine Antwort im Ticket „Test 1“ darf außen nicht ankommen.
6. Im Browser über Tailscale arbeiten. Zammad liegt unter http://manuel:8080, Mailpit unter http://manuel:8025 und n8n unter http://manuel:5678. Beim ersten Aufruf richtet Zammad ein Admin-Konto ein. Als Adresse des Systems dort `http://manuel:8080` angeben, sonst lehnt Zammad die Verbindung für Live-Updates ab.

### 7.2 Backup einspielen

Erst wenn 7.1 funktioniert und die Ports wieder auf `127.0.0.1` beschränkt sind. Die beiden Dateien `*_zammad_db.psql.gz` und `*_zammad_files.tar.gz` liefert ein Admin aus der Sicherung. Niemand greift dafür auf das laufende Zammad zu.

1. Die frische Instanz löschen und das Backup bereitlegen.

```bash
zammad-compose down -v
zammad-compose create zammad-backup
backup=$(sudo podman volume inspect zammad_zammad-backup --format '{{.Mountpoint}}')
sudo mkdir -p "$backup/restore"
sudo cp ~/backup/*_zammad_db.psql.gz ~/backup/*_zammad_files.tar.gz "$backup/restore/"
```

2. Zammad ohne Scheduler starten und warten, bis die Wiederherstellung fertig ist. Danach ist der Ordner `restore` umbenannt.

```bash
zammad-compose up -d zammad-backup zammad-railsserver mailpit
sudo ls "$backup"
```

3. Vor allem anderen alle Wege nach außen abschalten, dann den Rest starten und die Mail erneut prüfen.

```bash
zammad "$(cat /usr/share/manuel/testumgebung/disable_outbound.rb)"
zammad-compose up -d
zammad "$(cat /usr/share/manuel/testumgebung/mail_test.rb)"
```

### 7.3 Open WebUI für Testende

Open WebUI und Ollama hängen gemeinsam im Netz `manuel`, dort erreicht Open WebUI Ollama unter `http://ollama:11434`. Port 3000 hört nur auf der Adresse von Tailscale, im Tailnet also unter http://manuel:3000. Seit dem 12.11.2026 läuft Open WebUI ohne Anmeldung mit `WEBUI_AUTH=False`. Alle arbeiten dann mit demselben Admin-Konto, können also Einstellungen ändern und die Chats der anderen lesen. Deshalb gehören keine Angaben von Gästen in Open WebUI. Das Login lässt sich nur bei einer frischen Installation abschalten. Zum Wiedereinschalten den Container mit `WEBUI_AUTH=True` neu starten, danach wird das erste Konto Admin.

```bash
sudo podman network create manuel
sudo podman network connect manuel ollama
sudo podman run -d --name open-webui --restart=always --network manuel -p "$(tailscale ip -4):3000:8080" \
  -e OLLAMA_BASE_URL=http://ollama:11434 -e WEBUI_AUTH=False \
  -v open-webui:/app/backend/data \
  ghcr.io/open-webui/open-webui:v0.13.3
```

In der Verwaltung des Tailnets MANUEL mit den Testenden teilen. Die Richtlinie lässt sie nur auf die Ports 3000 und 11434, siehe Beispiel am Anfang von Schritt 7. Keine echten Ticketdaten und keine Angaben von Gästen in Open WebUI, zum Vorführen dienen die anonymisierten Tickets nach [ADR 39](adr/0039-nur-tickets-von-2025-und-2026-anonymisieren.adoc). Die Websuche bleibt aus, bis SearXNG nach [ADR 35](adr/0035-anleitungen-ueber-eine-eigene-suche-finden.adoc) läuft.

n8n gehört zum Stapel und startet mit `zammad-compose`. `podman-compose` taugt dafür nicht, Version 1.6.0 scheitert an verschachtelten Variablen in der Compose-Datei von Zammad. `zammad-compose` nutzt deshalb `docker-compose` über den Socket von Podman.

### 7.4 Ollama mit opencode testen

[opencode](https://opencode.ai) ist ein Harness für das Terminal. Ab Version 2 findet es Modelle von Ollama selbst. Für MANUEL im Projekt oder unter `~/.config/opencode/` eine Datei `opencode.jsonc` anlegen. Die Adresse endet auf `/v1`, opencode leitet daraus die Abfrage der Modelle ab. Modelle nur für Embeddings wie `bge-m3` erscheinen nicht.

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "providers": {
    "ollama": {
      "settings": {
        "baseURL": "http://manuel:11434/v1"
      }
    }
  }
}
```

In opencode mit `/models` ein Modell wählen. Für Werkzeugaufrufe eignen sich größere Modelle wie `qwen3.6:35b-a3b`. Ollama begrenzt den Kontext auf 32768 Token. Quelle ist https://github.com/anomalyco/opencode/blob/dev/services/site/src/docs/content/providers.mdx.

### 7.5 Aufräumen

Nach dem Test die Instanz mit allen Daten löschen.

```bash
zammad-compose down -v
```

## 8 Logging von System und Strom

Entwurf vom 10.11.2026. Am 11.11.2026 lief der Logger einmal von Hand auf MANUEL und lieferte alle Werte außer denen der Steckdose. Das Image bringt den Logger `/usr/libexec/manuel/metrics_log.py` und den Timer `manuel-metrics.timer` mit. Er schreibt jede Minute eine Zeile mit Auslastung, Speicher, GPU, Temperaturen und Strom nach `/var/log/manuel/metrics-JJJJ-MM.csv`.

1. Die Steckdose NOUS A1T einrichten. Sie kommt mit Tasmota.
   1. Die Steckdose einstecken und mit dem WLAN `tasmota-…` verbinden, das sie aufspannt. Unter http://192.168.4.1 das WLAN des Makerspace eintragen.
   2. Unter Configuration, Other das Template eintragen und Activate anhaken. Quelle ist https://templates.blakadder.com/nous_A1T.html.

      ```json
      {"NAME":"NOUS A1T","GPIO":[32,0,0,0,2720,2656,0,0,2624,320,224,0,0,0],"FLAG":0,"BASE":49}
      ```

   3. Unter Configuration, Other ein Passwort für die Weboberfläche setzen. Ohne Passwort kann jeder im Netz MANUEL ausschalten. Am 11.11.2026 ist noch keines gesetzt.
   4. In der Console drei Befehle eingeben. Nach einem Stromausfall schaltet die Steckdose wieder ein. Die Taste an der Steckdose schaltet MANUEL nicht mehr aus. Der Name erscheint in der Weboberfläche.

      ```
      PowerOnState 1
      SetOption73 1
      DeviceName MANUEL
      ```

   5. Die Strommessung kalibrieren, siehe [Power Monitoring Calibration](https://tasmota.github.io/docs/Power-Monitoring-Calibration/). Ab Werk zeigte die Steckdose am 11.11.2026 291 V statt rund 230 V. Dafür eine rein ohmsche Last mit bekannter Leistung einstecken, am besten eine Glüh- oder Halogenlampe, nicht MANUEL, keine LED-Lampe und kein Netzteil. Ab Tasmota 14.2 bekommt `VoltageSet` die mit einem Multimeter gemessene Spannung oder 230, und `PowerSet` die Leistung der Last zusammen mit derselben Spannung. Den Strom berechnet die Steckdose daraus. Vor Tasmota 14.2 bekommt `PowerSet` nur die Leistung, und `CurrentSet` den Strom in mA, also Leistung mal 1000 durch Spannung. Danach muss der Leistungsfaktor in der Weboberfläche nahe 1,00 liegen, sonst die Kalibrierung wiederholen. Ohne passende Last korrigiert `VoltageSet` allein die Spannung, die Leistung ist dann nur ungefähr richtig.

      ```
      VoltRes 1
      WattRes 2
      VoltageSet 230
      PowerSet 60.0,230
      ```

      Kalibriert am 11.11.2026 mit einem Wasserkocher mit 2200 W laut Typenschild, ohne Multimeter mit 230 V. Tasmota antwortete mit `VoltageSetCal` 1611 und `PowerSetCal` 12367. Werte im Log vor 06:57 Uhr sind unkalibriert. Zur Kontrolle zeigte die Steckdose um 07:07 Uhr 230,9 V, ein Multimeter maß 229,7 V. Die Spannung stimmt damit auf 0,5 Prozent. Die Leistung hängt an der Angabe auf dem Typenschild und ist auf einige Prozent genau. MANUEL zog im Leerlauf rund 20 bis 28 W bei einem Leistungsfaktor von 0,68.

   6. Im Router der Steckdose eine feste Adresse geben.
2. Adresse und Passwort der Steckdose auf MANUEL eintragen. Die Datei liegt nur auf dem Gerät und ist nur für root lesbar. Ohne `NOUS_URL` bleiben die Spalten für Strom leer.

```bash
sudo mkdir -p /etc/manuel
sudo install -m 0600 /dev/null /etc/manuel/metrics.env
sudoedit /etc/manuel/metrics.env
```

```
NOUS_URL=http://<adresse-der-steckdose>
NOUS_USER=admin
NOUS_PASSWORD=<passwort>
```

3. Prüfen, dass der Timer läuft und Zeilen ankommen.

```bash
systemctl status manuel-metrics.timer
tail -n 3 /var/log/manuel/metrics-$(date +%Y-%m).csv
```

4. Die Werte der Steckdose mit ihrer Weboberfläche vergleichen.

## 9 Admins über Wartung informieren

Das Image bringt die Prüfung `/usr/libexec/manuel/status_check.py` und den Timer `manuel-status.timer` mit, siehe [ADR 44](adr/0044-admins-ueber-wartung-informieren.adoc). Zehn Minuten nach dem Start und jeden Morgen um 7 Uhr prüft sie Firmware-Updates, ein wartendes Image, den Container von Ollama und den Logger. Die Ergebnisse stehen im Journal und beim Login. Eingespielt wird nichts.

1. Von Hand prüfen, ohne etwas zu schreiben oder zu senden.

```bash
sudo python3 /usr/libexec/manuel/status_check.py --dry-run
```

2. Firmware-Updates bewusst einspielen, am besten zusammen mit einem geplanten Neustart. Nach einem Update des BIOS die Einstellungen aus Schritt 1 prüfen, vor allem die 16 GiB UMA.

```bash
fwupdmgr get-upgrades
sudo fwupdmgr update
```

3. Den Versand per E-Mail einrichten, sobald feststeht, über welchen Mailserver er läuft. Die Datei liegt nur auf dem Gerät.

```bash
sudo install -m 0600 /dev/null /etc/manuel/notify.env
sudoedit /etc/manuel/notify.env
```

```
SMTP_HOST=<mailserver>
SMTP_PORT=587
SMTP_USER=<benutzer>
SMTP_PASSWORD=<passwort>
SMTP_FROM=manuel@<domain>
NOTIFY_TO=<admin1>,<admin2>
```

Bei lima-city gilt laut [Hilfe von lima-city](https://www.lima-city.de/hilfe/wie-kann-ich-meine-e-mail-adressen-einrichten) `SMTP_HOST=mail.lima-city.de` mit `SMTP_PORT=465` und SSL von Anfang an. Benutzername ist die volle E-Mail-Adresse des Postfachs, Absender dieselbe Adresse.

