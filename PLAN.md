# Plan

Dieser Plan beschreibt, wie wir MANUEL vom Kauf der Hardware bis zum Verwendungsnachweis umsetzen. Die Infrastruktur dafür entsteht im Repo [it-infrastructure](https://github.com/makerspace-gt/it-infrastructure).

## Rahmenbedingungen

- **Hardware** ist ein MINISFORUM AI X1 Pro-370 mit AMD Ryzen AI 9 HX 370, Radeon 890M, XDNA-2-NPU, 64 GB DDR5 und 1 TB SSD.
- **Bewilligungszeitraum** ist vom 15.09.2026 bis 31.12.2026. Bis dahin müssen alle Ausgaben bezahlt sein.
- **Verwendungsnachweis** mit Sachbericht und zahlenmäßigem Nachweis ist bis 31.03.2027 im Förderportal der DSEE fällig. Der Sachbericht muss auch die Veröffentlichung und Kommunikation der Ergebnisse nachweisen.
- **Zweckbindung** gilt zwei Jahre nach Ende des Bewilligungszeitraums, also bis 31.12.2028.
- **Förderhinweis** mit DSEE-Logo und dem Zusatz »Gefördert durch« gehört auf alle Veröffentlichungen, also auch in dieses Repo und auf das Gerät.
- **Abweichung vom Finanzierungsplan** ist geklärt und kein Problem. Bewilligt war die Variante mit 2 TB, gekauft wurde die Variante mit 1 TB.

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
- **Ollama nur per VPN, Open WebUI über den NetBird-Proxy.** Ollama ist nur über NetBird für die Helpdesk-VM und Open WebUI erreichbar. Open WebUI ist über den Reverse Proxy von NetBird mit Anmeldung über authentik erreichbar, siehe [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md).
- **Datenschutz von Anfang an.** Löschfristen, Datenschutzhinweis und Verzeichnis von Verarbeitungstätigkeiten entstehen zusammen mit den Feldern in Zammad, siehe [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md).
- **Daten bleiben lokal.** Ticketinhalte verlassen nie unsere Systeme. Einzige Ausnahme sind Marke und Modell für die Suche nach Anleitungen über eine eigene SearXNG-Instanz, siehe [ADR 35](docs/adr/0035-anleitungen-ueber-eine-eigene-suche-finden.adoc). Echte Ticketdaten landen nie in diesem öffentlichen Repo.
- **Code rechnet, das Modell formuliert.** Zählen, Zuordnen, Termine planen und Daten übertragen erledigen Zammad-Trigger und n8n-Workflows nach festen Regeln. Das Sprachmodell liest aus Freitext heraus, schreibt Texte und fasst zusammen.
- **Alles ist Code.** Die Einrichtung des Hosts liegt als Ansible-Rollen in it-infrastructure. Prompts, exportierte n8n-Workflows, Testsatz-Werkzeuge und Doku liegen hier. Die Konfiguration der KI-Agenten in Zammad, also Regeln und Beschreibungen der Auswahlwerte, legen wir als Kopie in prompts/ ab.

## Offene Entscheidungen

Die Empfehlungen dieser Tabelle sind inzwischen entschieden und als ADR in [docs/adr](docs/adr/README.adoc) festgehalten. Die Tabelle bleibt als Stand vom 22.10.2026 stehen. Abweichend von der Empfehlung läuft das Sprachmodell mit llama.cpp, `d3:9b` und `bge-m3` mit Ollama, siehe [ADR 25](docs/adr/0025-sprachmodell-mit-llama-cpp-und-decision-modell-mit-ollama-betreiben.adoc).

| Frage | Empfehlung | Alternative |
|---|---|---|
| Betriebssystem | [uCore Minimal](https://github.com/ublue-os/ucore) von Universal Blue auf Basis von [Fedora CoreOS](https://docs.fedoraproject.org/en-US/fedora-coreos/), weil es den neuesten Kernel mitbringt, der laut [Phoronix](https://www.phoronix.com/review/amd-perfopt/3) die LLM-Leistung von Radeon-iGPUs deutlich verbessert, sich atomar mit Rollback aktualisiert und zu Bluefin auf unseren Notebooks passt | Fedora Server mit gleichem Kernel, klassischer Paketverwaltung und einfacherer Anbindung an Ansible |
| Inferenz-Server | [Ollama](https://docs.ollama.com/) im Container. Vulkan und ROCm vergleichen wir im Benchmark, denn die [Ollama-Doku zu GPUs](https://github.com/ollama/ollama/blob/main/docs/gpu.mdx) führt den gfx1150 des HX 370 inzwischen auch für ROCm v7 | [llama.cpp](https://github.com/ggml-org/llama.cpp) mit [llama-swap](https://github.com/mostlygeek/llama-swap), falls Ollama die GPU schlecht nutzt. Zammad bindet es über den Anbieter Custom (OpenAI Compatible) ein |
| Anbindung an Zammad | [KI-Agenten](https://admin-docs.zammad.org/en/latest/ai/ai-agents.html) und KI-Funktionen von Zammad mit [Ollama als Anbieter](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama), das Zammad über NetBird erreicht. Zammad füllt die Felder selbst, n8n übernimmt nur Aufgaben außerhalb von Zammad | n8n-Workflows auch für die Felder, falls die Agenten nicht reichen |
| Automatisierung | [n8n selbst gehostet](https://docs.n8n.io/hosting/) auf der Helpdesk-VM neben Zammad. Dort liegen die Zugangsdaten im Rechenzentrum statt in der offenen Werkstatt, Workflows ohne Sprachmodell laufen auch bei Neustart oder Ausfall des Mini-PCs, und Traefik, resticker und Uptime Kuma sind schon eingerichtet. n8n steht unter der [Sustainable Use License](https://github.com/n8n-io/n8n/blob/master/LICENSE.md), die den Betrieb für eigene Zwecke erlaubt, aber keine Open-Source-Lizenz ist | n8n auf dem Mini-PC direkt neben Ollama |
| Anzahl der Modelle | Ein Sprachmodell für alle Aufgaben mit einem eigenen Prompt pro Aufgabe, dazu ein kleines Embedding-Modell. Zwei große Modelle passen kaum gleichzeitig in den Speicher der GPU, und jeder Wechsel kostet Ladezeit | Zusätzlich ein kleines Sprachmodell, falls der Benchmark zeigt, dass einfache Aufgaben zu lange dauern |
| Schwierige Fälle | Vorerst keine Sonderbehandlung, das Sprachmodell bearbeitet alle Tickets | Eskalation auf ein großes, langsames Modell. Das schnelle Modell bleibt Standard, das große wird auf Anforderung geladen und schreibt seine Lösung als interne Notiz. Auslöser sind ein Klick in Zammad und feste Regeln, nicht die Selbsteinschätzung des Modells. Lohnt sich nur, wenn der Testsatz einen klaren Qualitätsvorsprung zeigt. Ein Decision-Modell wie [d3](https://ollama.com/library/d3) kann vorab markieren, ob ein Ticket sicherheitsrelevant ist oder die Beschreibung nicht reicht. Die Markierung ist ein Hinweis für die Engagierten und ersetzt weder den Sicherheitshinweis im Prompt noch ihre Prüfung |
| Embedding-Modell | [bge-m3](https://ollama.com/library/bge-m3), das Zammad für Ollama [selbst empfiehlt](https://github.com/zammad/zammad/blob/develop/lib/ai/provider/ollama.rb). Es ist mehrsprachig und dient der semantischen Suche in der Wissensdatenbank | [qwen3-embedding](https://ollama.com/library/qwen3-embedding) |
| Reparaturanleitungen | [Wissensdatenbank von Zammad](https://admin-docs.zammad.org/en/latest/manage/knowledge-base.html). Zammad erzeugt Artikel aus einem Ticket und zeigt per Embedding [passende Artikel am Ticket](https://github.com/zammad/zammad/blob/develop/app/services/service/ticket/ai/related_knowledge_base_answers.rb) an | Wiki.js mit eigenem Embedding-Workflow in n8n |
| Termin im Ticket | Eigenes Datumsfeld Termin über die [Objektverwaltung von Zammad](https://admin-docs.zammad.org/en/latest/system/objects.html) statt der Wartezeit des Tickets. Dann entfällt unsere angepasste Kopie der ticket.rb, siehe [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md) | Kleiner Patch als Initializer statt Kopie der ganzen Datei |
| Vernetzung und Fernzugriff | [NetBird](https://docs.netbird.io/) mit Regeln, die nur der Helpdesk-VM den Zugriff auf Ollama und nur Admins den Zugriff per SSH erlauben | Tailscale, das in uCore schon enthalten ist |
| Zugang zu Open WebUI | [Open WebUI](https://docs.openwebui.com/) über NetBird für Engagierte mit Konto | Über Traefik auf der Helpdesk-VM, die Open WebUI per NetBird erreicht |
| Startmodell | [qwen3.6:35b-a3b](https://ollama.com/library/qwen3.6:35b-a3b) mit festem Tag statt latest. Als Mixture-of-Experts-Modell sind pro Token nur etwa 3B Parameter aktiv, was bei begrenzter Speicherbandbreite zählt. Mit 23 bis 24 GB passt es in den Speicher, und es versteht auch Bilder wie Fotos von Typenschildern | Varianten mit MTP oder q8_0 und das dichte qwen3.6:27b als Vergleich im Benchmark |
| Hostname | Neuer Eintrag in der Inventardatei von it-infrastructure | |
| Testinstanz für Zammad | Test-VM, die OpenTofu nur bei Bedarf anlegt | Direkt im Echtsystem mit eigener Testgruppe |

Laut [Zammad-Doku](https://admin-docs.zammad.org/en/latest/ai/provider.html#ollama) lässt sich Ollama direkt als KI-Anbieter mit URL und Modell eintragen. Zammad verbindet sich dabei selbst mit Ollama. Die Doku nennt keine Anmeldung oder TLS für Ollama, deshalb schützen wir den Zugang über NetBird.

Laut [Quellcode des Ollama-Anbieters](https://github.com/zammad/zammad/blob/develop/lib/ai/provider/ollama.rb) ruft Zammad Ollama über /api/generate auf, schaltet das Nachdenken ab, setzt die Temperatur auf 0 und verlangt bei Bedarf JSON. Eine Kontextlänge schickt Zammad nicht mit, die muss Ollama selbst vorgeben. Die [Agententypen](https://github.com/zammad/zammad/tree/develop/app/models/ai/agent/type) umfassen unter anderem Ticket Categorizer für Auswahlfelder auch als Baum, Ticket Text Extractor für Text, Zahlen und Auswahlwerte, Ticket Tagger und Custom AI Agent. Ein Agent wird über einen normalen Trigger ausgelöst und wendet sein Ergebnis mit denselben Aktionen wie ein Trigger an, also Feldänderungen, interne Notizen oder Webhooks. Ob unsere Zammad-Version all das schon bietet, prüfen wir in Phase 0.

## Infrastruktur

MANUEL läuft auf der neu aufgebauten IT des Vereins. Zugangs-VM mit authentik und NetBird, Helpdesk-VM mit Zammad und n8n, Erreichbarkeit nur über NetBird, Updates mit Arcane und Überwachung mit Beszel beschreibt der [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md) in it-infrastructure. Für MANUEL muss davon bis zum 31.12.2026 nur Stufe 1 stehen.

## Aufgaben

| Aufgabe | Zammad | n8n |
|---|---|---|
| Geräte erfassen | Jedes Gerät bekommt ein Ticket, auch spontane Gäste am Empfang mit dem Tag `spontan`, siehe [ADR 34](docs/adr/0034-jedes-geraet-mit-ticket-und-typenschild-erfassen.adoc) | |
| Felder füllen | Ticket Categorizer für die Art des Geräts, Ticket Text Extractor für Defekt, Marke, Bezeichnung und Baujahr aus Text und Foto vom Typenschild, ein Mensch bestätigt. Die Stromversorgung folgt aus der Kategorie im Katalog, nach dem ungefähren Alter fragt MANUEL in der Rückfrage | |
| Reparaturansatz schreiben | Custom AI Agent schreibt eine interne Notiz, passende Artikel aus der Wissensdatenbank zeigt Zammad am Ticket an | |
| Lösung schreiben | Textwerkzeug macht aus Stichworten der Engagierten einen vollständigen Text | |
| Reparaturanleitungen | Artikel in der Wissensdatenbank aus einem erfolgreichen Ticket erzeugen und von Engagierten prüfen lassen | Anleitungen, Ersatzteile und Explosionszeichnungen über SearXNG und die API von iFixit nur mit Marke und Modell suchen, MANUEL wählt Links für eine interne Notiz aus, siehe [ADR 35](docs/adr/0035-anleitungen-ueber-eine-eigene-suche-finden.adoc) |
| Tickets zusammenfassen | Eingebaute Zusammenfassung | |
| Tickets verknüpfen | Verknüpfen von Hand, unterstützt durch passende Artikel und Zusammenfassung | Nur falls das nicht reicht, Kandidaten per Embedding suchen |
| Gästedaten eintragen | Custom AI Agent schreibt erkannte Kontaktdaten als interne Notiz, ein Mensch übernimmt sie | |
| Terminvorschläge | Datumsfeld Termin im Ticket | Anmeldungen der Helfenden in [Nuudel](https://nuudel.digitalcourage.de/) lesen, daraus die Zahl paralleler Reparaturen ableiten, regelmäßige Zeitslots von Gästen beibehalten, ähnliche Geräte höchstens einen Slot auseinander einplanen und den Vorschlagstext von Ollama formulieren lassen, siehe [Terminvergabe](#terminvergabe) |
| Statistik | Ergebnisfelder und Berichte, Tag `highlight` für besondere Reparaturen | Ergebnisse zählen, also gelungen, teilweise gelungen, vertagt, nicht erfolgt, abgebrochen und No-Show, Freitexte zu fehlendem Werkzeug von Ollama zusammenfassen lassen und die [Sharecard](sharecard/README.md) als Entwurf erzeugen, die ein Mensch freigibt, siehe [ADR 33](docs/adr/0033-resuemee-als-sharecard-teilen.adoc) |
| Open Repair Alliance | Felder mit den Werten der Laufzettel | Gerät über die API von Restarters.net beim passenden Event anlegen, Restarters meldet es an die Open Repair Alliance weiter. Die Geräte von 2024 bis 2026 einmal nachmelden, siehe [ADR 36](docs/adr/0036-reparaturen-ab-2024-an-restarters-nachmelden.adoc) |
| Newsletter | Feld für die Einwilligung | Gäste mit dokumentierter Einwilligung für die Neuigkeiten unserer Initiative auf reparatur-initiativen.org anmelden, die Plattform verschickt dann die Bestätigungsmail |

Zammad löst n8n über die Trigger-Aktion Webhook aus, zum Beispiel wenn ein Ticket nach dem Termin geschlossen wird.

### Terminvergabe

Das Repair Café findet in der Regel am ersten und dritten Samstag im Monat statt. Wegen Feiertagen fallen Termine auch aus, die Daten kommen deshalb aus einer gepflegten Liste und werden nicht nur berechnet. Termine laufen von 11:00 bis 14:00 Uhr im Halbstundentakt. Das sind 6 Slots, dazu kommt 14:00 Uhr nur für Kleinigkeiten wie einen Lampenschalter tauschen, erstmal nur schauen oder klären, welches Ersatzteil bestellt werden muss.

Wie viele Termine parallel möglich sind, folgt aus den Anmeldungen der Helfenden. Der Empfang schafft 6 Personen parallel, pro 3 Reparierende gibt es 1 Person als Reserve.

| Wert | Rechnung |
|---|---|
| Empfang | Parallel durch 6, aufgerundet |
| Unterstützung | Parallel durch 3, aufgerundet |
| Personen | Parallel plus Empfang plus Unterstützung |
| Termine | Parallel mal 6, mit 14:00 Uhr mal 7 |

Bei einer gegebenen Zahl an Helfenden gilt der größte Wert für Parallel, der damit auskommt.

Tickets werden 1 bis 2 Tage gesammelt und dann gemeinsam abgearbeitet. So kann der Workflow alle offenen Tickets zusammen planen, statt sie nach Eingang zu verteilen. Fälle mit Wunschzeit kommen zuerst, die übrigen folgen. Angerufen wird meist erst in der Woche vor dem Repair Café, die Zeit kann sich dabei noch ändern. Der Plan bleibt deshalb ein Vorschlag, den Menschen bestätigen.

Feste Regeln sind die Plätze pro Slot und dass 14:00 Uhr nur Kleinigkeiten bekommt. Unter den übrigen Slots gilt diese Reihenfolge:

1. Die Wunschzeit des Gastes. Bei vertagten Geräten gilt ohne neuen Wunsch die bisherige Uhrzeit, damit sich die Gäste nicht umgewöhnen müssen
2. Ähnliche Geräte liegen höchstens einen Slot auseinander, damit Gäste mitarbeiten und ihre neuen Erkenntnisse direkt weitergeben. Gleiche Geräte gehen dabei vor gleicher Oberkategorie
3. Die Termine verteilen sich über den Tag, statt den Tag von Anfang an aufzufüllen

Das System läuft mit 16 GiB UMA. Damit passen `qwen3.6:35b-a3b`, `d3:9b` und `bge-m3` zusammen auf die GPU, ein Wechsel würde sonst 13 bis 26 Sekunden kosten. Ob alle Modelle dauerhaft geladen bleiben, entscheiden wir im Betrieb.

Eine Anfrage kann mehrere Geräte nennen. Das Decision-Modell erkennt das vorab, das Sprachmodell listet die Geräte auf, und die Engagierten teilen das Ticket auf. Jedes Gerät bekommt ein eigenes Ticket, damit Slots, Ergebnis und Statistik pro Gerät stimmen.

Am Ende soll es für alle so bequem wie möglich sein. Im Zweifel bekommt ein Gast die Zeit, die ihm am wenigsten Umstände macht, und bestätigte Termine bleiben unverändert, wenn neu geplant wird.

Die Rechnung und die Verteilung übernimmt n8n. Vertagte Geräte bleiben im selben Ticket, jeder Termin bekommt dort ein Tag wie `2026-10-17`. Ein Gerät gilt als vertagt, wenn das Ergebnis `vertagt` oder ein Wert darunter ist und das Ticket offen ist. Sagt ein Gast ab und will sich später wieder melden, wird der Platz frei und MANUEL plant nichts Neues ein. Dazu schlägt MANUEL die übliche Antwort vor. Sie dankt fürs Bescheid geben und nennt, dass das Repair Café am ersten und dritten Samstag im Monat stattfindet. Das Ticket wird geschlossen und bekommt das Tag `abgelehnt`, eine Regel in Zammad löscht geschlossene Tickets mit diesem Tag nach drei Monaten. Meldet sich der Gast vorher wieder und das Ticket geht auf, greift die Löschung nicht. Wer nicht erschienen ist, muss sich neu melden. MANUEL schlägt für diese Tickets nichts vor und erinnert nicht daran. Die bisherige Uhrzeit liest der Workflow aus dem Termin im Ticket, bevor er ihn überschreibt. Das Modell braucht er dafür nicht. Das Modell liefert nur die Angaben pro Ticket, also Wunschzeit, Gerät und ob es eine Kleinigkeit ist. Eine Kleinigkeit kann trotzdem sicherheitsrelevant sein, ein Lampenschalter hängt zum Beispiel an Netzspannung.

## Anbindung an reparatur-initiativen.org

Die Plattform [reparatur-initiativen.org](https://www.reparatur-initiativen.org) der anstiftung basiert auf dem Open-Source-Projekt [mapped-repair-events](https://github.com/anstiftung/mapped-repair-events) unter GPL-3.0. Es liegt als Submodul in diesem Repo.

Entscheidung vom 08.11.2026. Reparaturen melden wir künftig über Restarters.net an die Open Repair Alliance, siehe den nächsten Abschnitt. Bei der anstiftung führen wir weiter die Termine, damit Gäste sie abonnieren können, und die Neuigkeiten. Laufzettel legen wir dort nicht mehr an, sonst zählt die Open Repair Alliance jede Reparatur doppelt. Sie bittet ausdrücklich darum, nur ein Werkzeug zu nutzen.

- **Bisher bekam die Open Repair Alliance unsere Daten über die anstiftung.** Im [Datensatz der Open Repair Alliance](https://openrepair.org/open-data/) ist die anstiftung als Datenlieferantin geführt. Den Datensatz laden wir bei Bedarf dort herunter. Er steht unter CC BY-SA 4.0 und ist mit über 100 MB zu groß für das Repo, deshalb steht er in der `.gitignore`. Ihre Einträge tragen die Kategorien von reparatur-initiativen.org. Reparaturen, die wir dort als Laufzettel melden, landen also ohne eigenen Export bei der Open Repair Alliance.
- **Laufzettel gibt es bisher nur als Webformular.** Ein Laufzettel gehört zu einem Termin und enthält unter anderem Gerät, Kategorie, Marke, Alter, Fehlerbeschreibung und das Ergebnis der Reparatur mit Gründen.
- **Die Neuigkeiten einer Initiative gibt es ebenfalls nur als Webformular.** Nach der Anmeldung verschickt die Plattform eine Mail zur Bestätigung, also ein Double-Opt-in.
- **Die vorhandene API kann nur lesen.** Sie liefert Initiativen und Statistiken und braucht einen API-Token. Schreibende Endpunkte gibt es nicht.

Ideal wären zwei neue Endpunkte, die wir der anstiftung als Beitrag zum Projekt anbieten:

- ein Endpunkt zum Anlegen von Laufzetteln für einen Termin unserer Initiative
- ein Endpunkt zum Anmelden für die Neuigkeiten einer Initiative, der wie das Webformular die Bestätigungsmail auslöst

Die API-Token sind bisher nicht an eine Initiative gebunden. Für schreibende Endpunkte müsste ein Token auf die Initiativen beschränkt sein, die er verwalten darf.

## Anbindung an Restarters.net

[Restarters.net](https://restarters.net) von The Restart Project ist Open Source und hat eine API, über die sich Geräte anlegen, ändern und löschen lassen. Die Open Repair Alliance übernimmt die Daten von dort in ihre Datensätze. Lesen geht ohne Token, Schreiben braucht einen API-Token, den die Betreiber auf Anfrage vergeben.

- **Jedes Gerät gehört zu einem Event einer Gruppe.** Wir brauchen also eine Gruppe für unser Repair Café und je Termin ein Event. Die Termine stehen dann bei der anstiftung und bei Restarters. Das ist unkritisch, weil die Open Repair Alliance Geräte zählt und keine Termine.
- **Ein Gerät hat die Felder** `category`, `item_type`, `brand`, `model`, `age`, `problem`, `notes`, `repair_status`, `spare_parts` und `barrier`. Pflicht sind nur `category` und `item_type`.
- **Restarters hat 47 eigene Kategorien.** Sie entsprechen meist einer ORA-Gruppe. Einige ORA-Gruppen gibt es dort nicht. Die Open Repair Alliance leitet sie aus dem `item_type` ab, aus `Small kitchen item ~ Blender` wird zum Beispiel Food processor. Wir senden deshalb als `item_type` den englischen Namen aus unserem [Katalog](katalog/).

| ORA-Gruppe im Katalog | Kategorie bei Restarters |
|---|---|
| die meisten Gruppen | gleichnamige Kategorie |
| Food processor | Small kitchen item |
| Hair dryer | Hair & beauty item |
| Battery/charger/adapter, Small home electrical, Large home electrical | Misc mit Strom |
| Laptop | Laptop small, medium oder large |
| Flat screen | Flat screen nach Bildschirmgröße in Zoll |
| Unpowered - Textile | Clothing/textile |
| Unpowered - Household | Hand tool oder Misc ohne Strom |
| Unpowered - Furniture, Bicycle, Jewellery | Furniture, Bicycle, Jewellery |
| Unpowered - Other | Misc ohne Strom |

Die Zuordnung stammt aus den Open Repair Data vom Juli 2026. Dort steht bei jedem Eintrag von Restarters die ursprüngliche Kategorie neben der ORA-Gruppe. Bei Laptop und Fernseher braucht Restarters die Größe, danach fragt MANUEL, wenn sie in der Nachricht fehlt.

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

Das Ergebnis in Zammad ist ein Baum und weicht von database.sql ab, Stand 06.11.2026. Für die Übertragung brauchen wir deshalb eine feste Zuordnung.

| Stufe | Nur in Zammad | Nur in database.sql |
|---|---|---|
| Ergebnis | `No-Show`, `gelungen`, `teilweise gelungen` | `erfolgreich abgeschlossen` |
| Vertagt weil | `Ersatzteilbesorgung durch Gast`, `Ersatzteilbesorgung durch Repair Café`, `Gerät nicht komplett`, `zu lange Wartezeit` | `Ersatzteilbesorgung durch Besucher`, `Ersatzteilbesorgung durch Reparateur` |
| Nicht erfolgt weil | `Fehler nicht gefunden` | `Sonstiges` |
| Abbruch weil | keine Unterwerte | `technisch nicht möglich`, `nicht betriebssicher` |

Auch die Kategorien in database.sql sind nicht aktuell. Das Formular auf reparatur-initiativen.org zeigt am 06.11.2026 `Elektro divers` statt `Elektro Sonstiges` und enthält `3D-Drucker` und `3D-Stift`, die in database.sql fehlen. Bei der Stromversorgung bietet es `mit Netzteil`, `230 V`, `Batterie`, `Akku` und `ohne Kabel (Mechanik)` an. Als Quelle für die Auswahl in Zammad gilt deshalb die Liste im Formular. Das Formular erlaubt außerdem unter `Kategorie nicht vorhanden?` eine eigene Unterkategorie mit Oberkategorie und Namen ab 3 Zeichen, ebenso `Marke nicht vorhanden?` für neue Marken. Passt keine Kategorie sicher, schlägt MANUEL deshalb eine neue Unterkategorie vor, statt eine unpassende zu wählen. Ein Mensch bestätigt sie.

Die Kategorienliste enthält Dopplungen. Marken stehen neben Gattungen wie `Sodastream` und `Wassersprudler`, Schreibweisen wie `Fön` und `Föhn`, und 21 Namen stehen unter mehreren Oberkategorien. Welche gleichwertig sind, halten wir in [eval/decision/gleichwertig.tsv](eval/decision/gleichwertig.tsv) fest. Die Gattung geht vor, die Marke kommt ins Feld Marke. Die Liste besprechen wir mit der anstiftung, weil ihr die Kategorien gehören.

Unsichere Einordnungen klärt ein Mensch mit einer Zahl. Liegt die Sicherheit unter 70 Prozent, schreibt MANUEL eine interne Notiz mit drei bis fünf nummerierten Vorschlägen ins Ticket, und Engagierte antworten etwa mit `2`. Die Grundlage steht in der [Einordnung](docs/einordnung.md), Schritt 10.

Die Kategorie ist mehr als ein Feld für die Statistik. Von ihr hängen die Artikel aus der Wissensdatenbank, der Reparaturansatz und die passenden Helfenden ab. Eine falsche Kategorie schickt die Reparatur in die falsche Richtung. Aus dem Stabmixer wird ein Spielzeug, aus dem Akku-Ladegerät ein CD-Player. Nicht jeder Fehler wiegt gleich. Bleibt er in derselben ORA-Gruppe, etwa Standmixer statt Mixer, passen die Vorschläge meist trotzdem. Landet er in einer anderen Gruppe, sind sie wertlos oder irreführend. Deshalb messen wir beides getrennt, und unsichere Fälle fragt MANUEL lieber nach, als sie einzutragen. Damit Beschreibungen und Synonyme die Verwechslungen verringern, gibt es den [Katalog](katalog/).

Die Ersatzteilwerte sind nur anders benannt und lassen sich direkt zuordnen, ebenso `gelungen` und `erfolgreich abgeschlossen`. Offen sind `teilweise gelungen`, die beiden zusätzlichen Gründe für die Vertagung, `Fehler nicht gefunden`, das in database.sql vermutlich dem Feld defect_found entspricht, und die Gründe für den Abbruch.

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
- [ ] Termin als eigenes Datumsfeld anlegen und beim Umzug bestehende Wartezeiten übernehmen, die angepasste ticket.rb kommt nicht mit, siehe [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md)
- [ ] Zammad-Benutzer für MANUEL mit API-Token anlegen, beschränkt auf die Gruppe des Repair Cafés
- [ ] Felder in Zammad prüfen und anlegen, also Art des Geräts, Defekt, Stromversorgung, Marke, Bezeichnung, Baujahr, Lösung und Ergebnis mit festen Auswahlwerten, die zu den Laufzetteln von reparatur-initiativen.org passen
- [ ] Auswahlwerte und IDs aus database.sql von mapped-repair-events übernehmen, die Kategorien als Baumauswahl, die Marke als Textfeld
- [ ] Für jeden Auswahlwert eine kurze Beschreibung hinterlegen, weil die Agenten sie als Kontext nutzen
- [ ] Zusätzliche Felder aus der Datenpotenzialanalyse anlegen, also wer repariert hat, Dauer der Reparatur, wieder aufgenommen und Werbung durch
- [ ] Mit der anstiftung klären, ob database.sql dem aktuellen Stand der Kategorien und Marken auf reparatur-initiativen.org entspricht
- [ ] Feld für die Einwilligung in den Newsletter anlegen
- [ ] Über [Core Workflows](https://admin-docs.zammad.org/en/latest/system/core-workflows.html) nur die Felder zeigen, die beim Repair Café gerade gebraucht werden, zum Beispiel Lösung und Ergebnis erst nach der Reparatur
- [ ] [Übersichten](https://admin-docs.zammad.org/en/latest/manage/overviews.html) für das Repair Café anlegen, etwa Termine des nächsten Repair Cafés und offene Reparaturen
- [ ] Löschfristen in Zammad umsetzen, Tickets des Repair Cafés 3 Jahre nach Abschluss, Anfragen ohne Erscheinen nach 3 Monaten, siehe Abschnitt Datenschutz im [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md)
- [ ] Kurzen Datenschutzhinweis für Gäste schreiben, der auch die Unterstützung durch ein lokales Sprachmodell nennt
- [ ] MANUEL in das Verzeichnis von Verarbeitungstätigkeiten aufnehmen, mit Zweck, verarbeiteten Feldern, lokaler Verarbeitung auf dem Mini-PC und Speicherdauer der Prompts in Ollama und Open WebUI
- [ ] Standort, Stromversorgung und LAN-Anschluss im Makerspace klären
- [ ] Zuständige Engagierte für Betrieb, Prompts und Auswertung finden

### Phase 0b Voraussetzungen aus dem IT-Plan

- [ ] Stufe 1 aus dem [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md) umsetzen, also Zugangs-VM mit authentik, NetBird und Vaultwarden und Helpdesk-VM mit Zammad

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
- [ ] Host in it-infrastructure aufnehmen und den Arcane-Agenten ausrollen, für Ollama und Open WebUI mit automatischen Updates
- [ ] resticker einrichten und das Volume mit den Modellen vom Backup ausschließen, weil sich Modelle jederzeit neu laden lassen
- [ ] Push-Monitor in Uptime Kuma anlegen
- [ ] Beszel-Agenten ausrollen und Alarme für Plattenplatz, Arbeitsspeicher und Temperatur anlegen
- [ ] NetBird-Client auf dem Mini-PC einrichten, auf uCore per rpm-ostree oder als Container mit Host-Netzwerk
- [ ] Startreihenfolge in systemd festlegen, sodass NetBird vor Docker läuft
- [ ] Zugriffsregeln in NetBird anlegen, sodass die Helpdesk-VM nur den Port von Ollama und Admins nur SSH erreichen

### Phase 2 Inferenz

- [ ] GPU-Stack prüfen mit vulkaninfo und Zugriff auf /dev/dri im Container
- [x] Speicherzuteilung für die GPU über UMA und GTT-Limit testen und dokumentieren, Ergebnis 16 GiB UMA ohne Kernel-Parameter, siehe docs/benchmarks.md
- [ ] Rolle ollama in it-infrastructure anlegen und den Port nur an die NetBird-Adresse binden, weil Ollama keine Anmeldung kennt und Docker die Firewall des Hosts umgeht
- [ ] Prüfen, dass Ollama aus dem LAN und dem Gäste-WLAN des Makerspace nicht erreichbar ist
- [ ] Kontrollieren, dass Modelle wirklich auf der GPU laufen und nicht auf der CPU, zum Beispiel an der GPU-Auslastung in Beszel
- [ ] Leistungsprofil und TDP im BIOS auf Dauerbetrieb einstellen und den Einfluss auf die Geschwindigkeit messen
- [ ] Vulkan und ROCm mit llama-bench vergleichen. Die [Ollama-Doku zu GPUs](https://github.com/ollama/ollama/blob/main/docs/gpu.mdx) führt gfx1150 für ROCm v7, ältere [Erfahrungen im Framework-Forum](https://community.frame.work/t/amd-rocm-does-not-support-the-amd-ryzen-ai-300-series-gpus/68767) waren gemischt. Für Vulkan braucht der Container die Gruppe render und für Angaben zum Grafikspeicher die Capability cap_perfmon
- [ ] `OLLAMA_IGPU_ENABLE=1` setzen. Ollama verwirft integrierte AMD-GPUs standardmäßig und lässt nur gfx1151 zu, siehe [discover/runner.go](https://github.com/ollama/ollama/blob/main/discover/runner.go). Ohne die Variable läuft auf dem HX 370 mit gfx1150 alles unbemerkt auf der CPU
- [ ] `OLLAMA_CONTEXT_LENGTH` fest auf etwa 32768 setzen. Zammad schickt keine Kontextlänge mit, und Ollama wählt sonst je nach erkanntem Grafikspeicher 4K, 32K oder 256K, siehe [envconfig/config.go](https://github.com/ollama/ollama/blob/main/envconfig/config.go). Bei 4K würden lange Prompts wie der des Ticket Categorizer still abgeschnitten
- [ ] `OLLAMA_KEEP_ALIVE` hoch setzen, damit das Modell beim Repair Café nicht nach 5 Minuten Pause entladen wird, und `OLLAMA_MAX_LOADED_MODELS` so wählen, dass Sprach- und Embedding-Modell gleichzeitig geladen bleiben
- [ ] Startmodell [qwen3.6:35b-a3b](https://ollama.com/library/qwen3.6:35b-a3b) laden
- [x] UMA und GTT-Limit so einstellen, dass die GPU deutlich mehr als 24 GB nutzen darf
- [ ] Embedding-Modell [bge-m3](https://ollama.com/library/bge-m3) laden und prüfen, dass es zusammen mit dem Sprachmodell in den Speicher passt
- [ ] Wechselzeit zwischen schnellem und großem Modell messen, mit Modell im Zwischenspeicher und nach einem Neustart
- [ ] Geschwindigkeit messen und mit qwen3.6:35b-a3b-mtp-q4_K_M, qwen3.6:35b-a3b-q8_0 und qwen3.6:27b vergleichen, Ergebnisse in docs/benchmarks.md festhalten
- [ ] Optional die NPU mit [AMD Lemonade](https://github.com/lemonade-sdk/lemonade) ausprobieren

### Phase 3 Prompts und Tests

- [ ] Rolle open-webui anlegen und Konten für die beteiligten Engagierten einrichten
- [ ] Testsatz aus abgeschlossenen Repair-Café-Tickets exportieren und pseudonymisieren, nur lokal speichern
- [ ] Extraktionsregeln und Anweisungen für die Agenten sowie die Textwerkzeuge nach den Gedanken oben in prompts/ ablegen
- [ ] Skript in eval/ schreiben, das Modelle und Prompts gegen den Testsatz laufen lässt
- [ ] Bewertungskriterien festlegen, zum Beispiel richtige Kategorie und Nützlichkeit des Vorschlags aus Sicht der Engagierten
- [ ] Decision-Modell d3 an deutschen Beispiel-Tickets prüfen, vor allem das Kriterium sicherheitsrelevant. Übersehene Fälle wie Mikrowelle, Akku, Netzspannung und Gas zählen schwerer als Fehlalarme, die Schwelle wird danach gewählt
- [ ] Schnelles und großes Modell am Testsatz vergleichen und entscheiden, ob sich die Eskalation lohnt
- [ ] Beim Repair Café im November Vorschläge live in Open WebUI testen und Rückmeldungen sammeln
- [ ] Auslesen von Fotos vom Typenschild mit dem Hauptmodell an Beispielfotos testen, ein Mensch bestätigt die Felder, siehe [ADR 34](docs/adr/0034-jedes-geraet-mit-ticket-und-typenschild-erfassen.adoc)
- [ ] Spalte „spontan“ im Blatt Eingabe der Statistik anlegen, damit die [Sharecard](sharecard/README.md) spontane Gäste zeigt

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
- [ ] Prüfen, dass Vorschläge von MANUEL im Ticket gut erkennbar sind und Engagierte sie mit wenigen Klicks übernehmen oder korrigieren können, auch auf Tablet und Smartphone
- [ ] Beim Repair Café im Dezember im Echtbetrieb einsetzen und Rückmeldungen zu den Notizen sammeln
- [ ] Falls sich die Eskalation lohnt, Auslöser in Zammad anlegen und Anfragen in n8n in eine Warteschlange stellen, weil immer nur eine Anfrage gleichzeitig läuft
- [ ] Ablauf am Empfang anpassen, jedes Gerät bekommt ein Ticket und spontane Gäste den Tag `spontan`, siehe [ADR 34](docs/adr/0034-jedes-geraet-mit-ticket-und-typenschild-erfassen.adoc)
- [ ] Stromversorgung aus der Kategorie im Katalog setzen und das ungefähre Alter in der Rückfrage erfragen
- [ ] Feld „repariert von“ mit den Werten Gast selbst, Gast mit Hilfe und Engagierte anlegen, siehe [ADR 32](docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc)
- [ ] KI-Rückmeldung von Zammad an den KI-Agenten prüfen und den Export unter KI, Feedback & Logs testen

### Phase 5 Wissensdatenbank und n8n

- [ ] Wissensdatenbank in Zammad für Reparaturanleitungen einrichten und aus erfolgreichen Reparaturen Artikel erzeugen, die Engagierte vor der Veröffentlichung prüfen
- [ ] Rolle n8n in it-infrastructure für die Helpdesk-VM anlegen, siehe [n8n-Doku zum Selbsthosten](https://docs.n8n.io/hosting/), hinter Traefik mit Anmeldung und mit Sicherung per resticker
- [ ] Workflow für Statistik bauen, der Ergebnisse zählt und Freitexte zu fehlendem Werkzeug zusammenfasst
- [ ] Workflows als JSON nach n8n-workflows/ exportieren
- [ ] Mit der anstiftung per Issue in mapped-repair-events klären, ob sie schreibende Endpunkte für Laufzettel und Neuigkeiten annehmen würde
- [ ] Felder in Zammad auf die Felder der Laufzettel abbilden, damit die Daten ohne Nacharbeit übertragbar sind
- [ ] Endpunkte in mapped-repair-events umsetzen und als Pull Request einreichen
- [ ] Workflow bauen, der nach dem Repair Café die Geräte über die API von Restarters.net meldet, siehe [ADR 14](docs/adr/0014-reparaturen-ueber-restarters-melden.adoc)
- [ ] Nachmeldung der Geräte von 2024 bis 2026 an Restarters nach Freigabe der Vorschau senden, siehe [ADR 36](docs/adr/0036-reparaturen-ab-2024-an-restarters-nachmelden.adoc)
- [ ] SearXNG in it-infrastructure auf der Helpdesk-VM einrichten und den Workflow für die Suche nach Anleitungen bauen, siehe [ADR 35](docs/adr/0035-anleitungen-ueber-eine-eigene-suche-finden.adoc)
- [ ] Workflow für die Sharecard bauen, der die Zahlen aus Zammad holt, Highlights über den Tag `highlight` findet und die Karte als Entwurf ans Team schickt
- [ ] Workflow für Terminvorschläge bauen, der Anmeldungen in Nuudel auswertet
- [ ] Workflow für den Newsletter bauen, der nur Gäste anmeldet, für die Engagierte den Wunsch im Feld zur Einwilligung vermerkt haben. Die KI-Agenten dürfen dieses Feld nie setzen. Übermittelt wird nur die E-Mail-Adresse, der Endpunkt löst die Bestätigungsmail aus, jede Übermittlung erscheint einmalig als interne Notiz im Ticket und Fehler werden gemeldet

### Phase 6 Abschluss und Veröffentlichung

- [ ] Kennzahlen aus dem Antrag erheben, also Reparaturquote, Reparaturen durch Gäste und neue Engagierte, Rückmeldungen zu Vorschlägen und gemeldete Reparaturen
- [ ] Dokumentation in docs/ vervollständigen, sodass andere Reparaturinitiativen MANUEL nachbauen können
- [ ] MANUEL als Fallstudie in [case-study](case-study/manuel.adoc) dokumentieren, mit Methodik, Benchmarks, Quellen und Ergebnissen nach dem Vorbild der [Datenpotenzialanalyse](datenpotenzialanalyse-repairc-cafe-gt/README.md), siehe [ADR 30](docs/adr/0030-rahmen-der-fallstudie-festlegen.adoc). Sie entsteht vom Groben zum Feinen
  - [ ] Stufe 1 im November 2026, Gliederung, Stichpunkte je Kapitel und Quellen
  - [ ] Stufe 2 im November und Dezember 2026, Reihenfolge der Absätze, Abbildungen und fehlende Daten wie Läufe für das Beispiel k01 und die Strommessung
  - [ ] Stufe 3 von Dezember 2026 bis Februar 2027, ausformulieren, zuerst die Kapitel 2, 5, 6 und 9, dann parallel zur Erprobung die Kapitel 7 bis 10
  - [ ] Stufe 4 im März 2027, Zusammenfassung, Abstract auf Englisch, Gegenlesen durch das Team und Version 1.0 mit dem Sachbericht
- [ ] Eigenständige compose.yaml als Beispiel für Nachnutzende bereitstellen
- [ ] Im Build-Workflow mit [syft](https://github.com/anchore/syft) eine SBOM des Images erzeugen und sie mit cosign als [Attestation](https://docs.sigstore.dev/cosign/verifying/attestation/) an das Image hängen, damit Nachnutzende Bibliotheken und Lizenzen prüfen können
- [ ] Dateien nach [REUSE](https://reuse.software/) mit SPDX-Angaben zu Lizenz und Urheber kennzeichnen, weil das Repo CC0 und Apache 2.0 mischt
- [ ] DSEE-Logo mit »Gefördert durch« in die README aufnehmen
- [ ] Ergebnisse veröffentlichen, zum Beispiel auf unserer Website, im Netzwerk Reparatur-Initiativen der anstiftung und in den sozialen Medien
- [ ] Belege der Veröffentlichung für den Sachbericht sammeln
- [ ] Verwendungsnachweis bis 31.03.2027 im Förderportal einreichen

## Ausblick

Im Antrag haben wir angekündigt, MANUEL später auch für Fragen wie »Wer verfügt über welche Kenntnisse?« und »Welche Werkzeuge und Maschinen stehen im Verein zur Verfügung?« einzusetzen.

- **Tags für Techniken.** Vorrang hat die Wissensdatenbank. Tickets werden nach drei Jahren gelöscht, Artikel bleiben und wachsen weiter, deshalb verlinkt MANUEL zuerst passende Artikel. Tags wie löten oder 3d-druck dienen danach vor allem als Ordnung für die Artikel. An Tickets bleiben sie optional, zum Beispiel um zu sehen, wie viele Tickets eines Termins Löten brauchen.
- **Discourse als Wissensbasis und Chatbot.** Für das Forum gibt es im alten Repo die Rolle [discourse](https://github.com/makerspace-gt/docker-compose-server/tree/main/roles/discourse). Das mitgelieferte Plugin [discourse-ai](https://github.com/discourse/discourse/tree/main/plugins/discourse-ai) kann Ollama [direkt ansprechen](https://github.com/discourse/discourse/blob/main/plugins/discourse-ai/lib/completions/endpoints/ollama.rb). Es bringt einen KI-Bot mit eigenen Rollen und hinterlegten Dokumenten, Zusammenfassungen, semantische Suche und ähnliche Themen per Embedding mit. Ein Bot im Forum könnte Fragen zu Kenntnissen der Mitglieder und zu Werkzeugen beantworten, gestützt auf Beiträge und Dokumente des Vereins.
- **Signal als Kanal für Benachrichtigungen.** Für [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api) auf Basis von [signal-cli](https://github.com/AsamK/signal-cli) gibt es im alten Repo die Rolle [signal-cli-rest-api](https://github.com/makerspace-gt/docker-compose-server/tree/main/roles/signal-cli-rest-api). n8n könnte darüber Engagierte an Termine erinnern oder über neue Anmeldungen informieren. Später wäre auch ein Signal-Bot denkbar, der Fragen an MANUEL weiterleitet. Gäste schreiben wir nur mit ihrer Einwilligung an.

Beide Dienste würden denselben Ollama-Server über NetBird nutzen. Weitere Dienste wie Vikunja und LanguageTool beschreibt der [Plan für den Neuaufbau der IT](https://github.com/makerspace-gt/it-infrastructure/blob/main/PLAN.md).

## Zeitplan

| Zeitraum | Phase |
|---|---|
| bis Lieferung | Phase 0, 0b mit Stufe 1 des IT-Plans und 0c |
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
├── it-infrastructure/      Submodul mit der IT-Infrastruktur des Vereins als Code
└── ollama/                Submodul mit dem Quellcode von Ollama, MIT
```

Das Submodul von Ollama ist groß und deshalb in `.gitmodules` als shallow markiert. Die Quellen der übrigen Dienste liegen in it-infrastructure unter `upstream/`. Unsere eigenen exportierten Workflows liegen in `n8n-workflows/`, getrennt vom Submodul `upstream/n8n` in it-infrastructure.

Geheimnisse wie API-Token gehören nicht hierher. Sie liegen verschlüsselt im Ansible Vault von it-infrastructure.
