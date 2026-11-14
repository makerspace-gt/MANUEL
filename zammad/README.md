# Zammad für eine Reparatur-Initiative einrichten

Diese Dateien richten ein Zammad so ein, wie MANUEL es erwartet. Sie enthalten nichts, was nur für das Repair Café des Makerspace Gütersloh gilt, auch nicht den Namen Repair Café, den nur ein Netzwerk nutzt, und lassen sich mit docker compose bei jeder Initiative nachnutzen. Alle Läufe lassen sich wiederholen, vorhandene Einträge werden aktualisiert statt doppelt angelegt.

| Datei | Inhalt |
|---|---|
| [compose.yml](compose.yml) | Dienst `manuel-setup` zusätzlich zu `docker-compose.yml` aus [zammad-docker-compose](../quellen/zammad-docker-compose). Er wartet auf `zammad-init`, führt `setup.rb` aus und beendet sich |
| [setup.rb](setup.rb) | Lädt die folgenden Dateien in dieser Reihenfolge und ändert zuletzt das Schema der Datenbank, weil Zammad danach neu startet |
| [groups.rb](groups.rb) | Gruppe Repairs mit der Untergruppe Requests sowie die Rollen Repair agents und Repair moderators |
| [objects.rb](objects.rb) | Felder im Ticket, also Art des Geräts aus dem [Katalog](../katalog/), Marke, Bezeichnung, Baujahr, Alter und Angabe zum Alter, Stromversorgung, Defekt laut Anmeldung, festgestellter Defekt, Lösung, Ergebnis als Baum, Repariert von, VDE-Prüfung, Termin sowie Spenden und Bedarf für das Statistik-Ticket |
| [macros.rb](macros.rb) | Makros „Vorschlag hilfreich“ und „Vorschlag nicht hilfreich“, die je einen Tag setzen, siehe [ADR 32](../docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc) |
| [translations.rb](translations.rb) | Deutsche Übersetzungen aller Bezeichnungen als eigene Übersetzungen in Zammad und die Wörter aus guest_wording.tsv |
| [guest_wording.tsv](guest_wording.tsv) | Gast statt Kunde in 52 Texten von Zammad, englisch und deutsch |

## Start

Aus dem Wurzelverzeichnis dieses Repos, mit den Submodulen:

```bash
docker compose --project-directory . \
  -f quellen/zammad-docker-compose/docker-compose.yml \
  -f zammad/compose.yml up -d
```

Nach Änderungen am Katalog oder an den Dateien läuft die Einrichtung erneut mit demselben Aufruf und `run --rm manuel-setup` statt `up -d`. Auf MANUEL übernimmt das `zammad-compose`, das zusätzlich die Testumgebung aus [testumgebung/](../testumgebung/) einbindet.

## Sprache

Namen, Werte und Bezeichnungen sind englisch. Deutsch kommt als eigene Übersetzung mit, wie unter Admin, Übersetzungen. Zammad zeigt jedem Benutzer die Felder, Auswahlwerte und Makros in der Sprache, die er eingestellt hat. Andere Sprachen lassen sich in `tr()` ergänzen.

- Wo Zammad einen Begriff schon selbst übersetzt, etwa Yes oder Result, bleibt dessen Übersetzung. Deshalb heißt das Feld für das Modell „Model or type“, denn „Model“ übersetzt Zammad mit Modell.
- Eine Übersetzung gilt in Zammad für jeden gleichen Text. Ein Name im Katalog darf deshalb nicht wie die Bezeichnung eines Felds lauten. Das Feld heißt darum „Power source“, weil der Katalog „Power supply“ für Netzteil nutzt.
- Zwischen der Initiative und den Menschen, die ihre Geräte bringen, gibt es kein Geschäft. Deshalb steht Guest und Gast statt Customer und Kunde, und für Geld gibt es nur Spenden. `guest_wording.tsv` ändert dafür 52 Texte von Zammad, etwa Customer, Edit customer und Waiting Customers. Das wirkt wie eine Änderung unter Admin, Übersetzungen. Zammad behält sie bei Updates, und Zurücksetzen holt den alten Text zurück. Ausgelassen sind lange Hilfetexte für Admins, die Vorlagen der Benachrichtigungen an Agenten und Begriffe der Technik wie Client ID.
- Die Werte in den Tickets bleiben englisch, etwa `Not repaired::Fault not found`. Die alten deutschen Werte unseres Zammad stehen in [result_mapping.tsv](../eval/ora/result_mapping.tsv).

## Hinweise

- Die Art des Geräts ist ein Auswahlfeld mit dem Schlüssel des Katalogs als Wert und dem englischen Namen als Bezeichnung, wo er fehlt dem deutschen. So bleibt der Schlüssel im Ticket, auch wenn sich ein Name ändert, siehe [ADR 13](../docs/adr/0013-eintraege-mit-hierarchischem-schluessel-kennzeichnen.adoc).
- Die Namen der Felder folgen dem Open Repair Data Standard, wo er ein Feld hat, siehe [ADR 52](../docs/adr/0052-erfasste-daten-festlegen.adoc).
- Anfragen ohne Termin liegen in der Untergruppe Repairs › Requests, mit Termin wandert das Ticket in die Gruppe Repairs. Zammad übersetzt Namen von Gruppen nicht, sie stehen für alle englisch da.
- Repair agents bearbeiten die Tickets beider Gruppen. Repair moderators pflegen zusätzlich Makros, Textbausteine und die Wissensdatenbank und sehen die Berichte. Die Rechte sind ein Vorschlag.
- Ein vorhandenes Zammad mit anderen Namen für Gruppe oder Felder vorher anpassen, sonst entsteht ein zweites Feld oder eine zweite Gruppe. Bei uns wird die Gruppe Repair Café Anfragen zur Untergruppe Requests einer neuen Gruppe Repairs, und die Rollen Repair Café Agents und Repair Café Moderators heißen künftig Repair agents und Repair moderators.
- Die VDE-Prüfung kennt leer, empfohlen, ja und nein. Leer heißt, es ist noch nicht entschieden.
- Welche Felder wann sichtbar sind, etwa Spenden nur im Statistik-Ticket, regeln Core Workflows. Die fehlen hier noch.

Am 14.11.2026 lief `setup.rb` neunmal in der Testinstanz mit Zammad 7.2.2. Fehler und doppelte Einträge gab es nicht, beim letzten Lauf änderte sich nichts mehr. Der Dienst `manuel-setup` selbst ist noch nicht gelaufen, nur seine Konfiguration ist mit `docker compose config` geprüft.
