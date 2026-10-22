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

Die gesamte Infrastruktur wird neu aufgesetzt, bestehende VMs übernehmen wir nicht. Der Mini-PC steht im Makerspace hinter NAT. Zammad läuft auf der Helpdesk-VM. Beide sind über NetBird verbunden, sodass wir im Makerspace keine Ports öffnen müssen. Zammad nutzt Ollama als Anbieter für seine eingebauten KI-Funktionen. KI-Agenten in Zammad füllen die Felder im Ticket und schreiben interne Notizen. Die Wissensdatenbank von Zammad sammelt Reparaturanleitungen und zeigt passende Artikel direkt am Ticket an. n8n auf der Helpdesk-VM übernimmt nur, was außerhalb von Zammad liegt, also Nuudel, reparatur-initiativen.org und die Statistik. Der Mini-PC bleibt damit ein reiner Rechenknecht für Ollama und Open WebUI.

```
                 Makerspace (LAN)                              Internet
┌──────────────────────────────────────────────┐      ┌─────────────────────────┐
│ Mini-PC                                      │      │ Helpdesk-VM             │
│                                              │      │                         │
│  ┌──────────────┐        NetBird             │      │  ┌───────────────────┐  │
│  │ Ollama       │◄───────────────────────────┼──────┼──┤ Zammad            │  │
│  │ Sprachmodell │  nur für Helpdesk erlaubt  │      │  │ KI-Agenten        │  │
│  │ Embeddings   │◄───────────────────────────┼──────┼─┐└─────────▲─────────┘  │
│  └──────▲───────┘                            │      │ │          │ Webhooks   │
│         │                                    │      │ │┌─────────┴─────────┐  │
│  ┌──────┴───────┐                            │      │ └┤ n8n Workflows     │  │
│  │ Open WebUI   │  Prompt-Tests, später Chat │      │  └───────────────────┘  │
│  └──────────────┘                            │      │  Wissensdatenbank     │
│                                              │      └─────────────────────────┘
│  Arcane-Agent · resticker · Uptime-Kuma-Push │
│  Beszel-Agent                                │       Nuudel, Newsletter und
└──────────────────────────────────────────────┘       reparatur-initiativen.org
```

Grundsätze für den Betrieb:

- **Ein Mensch entscheidet.** MANUEL füllt Felder vor, schreibt interne Notizen und schlägt Texte vor. Die Engagierten prüfen und korrigieren die Felder während des Termins. Das ist zugleich die Qualitätskontrolle, die die Datenpotenzialanalyse empfiehlt. MANUEL antwortet nie selbst an Gäste und speichert Kontaktdaten nicht ohne Bestätigung. KI-Agenten in Zammad bekommen deshalb nie die Aktion zum Versand von E-Mails oder SMS.
- **Weboberflächen nur über NetBird.** Alle Weboberflächen sind am Ende nur über NetBird erreichbar. SSH mit Schlüssel bleibt direkt möglich und ist damit auch der Notzugang, falls NetBird ausfällt. Ausnahmen stehen im Abschnitt zur Erreichbarkeit.
- **Daten bleiben lokal.** Ticketinhalte verlassen nie unsere Systeme. Echte Ticketdaten landen nie in diesem öffentlichen Repo.
- **Code rechnet, das Modell formuliert.** Zählen, Zuordnen, Termine planen und Daten übertragen erledigen Zammad-Trigger und n8n-Workflows nach festen Regeln. Das Sprachmodell liest aus Freitext heraus, schreibt Texte und fasst zusammen.
- **Alles ist Code.** Die Einrichtung des Hosts liegt als Ansible-Rollen in docker-compose-server. Prompts, exportierte n8n-Workflows, Testsatz-Werkzeuge und Doku liegen hier. Die Konfiguration der KI-Agenten in Zammad, also Regeln und Beschreibungen der Auswahlwerte, legen wir als Kopie in prompts/ ab.

## Offene Entscheidungen

| Frage | Empfehlung | Alternative |
|---|---|---|
| Betriebssystem | [uCore Minimal](https://github.com/ublue-os/ucore) von Universal Blue auf Basis von [Fedora CoreOS](https://docs.fedoraproject.org/en-US/fedora-coreos/), weil es den neuesten Kernel mitbringt, der laut [Phoronix](https://www.phoronix.com/review/amd-perfopt/3) die LLM-Leistung von Radeon-iGPUs deutlich verbessert, sich atomar mit Rollback aktualisiert und zu Bluefin auf unseren Notebooks passt | Fedora Server mit gleichem Kernel, klassischer Paketverwaltung und einfacherer Anbindung an Ansible |
| Inferenz-Server | [Ollama](https://docs.ollama.com/) im Container. Vulkan und ROCm vergleichen wir im Benchmark, denn die [Ollama-Doku zu GPUs](https://github.com/ollama/ollama/blob/main/docs/gpu.mdx) führt den gfx1150 des HX 370 inzwischen auch für ROCm v7 | [llama.cpp](https://github.com/ggml-org/llama.cpp) mit [llama-swap](https://github.com/mostlygeek/llama-swap), falls Ollama die GPU schlecht nutzt |
| Anbindung an Zammad | [KI-Agenten](https://admin-docs.zammad.org/en/latest/ai/ai-agents.html) und KI-Funktionen von Zammad mit [Ollama als Anbieter](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama), das Zammad über NetBird erreicht. Zammad füllt die Felder selbst, n8n übernimmt nur Aufgaben außerhalb von Zammad | n8n-Workflows auch für die Felder, falls die Agenten nicht reichen |
| Automatisierung | [n8n selbst gehostet](https://docs.n8n.io/hosting/) auf der Helpdesk-VM neben Zammad. Dort liegen die Zugangsdaten im Rechenzentrum statt in der offenen Werkstatt, Workflows ohne Sprachmodell laufen auch bei Neustart oder Ausfall des Mini-PCs, und Traefik, resticker und Uptime Kuma sind schon eingerichtet. n8n steht unter der [Sustainable Use License](https://github.com/n8n-io/n8n/blob/master/LICENSE.md), die den Betrieb für eigene Zwecke erlaubt, aber keine Open-Source-Lizenz ist | n8n auf dem Mini-PC direkt neben Ollama |
| Anzahl der Modelle | Ein Sprachmodell für alle Aufgaben mit einem eigenen Prompt pro Aufgabe, dazu ein kleines Embedding-Modell. Zwei große Modelle passen kaum gleichzeitig in den Speicher der GPU, und jeder Wechsel kostet Ladezeit | Zusätzlich ein kleines Sprachmodell, falls der Benchmark zeigt, dass einfache Aufgaben zu lange dauern |
| Embedding-Modell | [bge-m3](https://ollama.com/library/bge-m3), das Zammad für Ollama [selbst empfiehlt](https://github.com/zammad/zammad/blob/develop/lib/ai/provider/ollama.rb). Es ist mehrsprachig und dient der semantischen Suche in der Wissensdatenbank | [qwen3-embedding](https://ollama.com/library/qwen3-embedding) |
| Reparaturanleitungen | [Wissensdatenbank von Zammad](https://admin-docs.zammad.org/en/latest/manage/knowledge-base.html). Zammad erzeugt Artikel aus einem Ticket und zeigt per Embedding [passende Artikel am Ticket](https://github.com/zammad/zammad/blob/develop/app/services/service/ticket/ai/related_knowledge_base_answers.rb) an | Wiki.js mit eigenem Embedding-Workflow in n8n |
| Termin im Ticket | Eigenes Datumsfeld Termin über die [Objektverwaltung von Zammad](https://admin-docs.zammad.org/en/latest/system/objects.html) statt der Wartezeit des Tickets. Dann entfällt unsere angepasste Kopie der ticket.rb, siehe Abschnitt dazu unten | Kleiner Patch als Initializer statt Kopie der ganzen Datei |
| Vernetzung und Fernzugriff | [NetBird](https://docs.netbird.io/) mit Regeln, die nur der Helpdesk-VM den Zugriff auf Ollama und nur Admins den Zugriff per SSH erlauben | Tailscale, das in uCore schon enthalten ist |
| Zugang zu Open WebUI | [Open WebUI](https://docs.openwebui.com/) über NetBird für Engagierte mit Konto | Über Traefik auf der Helpdesk-VM, die Open WebUI per NetBird erreicht |
| Betrieb von NetBird | Management, Signal und Relay von NetBird auf der Zugangs-VM nach der [Anleitung zum Selbsthosten](https://docs.netbird.io/selfhosted/selfhosted-quickstart). Alle übrigen VMs und der Mini-PC bekommen nur den Client | NetBird Cloud im kostenlosen Tarif |
| Startmodell | [qwen3.6:35b-a3b](https://ollama.com/library/qwen3.6:35b-a3b) mit festem Tag statt latest. Als Mixture-of-Experts-Modell sind pro Token nur etwa 3B Parameter aktiv, was bei begrenzter Speicherbandbreite zählt. Mit 23 bis 24 GB passt es in den Speicher, und es versteht auch Bilder wie Fotos von Typenschildern | Varianten mit MTP oder q8_0 und das dichte qwen3.6:27b als Vergleich im Benchmark |
| Updates der Container | [Arcane](https://getarcane.app) statt watchtower auf allen Hosts. Ein zentraler Arcane-Server verwaltet die Docker-Hosts über Agenten, die sich [ausgehend verbinden](https://github.com/getarcaneapp/arcane/tree/main/docker/examples) und keine offenen Ports brauchen. Arcane erkennt neue Images, aktualisiert nach Zeitplan, meldet per Signal und kann sich an authentik anmelden. Es steht unter BSD-3-Clause. Der Arcane-Server steuert Docker auf allen Hosts und gehört deshalb auf eine gehärtete VM, erreichbar nur über NetBird. Die Compose-Dateien bleiben in Ansible, die GitOps-Funktion von Arcane nutzen wir nicht, damit nicht zwei Werkzeuge dieselben Dateien schreiben. Zammad aktualisieren wir nicht automatisch, sondern nach Hinweis von Arcane von Hand, weil Datenbankmigrationen und unsere Anpassungen geprüft werden müssen | watchtower wie bisher |
| Überwachung der Ressourcen | [Beszel](https://beszel.dev) mit einem Hub neben Uptime Kuma auf der Monitoring-VM und einem Agenten auf jedem Host. Uptime Kuma meldet, ob Dienste erreichbar sind, Beszel meldet volle Platten, knappen Speicher, hohe Last, Temperaturen und SMART-Werte. Die Agenten können sich per WebSocket ausgehend mit dem Hub verbinden. Auf dem Mini-PC liest Beszel auch die [AMD-GPU](https://beszel.dev/guide/gpu) aus. Benachrichtigungen gehen über Shoutrrr, also auch per Signal, und die Anmeldung kann über [OAuth mit authentik](https://beszel.dev/guide/oauth) laufen. Beszel steht unter MIT | Nur Uptime Kuma wie bisher |
| Hostname | Neuer Eintrag in der Inventardatei hosts von docker-compose-server | |
| Testinstanz für Zammad | Test-VM, die OpenTofu nur bei Bedarf anlegt | Direkt im Echtsystem mit eigener Testgruppe |
| Wiki | Wiki.js nicht neu aufsetzen. Reparaturanleitungen kommen in die Wissensdatenbank von Zammad, Vereinswissen wie Maschinen, Kenntnisse und Abläufe in [Wiki-Beiträge in Discourse](https://meta.discourse.org/t/what-is-a-wiki-post/30801), wo der KI-Bot sie für Antworten nutzt. Doku zur IT liegt als Markdown in den Repos in Forgejo neben dem Code. Für den Umzug exportiert Wiki.js alle Seiten per [Git-Speicher](https://docs.requarks.io/storage/git) als Markdown. [Wiki.js](https://github.com/Requarks/wiki) wird aktiv entwickelt, Version 3 ist aber seit Jahren im Beta-Stadium | Wiki.js 2 neu aufsetzen und später auf Version 3 umsteigen |

Laut [Zammad-Doku](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama) lässt sich Ollama direkt als KI-Anbieter mit URL und Modell eintragen. Zammad verbindet sich dabei selbst mit Ollama. Die Doku nennt keine Anmeldung oder TLS für Ollama, deshalb schützen wir den Zugang über NetBird.

Laut [Quellcode des Ollama-Anbieters](https://github.com/zammad/zammad/blob/develop/lib/ai/provider/ollama.rb) ruft Zammad Ollama über /api/generate auf, schaltet das Nachdenken ab, setzt die Temperatur auf 0 und verlangt bei Bedarf JSON. Eine Kontextlänge schickt Zammad nicht mit, die muss Ollama selbst vorgeben. Die [Agententypen](https://github.com/zammad/zammad/tree/develop/app/models/ai/agent/type) umfassen unter anderem Ticket Categorizer für Auswahlfelder auch als Baum, Ticket Text Extractor für Text, Zahlen und Auswahlwerte, Ticket Tagger und Custom AI Agent. Ein Agent wird über einen normalen Trigger ausgelöst und wendet sein Ergebnis mit denselben Aktionen wie ein Trigger an, also Feldänderungen, interne Notizen oder Webhooks. Ob unsere Zammad-Version all das schon bietet, prüfen wir in Phase 0.

## Erreichbarkeit

Am Ende sind alle Weboberflächen nur über NetBird erreichbar. Das verkleinert die Angriffsfläche deutlich, weil Zammad, n8n, Arcane, Vaultwarden und die übrigen Dienste nicht mehr aus dem Internet ansprechbar sind. SSH mit Schlüssel bleibt direkt erreichbar.

Einige Dienste müssen trotzdem öffentlich bleiben, weil sie vor oder außerhalb von NetBird gebraucht werden:

- **NetBird selbst.** Management, Signal und Relay müssen erreichbar sein, damit sich Clients überhaupt verbinden können.
- **authentik.** Die Anmeldung bei NetBird läuft über authentik, bevor der Tunnel steht. Nur die Seiten für Anmeldung und OpenID Connect müssen öffentlich sein, die Verwaltung kann hinter NetBird.
- **Was Gäste nutzen.** Gäste haben kein NetBird. Zu klären ist, ob wir ein Webformular von Zammad auf der Webseite, das Kundenportal oder eine öffentliche Wissensdatenbank mit Reparaturanleitungen anbieten. Das Forum auf Discourse und der Kalender aus Nextcloud, der auf der Webseite erscheint, sind ebenfalls öffentlich. Für diese Teile veröffentlichen wir nur die nötigen Pfade.

Damit das funktioniert, braucht es drei Änderungen:

- **Zertifikate per DNS-Challenge.** Traefik holt Zertifikate bisher über HTTP und braucht dafür öffentliche Erreichbarkeit. Mit der [DNS-Challenge](https://doc.traefik.io/traefik/https/acme/) geht das auch für interne Dienste. Unser DNS-Anbieter lima-city wird vom zugrunde liegenden ACME-Werkzeug lego [unterstützt](https://go-acme.github.io/lego/dns/limacity/). Dafür brauchen wir einen API-Schlüssel von lima-city im Ansible Vault.
- **Namen auflösen.** Die Namen der Dienste zeigen auf die NetBird-Adressen der Hosts. Das geht über die [DNS-Verwaltung von NetBird](https://docs.netbird.io/manage/dns) oder über öffentliche Einträge mit den NetBird-Adressen.
- **Zugriff nach Gruppen.** Die [Zugriffsregeln von NetBird](https://docs.netbird.io/manage/access-control) legen fest, welche Gruppe welchen Dienst erreicht, zum Beispiel Admins alles und Engagierte des Repair Cafés nur Zammad und Open WebUI. Die Gruppen kommen aus authentik.

Engagierte brauchen dafür den NetBird-Client auf ihrem Gerät. Für das Repair Café in der Stadtbibliothek planen wir deshalb eine kurze Anleitung und Zeit zum Einrichten ein. Für einen Ausfall von NetBird bleibt der Weg über SSH mit Portweiterleitung, damit Admins weiter an Vaultwarden und die übrigen Dienste kommen.

## Angepasste ticket.rb

Die bisherige Rolle zammad in docker-compose-server ersetzt die komplette [ticket.rb](https://github.com/makerspace-gt/docker-compose-server/blob/main/roles/zammad/files/app/models/ticket.rb) von Zammad. Die Datei ist eine Kopie aus Zammad 7.1.0 bis 7.1.2 mit rund 770 Zeilen. Gegenüber der [Originaldatei](https://github.com/zammad/zammad/blob/7.1.2/app/models/ticket.rb) ist nur eine Zeile geändert. In der Methode reset_pending_time ist `self.pending_time = nil` auskommentiert. Damit bleibt die Wartezeit eines Tickets erhalten, wenn es den Status warten verlässt. Vermutlich nutzen wir sie als Termin im Repair Café.

Das Problem ist die Kopie, nicht die Änderung. Bei jedem Update von Zammad muss die ganze Datei neu abgeglichen werden. Die [aktuelle ticket.rb](https://github.com/zammad/zammad/blob/develop/app/models/ticket.rb) weicht schon an mehreren Stellen ab, zum Beispiel bei Rechten, Live-Nutzern und dem Zusammenführen von Tickets. Eine veraltete Kopie kann neue Funktionen wie die KI-Agenten still stören.

Beim Neuaufbau übernehmen wir die Kopie nicht. Es gibt zwei bessere Lösungen:

1. **Eigenes Datumsfeld Termin.** Ein Feld vom Typ Datum und Uhrzeit über die [Objektverwaltung](https://admin-docs.zammad.org/en/latest/system/objects.html) braucht gar keinen Patch. Übersichten, Trigger und n8n können es nutzen, und die Terminvorschläge schreiben direkt hinein. Die Wartezeit funktioniert dann wieder wie vorgesehen. Beim Umzug der Daten übernehmen wir bestehende Wartezeiten einmalig per Rails-Konsole in das neue Feld. Das empfehlen wir.
2. **Nur die eine Methode überschreiben.** Statt der ganzen Datei binden wir einen kleinen Initializer in die Container zammad-railsserver und zammad-scheduler ein. Er muss nur angepasst werden, wenn Zammad die Methode umbenennt.

```ruby
# config/initializers/zz_keep_pending_time.rb
# Keep the pending time when a ticket leaves a pending state
Rails.application.config.to_prepare do
  Ticket.class_eval do
    private

    def reset_pending_time
      true
    end
  end
end
```

## Aufgaben

| Aufgabe | Zammad | n8n |
|---|---|---|
| Felder füllen | Ticket Categorizer für die Art des Geräts, Ticket Text Extractor für Defekt, Stromversorgung, Marke, Bezeichnung und Baujahr, Texterkennung für Fotos vom Typenschild | |
| Reparaturansatz schreiben | Custom AI Agent schreibt eine interne Notiz, passende Artikel aus der Wissensdatenbank zeigt Zammad am Ticket an | |
| Lösung schreiben | Textwerkzeug macht aus Stichworten der Engagierten einen vollständigen Text | |
| Reparaturanleitungen | Artikel in der Wissensdatenbank aus einem erfolgreichen Ticket erzeugen und von Engagierten prüfen lassen | |
| Tickets zusammenfassen | Eingebaute Zusammenfassung | |
| Tickets verknüpfen | Verknüpfen von Hand, unterstützt durch passende Artikel und Zusammenfassung | Nur falls das nicht reicht, Kandidaten per Embedding suchen |
| Gästedaten eintragen | Custom AI Agent schreibt erkannte Kontaktdaten als interne Notiz, ein Mensch übernimmt sie | |
| Terminvorschläge | Datumsfeld Termin im Ticket | Anmeldungen der Helfenden in [Nuudel](https://nuudel.digitalcourage.de/) lesen, daraus die Zahl paralleler Reparaturen ableiten, regelmäßige Zeitslots von Gästen beibehalten, gleiche Geräte zur gleichen Zeit einplanen und den Vorschlagstext von Ollama formulieren lassen |
| Statistik | Ergebnisfelder und Berichte | Ergebnisse zählen, also erfolgreich, teilweise, vertagt, nicht gelungen und nicht erschienen, und Freitexte zu fehlendem Werkzeug und Highlights von Ollama zusammenfassen lassen |
| Open Repair Alliance | Felder mit den Werten der Laufzettel | Laufzettel auf reparatur-initiativen.org anlegen, die anstiftung meldet sie an die Open Repair Alliance weiter |
| Newsletter | Feld für die Einwilligung | Gäste mit dokumentierter Einwilligung für die Neuigkeiten unserer Initiative auf reparatur-initiativen.org anmelden, die Plattform verschickt dann die Bestätigungsmail |

Zammad löst n8n über die Trigger-Aktion Webhook aus, zum Beispiel wenn ein Ticket nach dem Termin geschlossen wird.

## Anbindung an reparatur-initiativen.org

Die Plattform [reparatur-initiativen.org](https://www.reparatur-initiativen.org) der anstiftung basiert auf dem Open-Source-Projekt [mapped-repair-events](https://github.com/anstiftung/mapped-repair-events) unter GPL-3.0. Es liegt als Submodul in diesem Repo.

- **Die Open Repair Alliance bekommt unsere Daten über die anstiftung.** Im [Datensatz der Open Repair Alliance](https://openrepair.org/open-data/) ist die anstiftung als Datenlieferantin geführt. Den Datensatz laden wir bei Bedarf dort herunter. Er steht unter CC BY-SA 4.0 und ist mit über 100 MB zu groß für das Repo, deshalb steht er in der `.gitignore`. Ihre Einträge tragen die Kategorien von reparatur-initiativen.org. Reparaturen, die wir dort als Laufzettel melden, landen also ohne eigenen Export bei der Open Repair Alliance.
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

Die Kategorien legen wir in Zammad als Baumauswahl an, die der Ticket Categorizer direkt füllt. Mit 407 Kategorien wird sein Prompt lang, deshalb muss die Kontextlänge in Ollama groß genug sein. Reicht das nicht, beschränken wir den Agenten auf die Kategorien, die im Repair Café tatsächlich vorkommen. Die 1.328 Marken passen nicht sinnvoll in eine Auswahl. Die Marke bleibt deshalb ein Textfeld, das der Ticket Text Extractor füllt. Beim Anlegen des Laufzettels sucht n8n den passenden Eintrag in der Markenliste.

Die Datei ist ein Stand zur Installation der Plattform. Ob sie mit den Listen auf reparatur-initiativen.org übereinstimmt, klären wir mit der anstiftung. Ein lesender API-Endpunkt für Kategorien und Marken würde den Abgleich vereinfachen.

### Erkenntnisse aus der Datenpotenzialanalyse

Die Hausarbeit [Datenpotenzialanalyse des Repair Café Gütersloh](https://codeberg.org/igami/datenpotenzialanalyse-repairc-cafe-gt) aus dem Wintersemester 2021/22 hat unsere Laufzettel ausgewertet. Sie liegt als Submodul in diesem Repo und steht unter CC BY 4.0. Für MANUEL sind vor allem diese Punkte aus Kapitel 4.2 und 5 wichtig:

- **Zusätzliche Felder.** Bisher wird nicht erfasst, wer repariert hat, also der Gast selbst oder mit Hilfe, ob eine Reparatur wieder aufgenommen wurde und wie lange sie gedauert hat. Wer repariert hat, brauchen wir für die Erfolgskennzahl aus dem Antrag zu Reparaturen durch Gäste und neue Engagierte.
- **Werbung durch.** Ein Feld, wie Gäste vom Repair Café erfahren haben, zeigt, welche Werbung wirkt.
- **Datensparsamkeit.** Eine Adresse der Gäste ist nie nötig. Eine Kontaktmöglichkeit per E-Mail oder Telefon reicht, wenn ein neuer Termin nötig ist oder ein Newsletter gewünscht wird. Falls das Geschlecht abgefragt wird, dann mit mehr als zwei Möglichkeiten.
- **Qualitätskontrolle.** Die Laufzettel wurden oft unvollständig oder falsch ausgefüllt. Wenn die Daten schon während des Termins erfasst werden, lassen sich Lücken sofort nachfragen. Genau dabei kann MANUEL mit Vorschlägen für die Felder helfen.
- **Wiederkehrende Fehler.** Die Zahl unterschiedlicher Fehler ließ sich stark eingrenzen. Für häufige Fehler lohnen sich Reparaturanleitungen in der Wissensdatenbank, damit Gäste selbst reparieren können.
- **Austausch mit dem Netzwerk.** Die Hausarbeit empfiehlt, die Erkenntnisse zur Kategorisierung der Fehler mit dem Netzwerk Reparatur-Initiativen zu besprechen. Das passt zu den geplanten Endpunkten in mapped-repair-events.

## Gedanken für die Prompts

- **Ein Prompt pro Aufgabe.** Jede Aufgabe aus der Tabelle bekommt einen eigenen Prompt. Bei den Agenten in Zammad sind das Rolle, Anweisung, Extraktionsregeln und Beschreibungen der Auswahlwerte. Eine Kopie liegt in prompts/, wird in Git versioniert und vor jeder Änderung gegen den Testsatz gemessen.
- **Rolle und Leserschaft klar benennen.** Das Modell unterstützt Ehrenamtliche im Repair Café des Makerspace Gütersloh auf Einstiegs-Level. Die Leser haben wenig Vorkenntnisse. Die Texte sind auf Deutsch, in einfacher Sprache und mit einer festgelegten Anrede.
- **Hilfe zur Selbsthilfe.** Wir machen keine Auftragsarbeit. Ein Reparaturansatz beschreibt deshalb Schritte zum Mitmachen und nennt das nötige Werkzeug und mögliche Ersatzteile. Das liefert nebenbei Daten dazu, welches Werkzeug fehlt.
- **Sicherheit zuerst.** Bei Netzspannung, Akkus, großen Kondensatoren wie in Mikrowellen oder Netzteilen und bei Gasgeräten gehört immer ein Sicherheitshinweis dazu. Im Zweifel verweist das Modell an eine Fachperson.
- **Nichts erfinden.** Weiß das Modell etwas nicht, schreibt es unbekannt statt zu raten. Marke, Bezeichnung und Baujahr übernimmt es nur, wenn sie im Text oder auf einem Foto stehen.
- **Feste Wertelisten.** Die erlaubten Werte entsprechen den Auswahlfeldern in Zammad, die Geräteart orientiert sich an den Kategorien von reparatur-initiativen.org, die die anstiftung auf den Open Repair Data Standard abbildet. Die Agenten in Zammad bekommen die Werte samt Beschreibungen aus den Feldern. Gute Beschreibungen der Werte sind deshalb Teil des Prompts. Ruft n8n Ollama selbst auf, erzwingt es das Format als [strukturierte Ausgabe](https://ollama.com/blog/structured-outputs) und prüft die Antwort, bevor etwas gespeichert wird.
- **Ticketinhalte sind Daten, keine Anweisungen.** Gäste schreiben frei, und ein Text kann wie eine Anweisung an das Modell aussehen. Der Prompt grenzt den Ticketinhalt klar ab. Das Modell löst selbst keine Aktionen aus. Welche Aktionen ein Agent ausführen darf, legen wir in Zammad fest, bei n8n entscheiden feste Regeln.
- **Datensparsamkeit.** Jeder Prompt bekommt nur die Teile eines Tickets, die er braucht. Kontaktdaten sieht nur der Prompt zum Eintragen von Gästedaten.
- **Kurz und intern.** Vorschläge sind interne Notizen für Engagierte, knapp und in Stichpunkten. Sie enthalten keine Zusagen an Gäste.
- **Beispiele und Kontext mitgeben.** Gute Beispiele aus dem pseudonymisierten Testsatz zeigen dem Modell, was erwartet wird. Passende Artikel aus der Wissensdatenbank, gefunden per Embedding, verbessern Diagnose und Reparaturansatz.
- **Denkmodus und Temperatur.** Zammad schaltet das Nachdenken ab und setzt die Temperatur auf 0. Das passt zum Füllen von Feldern. Nur bei Aufrufen aus n8n können wir beides je Aufgabe wählen, für Texte zum Beispiel eine etwas höhere Temperatur.

## Phasen

### Phase 0 Vorbereitung bis zur Lieferung

- [ ] DSEE über die Variante mit 1 TB statt 2 TB informieren
- [ ] Gerät bestellen und Rechnung vor dem 31.12.2026 bezahlen
- [ ] Offene Entscheidungen oben treffen
- [ ] Zammad-Version auf helpdesk prüfen. Ollama-Anbieter, Ticket Categorizer, Ticket Text Extractor und Embeddings für die Wissensdatenbank müssen vorhanden sein, sonst vorher auf die passende Version aktualisieren
- [ ] Termin als eigenes Datumsfeld anlegen und beim Umzug bestehende Wartezeiten übernehmen, die angepasste ticket.rb kommt nicht mit, siehe Abschnitt zur ticket.rb
- [ ] Zammad-Benutzer für MANUEL mit API-Token anlegen, beschränkt auf die Gruppe des Repair Cafés
- [ ] Felder in Zammad prüfen und anlegen, also Art des Geräts, Defekt, Stromversorgung, Marke, Bezeichnung, Baujahr, Lösung und Ergebnis mit festen Auswahlwerten, die zu den Laufzetteln von reparatur-initiativen.org passen
- [ ] Auswahlwerte und IDs aus database.sql von mapped-repair-events übernehmen, die Kategorien als Baumauswahl, die Marke als Textfeld
- [ ] Für jeden Auswahlwert eine kurze Beschreibung hinterlegen, weil die Agenten sie als Kontext nutzen
- [ ] Zusätzliche Felder aus der Datenpotenzialanalyse anlegen, also wer repariert hat, Dauer der Reparatur, wieder aufgenommen und Werbung durch
- [ ] Mit der anstiftung klären, ob database.sql dem aktuellen Stand der Kategorien und Marken auf reparatur-initiativen.org entspricht
- [ ] Feld für die Einwilligung in den Newsletter anlegen
- [ ] Standort, Stromversorgung und LAN-Anschluss im Makerspace klären
- [ ] Zuständige Engagierte für Betrieb, Prompts und Auswertung finden

### Phase 0b Zugangs-VM

- [ ] Zugangs-VM mit öffentlicher IP anlegen, später per OpenTofu, und DNS-Eintrag setzen
- [ ] Grundsystem per Ansible einrichten
- [ ] authentik einrichten, nach der [Installationsanleitung](https://github.com/goauthentik/authentik/blob/main/website/docs/install-config/install/docker-compose.mdx) mit PostgreSQL, Server und Worker
- [ ] Vaultwarden auf die Zugangs-VM umziehen, ohne Anmeldung über authentik, damit es auch bei einem Ausfall von authentik erreichbar bleibt
- [ ] Rolle netbird mit Management, Signal, Relay und Dashboard anlegen, Traefik übernimmt TLS. Als Vorlage dienen [getting-started.sh](https://github.com/netbirdio/netbird/blob/main/infrastructure_files/getting-started.sh) und die Compose-Vorlage für Traefik im Submodul netbird
- [ ] Firewall für HTTPS und die UDP-Ports von STUN und Relay öffnen
- [ ] Anmeldung für das Dashboard [an authentik anbinden](https://docs.netbird.io/selfhosted/identity-providers/authentik)
- [ ] Datenbank des Management-Servers per resticker sichern, weil ohne sie alle Peers und Regeln neu angelegt werden müssen
- [ ] Monitor in Uptime Kuma anlegen, weil ohne Management und Relay keine neuen Verbindungen zustande kommen
- [ ] Client auf der Helpdesk-VM installieren und testen, dass die Zammad-Container das NetBird-Netz über den Host erreichen
- [ ] Traefik auf DNS-Challenge mit lima-city umstellen und den API-Schlüssel im Ansible Vault ablegen
- [ ] Festlegen, welche Teile von Zammad, Discourse und Nextcloud für Gäste öffentlich bleiben
- [ ] Weboberflächen Dienst für Dienst nur noch über NetBird erreichbar machen und Zugriffsregeln nach Gruppen aus authentik anlegen
- [ ] Anleitung für Engagierte zum Einrichten des NetBird-Clients schreiben

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
- [ ] SSD verschlüsseln, weil der Mini-PC in der offenen Werkstatt steht. Fedora CoreOS kann das bei der Installation über die Butane-Datei mit LUKS und dem Schlüssel im TPM einrichten, siehe [Fedora-CoreOS-Doku zu Storage](https://docs.fedoraproject.org/en-US/fedora-coreos/storage/). Testen, ob das mit dem Wechsel auf unser Image zusammenspielt
- [ ] Automatische Updates und Neustartfenster festlegen, zum Beispiel nachts um 02:00 wie bei unseren anderen Servern
- [x] Prüfen, ob Python für Ansible vorhanden ist, und es sonst per rpm-ostree nachinstallieren
- [ ] Host in docker-compose-server aufnehmen und den Arcane-Agenten ausrollen, für Ollama und Open WebUI mit automatischen Updates
- [ ] resticker einrichten und das Volume mit den Modellen vom Backup ausschließen, weil sich Modelle jederzeit neu laden lassen
- [ ] Push-Monitor in Uptime Kuma anlegen
- [ ] Beszel-Agenten ausrollen und Alarme für Plattenplatz, Arbeitsspeicher und Temperatur anlegen
- [ ] NetBird-Client auf dem Mini-PC einrichten, auf uCore per rpm-ostree oder als Container mit Host-Netzwerk
- [ ] Startreihenfolge in systemd festlegen, sodass NetBird vor Docker läuft
- [ ] Zugriffsregeln in NetBird anlegen, sodass die Helpdesk-VM nur den Port von Ollama und Admins nur SSH erreichen

### Phase 2 Inferenz

- [ ] GPU-Stack prüfen mit vulkaninfo und Zugriff auf /dev/dri im Container
- [ ] Speicherzuteilung für die GPU über UMA und GTT-Limit testen und dokumentieren
- [ ] Rolle ollama in docker-compose-server anlegen und den Port nur an die NetBird-Adresse binden, weil Ollama keine Anmeldung kennt und Docker die Firewall des Hosts umgeht
- [ ] Prüfen, dass Ollama aus dem LAN und dem Gäste-WLAN des Makerspace nicht erreichbar ist
- [ ] Kontrollieren, dass Modelle wirklich auf der GPU laufen und nicht auf der CPU, zum Beispiel an der GPU-Auslastung in Beszel
- [ ] Leistungsprofil und TDP im BIOS auf Dauerbetrieb einstellen und den Einfluss auf die Geschwindigkeit messen
- [ ] Vulkan und ROCm mit llama-bench vergleichen. Die [Ollama-Doku zu GPUs](https://github.com/ollama/ollama/blob/main/docs/gpu.mdx) führt gfx1150 für ROCm v7, ältere [Erfahrungen im Framework-Forum](https://community.frame.work/t/amd-rocm-does-not-support-the-amd-ryzen-ai-300-series-gpus/68767) waren gemischt. Für Vulkan braucht der Container die Gruppe render und für Angaben zum Grafikspeicher die Capability cap_perfmon
- [ ] `OLLAMA_IGPU_ENABLE=1` setzen. Ollama verwirft integrierte AMD-GPUs standardmäßig und lässt nur gfx1151 zu, siehe [discover/runner.go](https://github.com/ollama/ollama/blob/main/discover/runner.go). Ohne die Variable läuft auf dem HX 370 mit gfx1150 alles unbemerkt auf der CPU
- [ ] `OLLAMA_CONTEXT_LENGTH` fest auf etwa 32768 setzen. Zammad schickt keine Kontextlänge mit, und Ollama wählt sonst je nach erkanntem Grafikspeicher 4K, 32K oder 256K, siehe [envconfig/config.go](https://github.com/ollama/ollama/blob/main/envconfig/config.go). Bei 4K würden lange Prompts wie der des Ticket Categorizer still abgeschnitten
- [ ] `OLLAMA_KEEP_ALIVE` hoch setzen, damit das Modell beim Repair Café nicht nach 5 Minuten Pause entladen wird, und `OLLAMA_MAX_LOADED_MODELS` so wählen, dass Sprach- und Embedding-Modell gleichzeitig geladen bleiben
- [ ] Startmodell [qwen3.6:35b-a3b](https://ollama.com/library/qwen3.6:35b-a3b) laden
- [ ] UMA und GTT-Limit so einstellen, dass die GPU deutlich mehr als 24 GB nutzen darf
- [ ] Embedding-Modell [bge-m3](https://ollama.com/library/bge-m3) laden und prüfen, dass es zusammen mit dem Sprachmodell in den Speicher passt
- [ ] Geschwindigkeit messen und mit qwen3.6:35b-a3b-mtp-q4_K_M, qwen3.6:35b-a3b-q8_0 und qwen3.6:27b vergleichen, Ergebnisse in docs/benchmarks.md festhalten
- [ ] Optional die NPU mit [AMD Lemonade](https://github.com/lemonade-sdk/lemonade) ausprobieren

### Phase 3 Prompts und Tests

- [ ] Rolle open-webui anlegen und Konten für die beteiligten Engagierten einrichten
- [ ] Testsatz aus abgeschlossenen Repair-Café-Tickets exportieren und pseudonymisieren, nur lokal speichern
- [ ] Extraktionsregeln und Anweisungen für die Agenten sowie die Textwerkzeuge nach den Gedanken oben in prompts/ ablegen
- [ ] Skript in eval/ schreiben, das Modelle und Prompts gegen den Testsatz laufen lässt
- [ ] Bewertungskriterien festlegen, zum Beispiel richtige Kategorie und Nützlichkeit des Vorschlags aus Sicht der Engagierten
- [ ] Beim Repair Café im November Vorschläge live in Open WebUI testen und Rückmeldungen sammeln

### Phase 4 Anbindung an Zammad

- [ ] In der Testinstanz unter AI und Providers Ollama mit der NetBird-Adresse des Mini-PCs und qwen3.6:35b-a3b als Modell eintragen, siehe [Zammad-Doku](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama)
- [ ] Prüfen, dass der Status des Anbieters nach der ersten Anfrage grün ist
- [ ] bge-m3 als Embedding-Modell beim Anbieter eintragen
- [ ] Speicherverbrauch von Elasticsearch in Beszel beobachten, weil dort auch die Vektoren der semantischen Suche liegen. Die Zammad-Rolle erlaubt bisher 4 GB
- [ ] Agenten Ticket Categorizer für die Art des Geräts und Ticket Text Extractor für die übrigen Felder anlegen
- [ ] Custom AI Agent für den Reparaturansatz und einen für erkannte Kontaktdaten anlegen, beide schreiben nur interne Notizen
- [ ] Trigger anlegen, die die Agenten bei neuen Tickets der Gruppe Repair Café auslösen
- [ ] Prüfen, dass kein Agent und kein Trigger E-Mails oder SMS an Gäste verschickt
- [ ] Gegen die Testinstanz auf der Test-VM testen
- [ ] Ollama in Zammad auf der Helpdesk-VM als Anbieter eintragen und Agenten und Trigger ins Echtsystem übernehmen
- [ ] Beim Repair Café im Dezember im Echtbetrieb einsetzen und Rückmeldungen zu den Notizen sammeln

### Phase 5 Wissensdatenbank und n8n

- [ ] Wissensdatenbank in Zammad für Reparaturanleitungen einrichten und aus erfolgreichen Reparaturen Artikel erzeugen, die Engagierte vor der Veröffentlichung prüfen
- [ ] Rolle n8n in docker-compose-server für die Helpdesk-VM anlegen, siehe [n8n-Doku zum Selbsthosten](https://docs.n8n.io/hosting/), hinter Traefik mit Anmeldung und mit Sicherung per resticker
- [ ] Workflow für Statistik bauen, der Ergebnisse zählt und Freitexte zu fehlendem Werkzeug und Highlights zusammenfasst
- [ ] Workflows als JSON nach n8n-workflows/ exportieren
- [ ] Mit der anstiftung per Issue in mapped-repair-events klären, ob sie schreibende Endpunkte für Laufzettel und Neuigkeiten annehmen würde
- [ ] Felder in Zammad auf die Felder der Laufzettel abbilden, damit die Daten ohne Nacharbeit übertragbar sind
- [ ] Endpunkte in mapped-repair-events umsetzen und als Pull Request einreichen
- [ ] Workflow bauen, der nach dem Repair Café die Laufzettel auf reparatur-initiativen.org anlegt, bis dahin Laufzettel von Hand übertragen
- [ ] Workflow für Terminvorschläge bauen, der Anmeldungen in Nuudel auswertet
- [ ] Workflow für den Newsletter bauen, der nur Gäste mit Einwilligung für die Neuigkeiten unserer Initiative auf reparatur-initiativen.org anmeldet

### Phase 6 Abschluss und Veröffentlichung

- [ ] Kennzahlen aus dem Antrag erheben, also Reparaturquote, Reparaturen durch Gäste und neue Engagierte, Rückmeldungen zu Vorschlägen und gemeldete Reparaturen
- [ ] Dokumentation in docs/ vervollständigen, sodass andere Reparaturinitiativen MANUEL nachbauen können
- [ ] Eigenständige compose.yaml als Beispiel für Nachnutzende bereitstellen
- [ ] DSEE-Logo mit »Gefördert durch« in die README aufnehmen
- [ ] Ergebnisse veröffentlichen, zum Beispiel auf unserer Website, im Netzwerk Reparatur-Initiativen der anstiftung und in den sozialen Medien
- [ ] Belege der Veröffentlichung für den Sachbericht sammeln
- [ ] Verwendungsnachweis bis 31.03.2027 im Förderportal einreichen

## Ausblick

Im Antrag haben wir angekündigt, MANUEL später auch für Fragen wie »Wer verfügt über welche Kenntnisse?« und »Welche Werkzeuge und Maschinen stehen im Verein zur Verfügung?« einzusetzen. Dafür bieten sich Dienste an, für die es in docker-compose-server schon Rollen gibt. Sie liegen als Submodule in diesem Repo.

- **Discourse als Wissensbasis und Chatbot.** Für das Forum gibt es die Rolle [discourse](https://github.com/makerspace-gt/docker-compose-server/tree/main/roles/discourse). Das mitgelieferte Plugin [discourse-ai](https://github.com/discourse/discourse/tree/main/plugins/discourse-ai) kann Ollama [direkt ansprechen](https://github.com/discourse/discourse/blob/main/plugins/discourse-ai/lib/completions/endpoints/ollama.rb). Es bringt einen KI-Bot mit eigenen Rollen und hinterlegten Dokumenten, Zusammenfassungen, semantische Suche und ähnliche Themen per Embedding mit. Ein Bot im Forum könnte Fragen zu Kenntnissen der Mitglieder und zu Werkzeugen beantworten, gestützt auf Beiträge und Dokumente des Vereins.
- **Signal als Kanal für Benachrichtigungen.** Für [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) auf Basis von [signal-cli](https://github.com/AsamK/signal-cli) gibt es die Rolle [signal-cli-rest-api](https://github.com/makerspace-gt/docker-compose-server/tree/main/roles/signal-cli-rest-api). n8n könnte darüber Engagierte an Termine erinnern oder über neue Anmeldungen informieren. Später wäre auch ein Signal-Bot denkbar, der Fragen an MANUEL weiterleitet. Gäste schreiben wir nur mit ihrer Einwilligung an.
- **Vikunja für Aufgaben aus dem Repair Café.** Für [Vikunja](https://vikunja.io/docs/) gibt es die Rolle [vikunja](https://github.com/makerspace-gt/docker-compose-server/tree/main/roles/vikunja). n8n könnte aus vertagten Reparaturen Aufgaben anlegen, etwa für die Besorgung von Ersatzteilen, und fehlendes Werkzeug aus der Statistik als Wunschliste für Anschaffungen sammeln.
- **LanguageTool für Rechtschreibung und Grammatik.** Ein eigener [LanguageTool-Server](https://dev.languagetool.org/http-server) prüft Texte, ohne dass sie an einen fremden Dienst gehen. Engagierte binden ihn in die Browser-Erweiterung ein und nutzen ihn dann in Zammad, Discourse, Nextcloud und Forgejo. [LanguageTool](https://github.com/languagetool-org/languagetool) steht unter LGPL-2.1 und läuft auf der Kollaborations-VM. Als Java-Programm braucht es 1 bis 2 GB Arbeitsspeicher, die optionalen [N-Gramm-Daten](https://dev.languagetool.org/finding-errors-using-n-gram-data) für bessere Ergebnisse brauchen zusätzlich mehrere GB Platte. Ein Teil davon überschneidet sich mit den Textwerkzeugen von Zammad, LanguageTool funktioniert aber in allen Diensten und ohne Sprachmodell.

Alle drei Dienste würden denselben Ollama-Server über NetBird nutzen. Dafür müssen die NetBird-Regeln um die jeweiligen Hosts erweitert werden.

Unabhängig von MANUEL fehlt uns eine zentrale Nutzerverwaltung. [authentik](https://github.com/goauthentik/authentik) liegt dafür als Submodul in diesem Repo. Es steht weitgehend unter MIT, ein Unternehmensteil unter eigener Lizenz. Laut [Doku zu Integrationen](https://docs.goauthentik.io/integrations/) lassen sich viele unserer Dienste per OpenID Connect oder SAML anbinden. Für MANUEL betrifft das vor allem NetBird, n8n, Open WebUI und Zammad. NetBird kann authentik [als Identity Provider nutzen](https://docs.netbird.io/selfhosted/identity-providers/authentik). Kommt authentik bald, richten wir NetBird gleich damit ein statt mit dem eingebauten Dex.

## Aufteilung und Größe der VMs

Die Aufteilung folgt drei Regeln. Sensible Dienste liegen getrennt von Inhalten der Gäste, was zusammen ausfällt, darf zusammen liegen, und Abhängigkeiten zeigen nur von Fachanwendungen zu Zugang und Monitoring. Die Größen sind Schätzungen für den laufenden Betrieb, nicht die Summe aller Speichergrenzen. Pro VM rechnen wir etwa 1 GB für Betriebssystem, Docker, Traefik, CrowdSec, resticker und die Agenten von Arcane und Beszel ein.

| VM | Dienste | RAM | vCPU | Lokale Platte | Grundlage |
|---|---|---|---|---|---|
| Zugang, neu | authentik, NetBird, Vaultwarden | 4 GB | 2 | 30 GB | authentik braucht laut [Installationsanleitung](https://github.com/goauthentik/authentik/blob/main/website/docs/install-config/install/docker-compose.mdx) mindestens 2 GB, NetBird und Vaultwarden sind klein |
| Verwaltung, neu | Forgejo, Runner, Arcane-Server | 6 GB | 4 | 60 GB | Der Runner braucht Platz für Jobs mit Ansible, OpenTofu und Docker |
| Helpdesk, neu | Zammad, n8n | 16 GB | 4 | 80 GB | Die [Zammad-Rolle](https://github.com/makerspace-gt/docker-compose-server/blob/main/roles/zammad/templates/.env.j2) erlaubt zusammen rund 13 GB, davon 4 GB für Elasticsearch. Dazu kommt n8n mit 1 bis 2 GB. Zammad speichert Anhänge in der Datenbank, und Elasticsearch hält künftig auch die Vektoren der semantischen Suche |
| Kollaboration, neu | Nextcloud, Vikunja, LanguageTool | 6 GB | 3 | 40 GB | Die Dateien von Nextcloud liegen auf der Storagebox, lokal liegen nur Programme und Datenbanken. Wiki.js entfällt, dafür kommt LanguageTool dazu |
| Fotos, neu | Immich | 6 GB | 4 | 30 GB plus Vorschaubilder | Laut [Anforderungen](https://github.com/immich-app/immich/blob/main/docs/docs/install/requirements.md) mindestens 6 GB und 2 Kerne. Die Datenbank muss auf lokaler SSD liegen und nie auf einem Netzlaufwerk, die Originale können auf die Storagebox |
| Forum, neu | Discourse | 4 GB | 2 | 40 GB | Laut [Installationsanleitung](https://github.com/discourse/discourse/blob/main/docs/INSTALL-cloud.md) mindestens 1 GB mit Swap, empfohlen 2 GB und mehr. Mit discourse-ai und Embeddings eher 4 GB |
| Monitoring, neu | Uptime Kuma, Beszel-Hub, signal-cli-rest-api | 2 GB | 2 | 20 GB | Alle drei sind klein, signal-cli braucht als Java-Programm etwa 0,5 GB |
| Test, bei Bedarf | Testinstanz von Zammad | 8 GB | 2 | 40 GB | Nur bei Bedarf per OpenTofu anlegen und danach wieder löschen |
| Mini-PC | Ollama, Open WebUI, optional Machine Learning für Immich | 64 GB | 12 Kerne | 1 TB | Sprachmodell mit 24 GB, Embedding-Modell, Varianten für den Benchmark |

Zusammen brauchen die dauerhaften VMs etwa 44 GB Arbeitsspeicher und 21 vCPU, mit der Testinstanz 52 GB.

- **Immich kann den Mini-PC mitnutzen.** Immich trennt das Machine Learning für Gesichter und Suche vom Server und kann es [auf einem anderen Rechner](https://github.com/immich-app/immich/blob/main/docs/docs/guides/remote-machine-learning.md) laufen lassen. Mit ROCm nutzt es auch AMD-GPUs, das Image dafür braucht laut [Doku](https://github.com/immich-app/immich/blob/main/docs/docs/features/ml-hardware-acceleration.md) aber 35 GB Platz. Dann bleibt die Immich-VM schlanker, und die Fotos werden trotzdem ausgewertet.
- **Die Storagebox ist ein Netzlaufwerk.** Für die Dateien von Nextcloud und die Originale von Immich ist das in Ordnung. Datenbanken und die Vorschaubilder von Immich gehören auf die lokale Platte. Die Vorschaubilder belegen erfahrungsgemäß einen Bruchteil der Originale, die genaue Größe hängt von der Bibliothek ab.
- **Die Zahlen prüfen wir mit Beszel.** Nach einigen Wochen Betrieb passen wir die Größen an den tatsächlichen Verbrauch an. Mit OpenTofu ist das eine Änderung in Git.

### Neuaufbau

Alle VMs entstehen neu, die Namen der Hosts legen wir beim Anlegen per OpenTofu fest. Die Daten der bestehenden Dienste ziehen trotzdem um, vor allem Tickets aus Zammad, Passwörter aus Vaultwarden, Dateien und Kalender aus Nextcloud, Seiten aus Wiki.js, die je nach Inhalt in Discourse, die Wissensdatenbank von Zammad oder Forgejo wandern, Aufgaben aus Vikunja und Beiträge aus Discourse. Dafür nutzen wir die Backups von resticker und die Aufgaben zur Wiederherstellung, die die Rollen für Zammad, Vaultwarden und Discourse schon mitbringen. Jeder Umzug ist zugleich ein Test der Wiederherstellung. Die alten VMs bleiben bis zur erfolgreichen Prüfung der neuen Dienste stehen.

## Infrastruktur als Code

Langfristig soll die gesamte Infrastruktur aus Git entstehen, von der VM bis zum Dienst. Die Bausteine dafür greifen in drei Schichten ineinander.

| Schicht | Werkzeug | Aufgabe |
|---|---|---|
| VMs | [OpenTofu](https://github.com/opentofu/opentofu) mit dem [Provider für OpenNebula](https://search.opentofu.org/provider/opennebula/opennebula/latest) | VMs mit CPU, Arbeitsspeicher, Platten, Netz und SSH-Schlüsseln in [OpenNebula](https://docs.opennebula.io/stable/) anlegen |
| Hosts und Dienste | Ansible in docker-compose-server | Grundsystem, NetBird-Client, Agenten von Arcane und Beszel und die Compose-Stacks der Dienste |
| Updates im Betrieb | Arcane | Neue Images erkennen und nach Regeln aktualisieren |

- **Ein Repo für VMs und Dienste.** Der Code für OpenTofu kommt als Ordner tofu/ nach docker-compose-server. So ändert ein Commit eine VM und die Dienste darauf gemeinsam. OpenTofu schreibt die Inventardatei für Ansible, alternativ liest Ansible die VMs direkt über das [Inventory-Plugin für OpenNebula](https://github.com/ansible-collections/community.general/blob/main/plugins/inventory/opennebula.py).
- **Der Zustand von OpenTofu enthält Geheimnisse.** Wir verschlüsseln ihn mit der eingebauten [Verschlüsselung des State](https://opentofu.org/docs/language/state/encryption/) und legen den Schlüssel im Ansible Vault ab.
- **Ansible läuft bei jedem Commit.** Ein Runner von [Forgejo Actions](https://forgejo.org/docs/latest/user/actions/overview/) führt die Playbooks aus. Bei einem Pull Request laufen ansible-lint, `ansible-playbook --check --diff` und `tofu plan`. Nach dem Merge auf main laufen nur die Playbooks, deren Rollen sich geändert haben. `tofu apply` und das Playbook für Zammad starten wir von Hand, weil sie VMs löschen oder Datenbanken migrieren können. Bis Forgejo steht, geht dasselbe mit einem [eigenen Runner für GitHub Actions](https://docs.github.com/en/actions/hosting-your-own-runners).
- **Der Runner läuft bei uns, nicht in der Cloud.** Er braucht den SSH-Schlüssel für alle Hosts, das Passwort für den Ansible Vault und den Zugang zu OpenNebula. Diese Geheimnisse gehören nicht zu einem fremden Anbieter. Der [selbst gehostete Runner](https://forgejo.org/docs/latest/admin/actions/runner-installation/) erreicht die Hosts über NetBird.
- **Eigene Forgejo-Instanz.** [Forgejo](https://codeberg.org/forgejo/forgejo) steht unter GPL-3.0 und ist nur über NetBird erreichbar. Die Anmeldung läuft über [authentik](https://docs.goauthentik.io/integrations/services/forgejo/). Öffentliche Repos wie MANUEL spiegeln wir per [Push-Mirror](https://forgejo.org/docs/latest/user/repo-mirror/) weiter nach GitHub oder Codeberg, damit andere Initiativen sie finden.
- **Eine Verwaltungs-VM für Forgejo, Runner und Arcane-Server.** Alle drei steuern die übrigen Hosts. Sie liegen getrennt von der Zugangs-VM mit authentik, NetBird und Vaultwarden, weil der Runner fremden Code aus Repos ausführt.
- **Henne und Ei.** Die Verwaltungs-VM und Forgejo richten wir einmalig von einem Admin-Rechner aus mit OpenTofu und Ansible ein. Danach übernimmt die CI alle übrigen Hosts. Änderungen an der Verwaltungs-VM selbst laufen weiter von Hand.

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
├── prompts/         Kopien der Agenten-Konfiguration aus Zammad und Prompts für n8n
├── eval/            Skripte zum Testen, ohne echte Ticketdaten
├── n8n-workflows/   exportierte n8n-Workflows
├── mapped-repair-events/  Submodul mit der Plattform der anstiftung, GPL-3.0
├── datenpotenzialanalyse-repairc-cafe-gt/  Submodul mit der Hausarbeit zu unseren Laufzetteln, CC BY 4.0
├── docker-compose-server/  Submodul mit unserer IT-Infrastruktur als Ansible-Rollen
├── zammad/                Submodul mit dem Quellcode von Zammad, AGPL-3.0
├── zammad-docker-compose/ Submodul mit dem Docker-Compose-Stack von Zammad, AGPL-3.0
├── n8n/                   Submodul mit dem Quellcode von n8n, Sustainable Use License
├── netbird/               Submodul mit dem Quellcode von NetBird, BSD-3-Clause, Server-Teile AGPL-3.0
├── ollama/                Submodul mit dem Quellcode von Ollama, MIT
├── signal-cli/            Submodul für den Ausblick, GPL-3.0
├── signal-cli-rest-api/   Submodul für den Ausblick, MIT
├── discourse/             Submodul für den Ausblick, GPL-2.0
├── vikunja/               Submodul für den Ausblick, AGPL-3.0
├── authentik/             Submodul für die zentrale Nutzerverwaltung, MIT
├── arcane/                Submodul mit der Verwaltung der Docker-Hosts als Ersatz für watchtower, BSD-3-Clause
├── beszel/                Submodul mit der Überwachung der Ressourcen, MIT
├── opentofu/              Submodul für das Anlegen der VMs, MPL-2.0
├── forgejo/               Submodul für die eigene Git-Instanz, GPL-3.0
├── immich/                Submodul für die Verwaltung von Bildern, AGPL-3.0
├── languagetool/          Submodul für Rechtschreibung und Grammatik, LGPL-2.1
└── vaultwarden/           Submodul mit dem Passwortmanager, AGPL-3.0
```

Die Submodule von Zammad, n8n, NetBird, Ollama, Discourse, Vikunja, Signal, authentik, Arcane, Beszel, OpenTofu, Forgejo, Immich, LanguageTool und Vaultwarden sind groß und deshalb in `.gitmodules` als shallow markiert. Sie dienen als Nachschlagewerk für Schnittstellen und Konfiguration. Unsere eigenen exportierten Workflows liegen in `n8n-workflows/`, damit sie nicht mit dem Submodul `n8n/` kollidieren.

Geheimnisse wie API-Token gehören nicht hierher. Sie liegen verschlüsselt im Ansible Vault von docker-compose-server.
