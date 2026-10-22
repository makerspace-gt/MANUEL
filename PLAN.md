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

Der Mini-PC steht im Makerspace hinter NAT. Zammad läuft auf unseven.makerspace-gt.de. Beide sind über NetBird verbunden, sodass wir im Makerspace keine Ports öffnen müssen. Zammad nutzt Ollama über seine eingebauten KI-Funktionen als Anbieter. Alles, was Zammad nicht abdeckt, erledigen Workflows in n8n auf dem Mini-PC. n8n holt Daten aus Zammad, Nuudel und dem Wiki, ruft bei Bedarf Ollama auf und schreibt die Ergebnisse zurück.

```
                 Makerspace (LAN)                              Internet
┌──────────────────────────────────────────────┐      ┌─────────────────────────┐
│ Mini-PC                                      │      │ unseven                 │
│                                              │      │                         │
│  ┌──────────────┐        NetBird             │      │  ┌───────────────────┐  │
│  │ Ollama       │◄───────────────────────────┼──────┼──┤ Zammad            │  │
│  │ Sprachmodell │  nur für unseven erlaubt   │      │  │ KI-Funktionen     │  │
│  │ Embeddings   │                            │      │  └─────────▲─────────┘  │
│  └──▲───────▲───┘                            │      │            │            │
│     │       │      ┌───────────────────┐     │ HTTPS│  ┌─────────┴─────────┐  │
│     │       └──────┤ n8n               ├─────┼──────┼─►│ Zammad API        │  │
│     │              │ Workflows         │     │      │  │ Wiki.js API       │  │
│  ┌──┴───────────┐  └───────────────────┘     │      │  └───────────────────┘  │
│  │ Open WebUI   │  Prompt-Tests, später Chat │      └─────────────────────────┘
│  └──────────────┘                            │       Nuudel, Newsletter, ORA
│  watchtower · resticker · Uptime-Kuma-Push   │
└──────────────────────────────────────────────┘
```

Grundsätze für den Betrieb:

- **Ein Mensch entscheidet.** MANUEL schreibt nur interne Notizen und Tags. Er antwortet nie selbst an Gäste.
- **Daten bleiben lokal.** Ticketinhalte verlassen nie unsere Systeme. Echte Ticketdaten landen nie in diesem öffentlichen Repo.
- **Code rechnet, das Modell formuliert.** Zählen, Zuordnen, Termine planen und Daten übertragen erledigen n8n-Workflows nach festen Regeln. Das Sprachmodell liest aus Freitext heraus, schreibt Texte und fasst zusammen.
- **Alles ist Code.** Die Einrichtung des Hosts liegt als Ansible-Rollen in docker-compose-server. Prompts, exportierte n8n-Workflows, Testsatz-Werkzeuge und Doku liegen hier.

## Offene Entscheidungen

| Frage | Empfehlung | Alternative |
|---|---|---|
| Betriebssystem | uCore Minimal von Universal Blue auf Basis von Fedora CoreOS, weil es den neuesten Kernel mitbringt, sich atomar mit Rollback aktualisiert und zu Bluefin auf unseren Notebooks passt | Fedora Server mit gleichem Kernel, klassischer Paketverwaltung und einfacherer Anbindung an Ansible |
| Inferenz-Server | Ollama im Container mit Vulkan-Backend | llama.cpp mit llama-swap, falls Ollama die GPU schlecht nutzt |
| Anbindung an Zammad | KI-Funktionen von Zammad selbst mit [Ollama als Anbieter](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama), das Zammad über NetBird erreicht, ergänzt um n8n-Workflows für alles, was Zammad nicht abdeckt | Eigener Worker in Python statt n8n |
| Automatisierung | n8n selbst gehostet auf dem Mini-PC, nah an Ollama und ohne zusätzliche Last für unseven. n8n steht unter der Sustainable Use License, die den Betrieb für eigene Zwecke erlaubt, aber keine Open-Source-Lizenz ist | n8n auf unseven neben Zammad |
| Anzahl der Modelle | Ein Sprachmodell für alle Aufgaben mit einem eigenen Prompt pro Aufgabe, dazu ein kleines Embedding-Modell. Zwei große Modelle passen kaum gleichzeitig in den Speicher der GPU, und jeder Wechsel kostet Ladezeit | Zusätzlich ein kleines Sprachmodell, falls der Benchmark zeigt, dass einfache Aufgaben zu lange dauern |
| Embedding-Modell | Ein mehrsprachiges Modell wie bge-m3 oder qwen3-embedding für die semantische Suche in Zammad und das Finden ähnlicher Tickets | |
| Vernetzung und Fernzugriff | NetBird mit Regeln, die nur unseven den Zugriff auf Ollama und nur Admins den Zugriff per SSH erlauben | Tailscale, das in uCore schon enthalten ist |
| Zugang zu Open WebUI | Über NetBird für Engagierte mit Konto | Über Traefik auf unseven, das Open WebUI per NetBird erreicht |
| Betrieb von NetBird | Eigene VM nur für Management, Signal und Relay von NetBird, eingerichtet als neuer Host in docker-compose-server. Der Mini-PC und unseven bekommen nur den Client | NetBird Cloud im kostenlosen Tarif |
| Startmodell | [qwen3.6:35b-a3b](https://ollama.com/library/qwen3.6:35b-a3b) mit festem Tag statt latest. Als Mixture-of-Experts-Modell sind pro Token nur etwa 3B Parameter aktiv, was bei begrenzter Speicherbandbreite zählt. Mit 23 bis 24 GB passt es in den Speicher, und es versteht auch Bilder wie Fotos von Typenschildern | Varianten mit MTP oder q8_0 und das dichte qwen3.6:27b als Vergleich im Benchmark |
| Hostname | Neuer Eintrag in der Inventardatei hosts von docker-compose-server | |
| Testinstanz für Zammad | Host unstable aus docker-compose-server | Direkt im Echtsystem mit eigener Testgruppe |

Laut [Zammad-Doku](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama) lässt sich Ollama direkt als KI-Anbieter mit URL und Modell eintragen. Zammad verbindet sich dabei selbst mit Ollama. Die Doku nennt keine Anmeldung oder TLS für Ollama, deshalb schützen wir den Zugang über NetBird. Noch zu prüfen ist, welche KI-Funktionen unsere Zammad-Version bietet und ob sie Kategorisierung, Erstdiagnose und Lösungsvorschläge abdecken.

## Aufgaben

| Aufgabe | Sprachmodell | n8n |
|---|---|---|
| Terminvorschläge | Vorschlagstext formulieren | Anmeldungen der Helfenden in Nuudel lesen, daraus die Zahl paralleler Reparaturen ableiten, regelmäßige Zeitslots von Gästen beibehalten, gleiche Geräte zur gleichen Zeit einplanen |
| Felder in Zammad füllen | Art des Geräts, Defekt, Stromversorgung, Marke, Bezeichnung und Baujahr aus Freitext und Fotos vom Typenschild herauslesen, nach der Reparatur Lösung und Ergebnis | Vorschläge gegen die erlaubten Werte prüfen und eintragen |
| Reparaturansatz schreiben | Aus Defekt und ähnlichen früheren Fällen einen Ansatz zum Mitmachen schreiben | Ähnliche Tickets und Wiki-Anleitungen per Embedding suchen und mitgeben |
| Lösung schreiben | Aus Stichworten der Engagierten einen vollständigen Text schreiben | |
| Statistik | Freitexte zusammenfassen, zum Beispiel welches Werkzeug fehlte und was richtig cool war | Ergebnisse zählen, also erfolgreich, teilweise, vertagt, nicht gelungen und nicht erschienen |
| Newsletter | | Gäste mit dokumentierter Einwilligung für die Neuigkeiten unserer Initiative auf reparatur-initiativen.org anmelden, die Plattform verschickt dann die Bestätigungsmail |
| Open Repair Alliance | Geräte den Kategorien von reparatur-initiativen.org zuordnen | Laufzettel auf reparatur-initiativen.org anlegen, die anstiftung meldet sie an die Open Repair Alliance weiter |
| Tickets zusammenfassen | Zusammenfassung schreiben, eventuell über die KI-Funktionen von Zammad | |
| Tickets verknüpfen | Bestätigen, dass zwei Tickets denselben Fall betreffen | Kandidaten per Embedding suchen und nach Bestätigung verknüpfen |
| Gästedaten eintragen | Vorname, Nachname, E-Mail, Telefon und Mobilnummer aus Mails und Signaturen herauslesen | Vorschlag anzeigen und erst nach Bestätigung durch einen Menschen speichern |

## Anbindung an reparatur-initiativen.org

Die Plattform [reparatur-initiativen.org](https://www.reparatur-initiativen.org) der anstiftung basiert auf dem Open-Source-Projekt [mapped-repair-events](https://github.com/anstiftung/mapped-repair-events) unter GPL-3.0. Es liegt als Submodul in diesem Repo.

- **Die Open Repair Alliance bekommt unsere Daten über die anstiftung.** Im [Datensatz der Open Repair Alliance](https://openrepair.org/open-data/) ist die anstiftung als Datenlieferantin geführt. Ihre Einträge tragen die Kategorien von reparatur-initiativen.org. Reparaturen, die wir dort als Laufzettel melden, landen also ohne eigenen Export bei der Open Repair Alliance.
- **Laufzettel gibt es bisher nur als Webformular.** Ein Laufzettel gehört zu einem Termin und enthält unter anderem Gerät, Kategorie, Marke, Alter, Fehlerbeschreibung und das Ergebnis der Reparatur mit Gründen.
- **Die Neuigkeiten einer Initiative gibt es ebenfalls nur als Webformular.** Nach der Anmeldung verschickt die Plattform eine Mail zur Bestätigung, also ein Double-Opt-in.
- **Die vorhandene API kann nur lesen.** Sie liefert Initiativen und Statistiken und braucht einen API-Token. Schreibende Endpunkte gibt es nicht.

Ideal wären zwei neue Endpunkte, die wir der anstiftung als Beitrag zum Projekt anbieten:

- ein Endpunkt zum Anlegen von Laufzetteln für einen Termin unserer Initiative
- ein Endpunkt zum Anmelden für die Neuigkeiten einer Initiative, der wie das Webformular die Bestätigungsmail auslöst

Die API-Token sind bisher nicht an eine Initiative gebunden. Für schreibende Endpunkte müsste ein Token auf die Initiativen beschränkt sein, die er verwalten darf.

### Stammdaten für die Felder im Ticket

Die Datei [config/sql/init/database.sql](mapped-repair-events/config/sql/init/database.sql) enthält die Wertelisten der Laufzettel. Sie ist die verbindliche Quelle für die Auswahlwerte in Zammad und für das JSON-Schema der Prompts. Wenn wir dieselben Werte und IDs nutzen, lassen sich Tickets ohne Nacharbeit als Laufzettel übertragen.

| Feld in Zammad | Feld im Laufzettel | Werte aus der Datenbank |
|---|---|---|
| Art des Geräts | category_id | Tabelle categories mit 407 Kategorien als Baum mit Oberkategorien wie Haushaltsgeräte oder Fahrrad. Jede Kategorie verweist auf eine Kategorie des Open Repair Data Standard |
| Marke | brand_id | Tabelle brands mit 1.328 Marken. Unbekannte Marken legt der Laufzettel als neue Marke an |
| Bezeichnung | device_name | Freitext |
| Baujahr | device_age | Alter in Jahren, berechnet aus dem Baujahr |
| Stromversorgung | power_supply | mit Netzteil, 230 V, Batterie, Akku, ohne Kabel (Mechanik) |
| Defekt | defect_description | Freitext bis 1.000 Zeichen |
| Lösung | kein eigenes Feld | Wird bei der Übertragung an den Defekt angehängt, zusammen höchstens 1.000 Zeichen. Der Open Repair Data Standard beschreibt Fehler und Lösung ebenfalls in einem Feld |
| Fehler gefunden | defect_found | ja, nein |
| Ergebnis | defect_found_reason | erfolgreich abgeschlossen, vertagt, nicht erfolgt, Abbruch weil das Gerät nicht mehr genutzt werden darf |
| Grund für die Vertagung | repair_postponed_reason | Hilfsmittel oder Zubehör fehlt, Ersatzteilbesorgung durch Besucher, Ersatzteilbesorgung durch Reparateur |
| Grund, warum nicht repariert | no_repair_reason | zum Beispiel hat noch Garantie, Ersatzteil nicht erhältlich, Ersatzteil zu teuer, Gesamtaufwand zu hoch, Öffnung des Gerätes nicht möglich |
| Grund für den Abbruch | device_must_not_be_used_anymore | technisch nicht möglich, nicht betriebssicher |

Die Tabelle form_field_options_extra_infos ordnet jedem Ergebnis den Status und das Reparaturhindernis des Open Repair Data Standard zu. Diese Abbildung übernimmt die anstiftung, wir müssen sie nicht selbst pflegen.

Für unsere eigene Statistik braucht Zammad zusätzlich den Wert nicht erschienen. Den gibt es im Laufzettel nicht, solche Tickets werden nicht übertragen.

Weil die Marken- und Kategorienlisten lang sind, bekommt das Sprachmodell sie nicht vollständig in den Prompt. Es liest Marke und Gerät als Text heraus, und n8n sucht den passenden Eintrag in der Liste. Bei Kategorien hilft das Embedding-Modell, die nächstliegende zu finden.

Die Datei ist ein Stand zur Installation der Plattform. Ob sie mit den Listen auf reparatur-initiativen.org übereinstimmt, klären wir mit der anstiftung. Ein lesender API-Endpunkt für Kategorien und Marken würde den Abgleich vereinfachen.

## Gedanken für die Prompts

- **Ein Prompt pro Aufgabe.** Jede Aufgabe aus der Tabelle bekommt einen eigenen Prompt in prompts/. Er wird in Git versioniert und vor jeder Änderung gegen den Testsatz gemessen.
- **Rolle und Leserschaft klar benennen.** Das Modell unterstützt Ehrenamtliche im Repair Café des Makerspace Gütersloh auf Einstiegs-Level. Die Leser haben wenig Vorkenntnisse. Die Texte sind auf Deutsch, in einfacher Sprache und mit einer festgelegten Anrede.
- **Hilfe zur Selbsthilfe.** Wir machen keine Auftragsarbeit. Ein Reparaturansatz beschreibt deshalb Schritte zum Mitmachen und nennt das nötige Werkzeug und mögliche Ersatzteile. Das liefert nebenbei Daten dazu, welches Werkzeug fehlt.
- **Sicherheit zuerst.** Bei Netzspannung, Akkus, großen Kondensatoren wie in Mikrowellen oder Netzteilen und bei Gasgeräten gehört immer ein Sicherheitshinweis dazu. Im Zweifel verweist das Modell an eine Fachperson.
- **Nichts erfinden.** Weiß das Modell etwas nicht, schreibt es unbekannt statt zu raten. Marke, Bezeichnung und Baujahr übernimmt es nur, wenn sie im Text oder auf einem Foto stehen.
- **Feste Wertelisten und JSON.** Beim Füllen von Feldern antwortet das Modell als JSON nach einem festen Schema. Die erlaubten Werte entsprechen den Auswahlfeldern in Zammad, die Geräteart orientiert sich an den Kategorien von reparatur-initiativen.org, die die anstiftung auf den Open Repair Data Standard abbildet. Ollama kann ein solches Schema als strukturierte Ausgabe erzwingen. n8n prüft die Antwort trotzdem, bevor etwas gespeichert wird.
- **Ticketinhalte sind Daten, keine Anweisungen.** Gäste schreiben frei, und ein Text kann wie eine Anweisung an das Modell aussehen. Der Prompt grenzt den Ticketinhalt klar ab. Das Modell löst selbst keine Aktionen aus, das entscheidet allein n8n nach festen Regeln.
- **Datensparsamkeit.** Jeder Prompt bekommt nur die Teile eines Tickets, die er braucht. Kontaktdaten sieht nur der Prompt zum Eintragen von Gästedaten.
- **Kurz und intern.** Vorschläge sind interne Notizen für Engagierte, knapp und in Stichpunkten. Sie enthalten keine Zusagen an Gäste.
- **Beispiele und Kontext mitgeben.** Gute Beispiele aus dem pseudonymisierten Testsatz zeigen dem Modell, was erwartet wird. Ähnliche frühere Tickets und passende Wiki-Anleitungen, gefunden per Embedding, verbessern Diagnose und Reparaturansatz.
- **Denkmodus und Temperatur je Aufgabe testen.** qwen3.6 kann vor der Antwort nachdenken. Für das Füllen von Feldern ist das meist unnötig und kostet Zeit, für die Diagnose kann es helfen. Für Felder und Statistik gilt eine niedrige Temperatur, für Texte eine etwas höhere.

## Phasen

### Phase 0 Vorbereitung bis zur Lieferung

- [ ] DSEE über die Variante mit 1 TB statt 2 TB informieren
- [ ] Gerät bestellen und Rechnung vor dem 31.12.2026 bezahlen
- [ ] Offene Entscheidungen oben treffen
- [ ] Zammad-Version und vorhandene KI-Funktionen prüfen
- [ ] Zammad-Benutzer für MANUEL mit API-Token anlegen, beschränkt auf die Gruppe des Repair Cafés
- [ ] Felder in Zammad prüfen und anlegen, also Art des Geräts, Defekt, Stromversorgung, Marke, Bezeichnung, Baujahr, Lösung und Ergebnis mit festen Auswahlwerten, die zu den Laufzetteln von reparatur-initiativen.org passen
- [ ] Auswahlwerte und IDs aus database.sql von mapped-repair-events übernehmen, die Kategorien als Baumauswahl
- [ ] Mit der anstiftung klären, ob database.sql dem aktuellen Stand der Kategorien und Marken auf reparatur-initiativen.org entspricht
- [ ] Feld für die Einwilligung in den Newsletter anlegen
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
- [x] Prüfen, ob Python für Ansible vorhanden ist, und es sonst per rpm-ostree nachinstallieren
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
- [ ] Startmodell [qwen3.6:35b-a3b](https://ollama.com/library/qwen3.6:35b-a3b) laden und die Kontextlänge num_ctx auf 16K bis 32K begrenzen
- [ ] UMA und GTT-Limit so einstellen, dass die GPU deutlich mehr als 24 GB nutzen darf
- [ ] Embedding-Modell laden und prüfen, dass es zusammen mit dem Sprachmodell in den Speicher passt
- [ ] Geschwindigkeit messen und mit qwen3.6:35b-a3b-mtp-q4_K_M, qwen3.6:35b-a3b-q8_0 und qwen3.6:27b vergleichen, Ergebnisse in docs/benchmarks.md festhalten
- [ ] Optional die NPU mit AMD Lemonade ausprobieren

### Phase 3 Prompts und Tests

- [ ] Rolle open-webui anlegen und Konten für die beteiligten Engagierten einrichten
- [ ] Testsatz aus abgeschlossenen Repair-Café-Tickets exportieren und pseudonymisieren, nur lokal speichern
- [ ] Prompts für das Füllen der Felder, den Reparaturansatz und die Lösung aus Stichworten nach den Gedanken oben in prompts/ ablegen
- [ ] JSON-Schema für die Felder mit den erlaubten Werten aus Zammad festlegen
- [ ] Skript in eval/ schreiben, das Modelle und Prompts gegen den Testsatz laufen lässt
- [ ] Bewertungskriterien festlegen, zum Beispiel richtige Kategorie und Nützlichkeit des Vorschlags aus Sicht der Engagierten
- [ ] Beim Repair Café im November Vorschläge live in Open WebUI testen und Rückmeldungen sammeln

### Phase 4 Anbindung an Zammad

- [ ] In der Testinstanz unter AI und Providers Ollama mit der NetBird-Adresse des Mini-PCs und qwen3.6:35b-a3b als Modell eintragen, siehe [Zammad-Doku](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama)
- [ ] Prüfen, dass der Status des Anbieters nach der ersten Anfrage grün ist
- [ ] KI-Funktionen von Zammad mit Repair-Café-Tickets testen
- [ ] Rolle n8n in docker-compose-server anlegen, n8n nur über NetBird erreichbar machen und seine Daten per resticker sichern
- [ ] Workflow zum Füllen der Felder bauen, der Vorschläge als interne Notiz schreibt und erst nach Bestätigung in die Felder überträgt
- [ ] Workflow für den Reparaturansatz bauen, der ähnliche Tickets und Wiki-Anleitungen per Embedding mitgibt
- [ ] Workflow für Gästedaten bauen, der Kontaktdaten nur als Vorschlag zur Bestätigung anzeigt
- [ ] Workflows als JSON nach n8n/ exportieren
- [ ] Gegen die Testinstanz auf unstable testen
- [ ] Ollama in Zammad auf unseven als Anbieter eintragen und die Workflows auf das Echtsystem umstellen
- [ ] Beim Repair Café im Dezember im Echtbetrieb einsetzen und Rückmeldungen zu den Notizen sammeln

### Phase 5 Weitere Workflows

- [ ] Workflow für Statistik bauen, der Ergebnisse zählt und Freitexte zu fehlendem Werkzeug und Highlights zusammenfasst
- [ ] Aus erfolgreichen Reparaturen Entwürfe für Reparaturanleitungen erzeugen und als unveröffentlichte Seiten über die Wiki.js-API anlegen
- [ ] Mit der anstiftung per Issue in mapped-repair-events klären, ob sie schreibende Endpunkte für Laufzettel und Neuigkeiten annehmen würde
- [ ] Felder in Zammad auf die Felder der Laufzettel abbilden, damit die Daten ohne Nacharbeit übertragbar sind
- [ ] Endpunkte in mapped-repair-events umsetzen und als Pull Request einreichen
- [ ] Workflow bauen, der nach dem Repair Café die Laufzettel auf reparatur-initiativen.org anlegt, bis dahin Laufzettel von Hand übertragen
- [ ] Workflow für Terminvorschläge bauen, der Anmeldungen in Nuudel auswertet
- [ ] Workflow zum Zusammenfassen und Verknüpfen von Tickets bauen, falls die KI-Funktionen von Zammad das nicht abdecken
- [ ] Workflow für den Newsletter bauen, der nur Gäste mit Einwilligung für die Neuigkeiten unserer Initiative auf reparatur-initiativen.org anmeldet

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
├── n8n/             exportierte n8n-Workflows
└── mapped-repair-events/  Submodul mit der Plattform der anstiftung, GPL-3.0
```

Geheimnisse wie API-Token gehören nicht hierher. Sie liegen verschlüsselt im Ansible Vault von docker-compose-server.
