# Plan

Dieser Plan beschreibt, wie wir MANUEL vom Kauf der Hardware bis zum Verwendungsnachweis umsetzen. Er knüpft an unsere bestehende Infrastruktur in [docker-compose-server](https://github.com/makerspace-gt/docker-compose-server) an.

## Rahmenbedingungen

- **Hardware** ist ein MINISFORUM AI X1 Pro-370 mit AMD Ryzen AI 9 HX 370, Radeon 890M, XDNA-2-NPU, 64 GB DDR5 und 1 TB SSD.
- **Bewilligungszeitraum** ist vom 15.09.2026 bis 31.12.2026. Bis dahin müssen alle Ausgaben bezahlt sein.
- **Verwendungsnachweis** mit Sachbericht und zahlenmäßigem Nachweis ist bis 31.03.2027 im Förderportal der DSEE fällig. Der Sachbericht muss auch die Veröffentlichung und Kommunikation der Ergebnisse nachweisen.
- **Zweckbindung** gilt zwei Jahre nach Ende des Bewilligungszeitraums, also bis 31.12.2028.
- **Förderhinweis** mit DSEE-Logo und dem Zusatz »Gefördert durch« gehört auf alle Veröffentlichungen, also auch in dieses Repo und auf das Gerät.
- **Abweichung vom Finanzierungsplan** muss geklärt werden. Bewilligt ist die Variante mit 2 TB, gekauft wird die Variante mit 1 TB.

## Architektur

Der Mini-PC steht im Makerspace hinter NAT. Zammad läuft auf unseven.makerspace-gt.de. Damit wir im Makerspace keine Ports öffnen müssen, holt sich MANUEL neue Tickets selbst über die Zammad-API ab und schreibt seine Vorschläge als interne Notiz zurück.

```
                 Makerspace (LAN)                              Internet
┌──────────────────────────────────────────────┐      ┌─────────────────────────┐
│ Mini-PC                                      │      │ unseven                 │
│                                              │      │                         │
│  ┌──────────────┐    ┌───────────────────┐   │ HTTPS│  ┌───────────────────┐  │
│  │ Ollama       │◄───┤ manuel-worker     ├───┼──────┼─►│ Zammad API        │  │
│  │ (Vulkan/GPU) │    │ holt Tickets,     │   │      │  └───────────────────┘  │
│  └──────▲───────┘    │ schreibt Notizen  │   │      │                         │
│         │            └───────────────────┘   │      │  ┌───────────────────┐  │
│  ┌──────┴───────┐                            │      │  │ Wiki.js API       │  │
│  │ Open WebUI   │  Prompt-Tests, später Chat │      │  └───────────────────┘  │
│  └──────────────┘                            │      └─────────────────────────┘
│  watchtower · resticker · Uptime-Kuma-Push   │
└──────────────────────────────────────────────┘
```

Grundsätze für den Betrieb:

- **Ein Mensch entscheidet.** MANUEL schreibt nur interne Notizen und Tags. Er antwortet nie selbst an Gäste.
- **Daten bleiben lokal.** Ticketinhalte verlassen nie unsere Systeme. Echte Ticketdaten landen nie in diesem öffentlichen Repo.
- **Alles ist Code.** Die Einrichtung des Hosts liegt als Ansible-Rollen in docker-compose-server. Prompts, Worker, Testsatz-Werkzeuge und Doku liegen hier.

## Offene Entscheidungen

| Frage | Empfehlung | Alternative |
|---|---|---|
| Betriebssystem | uCore Minimal von Universal Blue auf Basis von Fedora CoreOS, weil es den neuesten Kernel mitbringt, sich atomar mit Rollback aktualisiert und zu Bluefin auf unseren Notebooks passt | Fedora Server mit gleichem Kernel, klassischer Paketverwaltung und einfacherer Anbindung an Ansible |
| Inferenz-Server | Ollama im Container mit Vulkan-Backend | llama.cpp mit llama-swap, falls Ollama die GPU schlecht nutzt |
| Anbindung an Zammad | Eigener Worker, der per API abholt und nur ausgehend verbindet | KI-Funktionen von Zammad selbst, die Ollama über NetBird erreichen |
| Vernetzung und Fernzugriff | NetBird mit Regeln, die nur unseven den Zugriff auf Ollama und nur Admins den Zugriff per SSH erlauben | Tailscale, das in uCore schon enthalten ist |
| Zugang zu Open WebUI | Über NetBird für Engagierte mit Konto | Über Traefik auf unseven, das Open WebUI per NetBird erreicht |
| Betrieb von NetBird | Eigene VM nur für Management, Signal und Relay von NetBird, eingerichtet als neuer Host in docker-compose-server. Der Mini-PC und unseven bekommen nur den Client | NetBird Cloud im kostenlosen Tarif |
| Startmodelle | Mixture-of-Experts-Modelle wie Qwen3-30B-A3B und gpt-oss-20b, weil die Speicherbandbreite der Engpass ist | Dichte Modelle bis etwa 14B, große dichte Modelle sind zu langsam |
| Hostname | Neuer Eintrag in der Inventardatei hosts von docker-compose-server | |
| Testinstanz für Zammad | Host unstable aus docker-compose-server | Direkt im Echtsystem mit eigener Testgruppe |

Vor der Entscheidung zur Anbindung prüfen wir, welche KI-Funktionen unsere Zammad-Version mitbringt und ob sie Ollama oder eine OpenAI-kompatible API als Anbieter unterstützt.

## Phasen

### Phase 0 Vorbereitung bis zur Lieferung

- [ ] DSEE über die Variante mit 1 TB statt 2 TB informieren
- [ ] Gerät bestellen und Rechnung vor dem 31.12.2026 bezahlen
- [ ] Offene Entscheidungen oben treffen
- [ ] Zammad-Version und vorhandene KI-Funktionen prüfen
- [ ] Zammad-Benutzer für MANUEL mit API-Token anlegen, beschränkt auf die Gruppe des Repair Cafés
- [ ] Standort, Stromversorgung und LAN-Anschluss im Makerspace klären
- [ ] Zuständige Engagierte für Betrieb, Prompts und Auswertung finden

### Phase 0b NetBird-VM

- [ ] VM mit öffentlicher IP anlegen und DNS-Eintrag setzen
- [ ] VM in die Inventardatei hosts von docker-compose-server aufnehmen und mit prepare_hosts.yaml vorbereiten
- [ ] Rolle netbird mit Management, Signal, Relay und Dashboard anlegen, Traefik übernimmt TLS
- [ ] Firewall für HTTPS und die UDP-Ports von STUN und Relay öffnen
- [ ] Anmeldung für das Dashboard festlegen, mit dem eingebauten Identity Provider oder einem vorhandenen
- [ ] Datenbank des Management-Servers per resticker sichern, weil ohne sie alle Peers und Regeln neu angelegt werden müssen
- [ ] Monitor in Uptime Kuma anlegen, weil ohne Management und Relay keine neuen Verbindungen zustande kommen
- [ ] Client auf unseven installieren und testen, dass die Zammad-Container das NetBird-Netz über den Host erreichen

### Phase 0c Eigenes Image

Die Images werden mit cosign signiert. Ohne den Schlüssel schlägt der Build fehl. cosign ist im Devcontainer enthalten. Die Befehle stammen aus der [README des image-template](https://github.com/ublue-os/image-template/blob/main/README.md).

- [x] Schlüsselpaar ohne Passwort im Wurzelverzeichnis des Repos erzeugen, weil GitHub Actions keinen passwortgeschützten Schlüssel nutzen kann

```bash
COSIGN_PASSWORD="" cosign generate-key-pair
```

- [x] Privaten Schlüssel als Secret `SIGNING_SECRET` im Repo hinterlegen, entweder in den Repo-Einstellungen unter Secrets and variables und Actions oder mit der GitHub CLI

```bash
gh secret set SIGNING_SECRET < cosign.key
```

- [x] Privaten Schlüssel zusätzlich in Vaultwarden ablegen und danach `cosign.key` lokal löschen. `cosign.key` steht in der `.gitignore` und darf nie committet werden
- [x] Öffentlichen Schlüssel committen und pushen

```bash
git add cosign.pub
git commit -m "add cosign.pub"
git push
```

- [x] Im Reiter Actions auf GitHub prüfen, dass der Build erfolgreich durchläuft und das Image unter `ghcr.io/makerspace-gt/manuel` erscheint
- [x] Sichtbarkeit des Pakets in der GitHub Container Registry auf öffentlich stellen

### Phase 1 Grundsystem

- [ ] Gerät inventarisieren, Rechnung und Fotos für den Verwendungsnachweis ablegen
- [ ] Aufkleber mit DSEE-Logo und »Gefördert durch« anbringen
- [ ] BIOS aktualisieren, Neustart nach Stromausfall aktivieren, UMA-Speicher für die GPU einstellen
- [x] Butane-Datei mit Hostname, Zeitzone und automatischem Wechsel auf unser Image in butane/manuel.bu ablegen
- [x] Image so erweitern, dass es unserem cosign-Schlüssel vertraut und signierte Updates prüft
- [ ] Öffentliche SSH-Schlüssel der Admins in butane/manuel.bu eintragen
- [ ] Fedora CoreOS mit der daraus erzeugten Ignition-Datei installieren, siehe butane/README.md
- [ ] Mit rpm-ostree status prüfen, dass das System auf dem signierten Image läuft
- [ ] Automatische Updates und Neustartfenster festlegen, zum Beispiel nachts um 02:00 wie bei unseren anderen Servern
- [ ] Prüfen, ob Python für Ansible vorhanden ist, und es sonst per rpm-ostree nachinstallieren
- [ ] Host in docker-compose-server aufnehmen und watchtower über die vorhandene Rolle ausrollen
- [ ] resticker einrichten und das Volume mit den Modellen vom Backup ausschließen, weil sich Modelle jederzeit neu laden lassen
- [ ] Push-Monitor in Uptime Kuma anlegen
- [ ] NetBird-Client auf dem Mini-PC einrichten, auf uCore per rpm-ostree oder als Container mit Host-Netzwerk
- [ ] Startreihenfolge in systemd festlegen, sodass NetBird vor Docker läuft
- [ ] Zugriffsregeln in NetBird anlegen, sodass unseven nur den Port von Ollama und Admins nur SSH erreichen

### Phase 2 Inferenz

- [ ] GPU-Stack prüfen mit vulkaninfo und Zugriff auf /dev/dri im Container
- [ ] Speicherzuteilung für die GPU über UMA und GTT-Limit testen und dokumentieren
- [ ] Rolle ollama in docker-compose-server anlegen und den Port nur an die NetBird-Adresse binden, weil Ollama keine Anmeldung kennt und Docker die Firewall des Hosts umgeht
- [ ] Prüfen, dass Ollama aus dem LAN und dem Gäste-WLAN des Makerspace nicht erreichbar ist
- [ ] Kontrollieren, dass Modelle wirklich auf der GPU laufen und nicht auf der CPU
- [ ] Leistungsprofil und TDP im BIOS auf Dauerbetrieb einstellen und den Einfluss auf die Geschwindigkeit messen
- [ ] Vulkan und ROCm mit llama-bench vergleichen, weil ROCm die Radeon 890M nur eingeschränkt unterstützt
- [ ] Startmodelle laden und Geschwindigkeit messen, Ergebnisse in docs/benchmarks.md festhalten
- [ ] Optional die NPU mit AMD Lemonade ausprobieren

### Phase 3 Prompts und Tests

- [ ] Rolle open-webui anlegen und Konten für die beteiligten Engagierten einrichten
- [ ] Testsatz aus abgeschlossenen Repair-Café-Tickets exportieren und pseudonymisieren, nur lokal speichern
- [ ] Erste Prompts für Kategorisierung, Erstdiagnose und Lösungsvorschlag in prompts/ ablegen
- [ ] Skript in eval/ schreiben, das Modelle und Prompts gegen den Testsatz laufen lässt
- [ ] Bewertungskriterien festlegen, zum Beispiel richtige Kategorie und Nützlichkeit des Vorschlags aus Sicht der Engagierten
- [ ] Beim Repair Café im November Vorschläge live in Open WebUI testen und Rückmeldungen sammeln

### Phase 4 Anbindung an Zammad

- [ ] manuel-worker in worker/ entwickeln, der neue Tickets der Gruppe Repair Café abholt
- [ ] Vorschläge als interne Notiz schreiben und Kategorie als Tag setzen
- [ ] Gegen die Testinstanz auf unstable testen
- [ ] Rolle manuel-worker in docker-compose-server anlegen und ausrollen
- [ ] Beim Repair Café im Dezember im Echtbetrieb einsetzen und Rückmeldungen zu den Notizen sammeln

### Phase 5 Wiki und Open Repair Alliance

- [ ] Aus erfolgreichen Reparaturen Entwürfe für Reparaturanleitungen erzeugen und als unveröffentlichte Seiten über die Wiki.js-API anlegen
- [ ] Reparaturdaten auf den Open Repair Data Standard abbilden
- [ ] Datenübermittlung an die Open Repair Alliance einrichten

### Phase 6 Abschluss und Veröffentlichung

- [ ] Kennzahlen aus dem Antrag erheben, also Reparaturquote, Reparaturen durch Gäste und neue Engagierte, Rückmeldungen zu Vorschlägen und gemeldete Reparaturen
- [ ] Dokumentation in docs/ vervollständigen, sodass andere Reparaturinitiativen MANUEL nachbauen können
- [ ] Eigenständige compose.yaml als Beispiel für Nachnutzende bereitstellen
- [ ] DSEE-Logo mit »Gefördert durch« in die README aufnehmen
- [ ] Ergebnisse veröffentlichen, zum Beispiel auf unserer Website, im Netzwerk Reparatur-Initiativen der anstiftung und in den sozialen Medien
- [ ] Belege der Veröffentlichung für den Sachbericht sammeln
- [ ] Verwendungsnachweis bis 31.03.2027 im Förderportal einreichen

## Zeitplan

| Zeitraum | Phase |
|---|---|
| bis Lieferung | Phase 0, 0b und 0c |
| November 2026, erste Hälfte | Phase 1 und 2 |
| November 2026 | Phase 3 mit Test beim Repair Café |
| Dezember 2026 | Phase 4 mit Echtbetrieb beim Repair Café |
| Dezember 2026 | Phase 5, so weit wie möglich innerhalb des Bewilligungszeitraums |
| Januar bis März 2027 | Phase 6 |

## Repo-Struktur

```
MANUEL/
├── README.md        Überblick und Förderhinweis
├── PLAN.md          dieser Plan
├── LICENSE          CC0 1.0
├── LICENSES/        Apache 2.0 für die Dateien aus dem image-template
├── Containerfile    eigenes uCore-Image, gebaut von .github/workflows/build.yml
├── build_files/     Skript für Pakete und Dienste im Image
├── system_files/    Dateien, die ins Image kopiert werden
├── butane/          Butane-Datei für die Installation und den Wechsel auf das Image
├── compose.yaml     Beispiel-Stack für Nachnutzende
├── docs/            Einrichtung, Betrieb, Datenschutz, Benchmarks
├── prompts/         Systemprompts für Kategorisierung, Diagnose und Wiki-Entwürfe
├── eval/            Skripte zum Testen, ohne echte Ticketdaten
└── worker/          manuel-worker für die Anbindung an Zammad
```

Geheimnisse wie API-Token gehören nicht hierher. Sie liegen verschlüsselt im Ansible Vault von docker-compose-server.
