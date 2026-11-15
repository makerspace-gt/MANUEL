# Zammad für eine Reparatur-Initiative einrichten

Diese Dateien richten ein Zammad so ein, wie MANUEL es erwartet, so viel wie möglich als Code ([ADR 54](../docs/adr/0054-zammad-als-code-einrichten.adoc)). Sie enthalten nichts, was nur für das Repair Café des Makerspace Gütersloh gilt, auch nicht den Namen Repair Café, den nur ein Netzwerk nutzt, und lassen sich mit docker compose bei jeder Initiative nachnutzen. Alle Läufe lassen sich wiederholen, vorhandene Einträge werden aktualisiert statt doppelt angelegt.

| Datei | Inhalt |
|---|---|
| [compose.yml](compose.yml) | Dienst `manuel-setup` zusätzlich zu `docker-compose.yml` aus [zammad-docker-compose](../quellen/zammad-docker-compose). Er wartet auf `zammad-init`, führt `setup.rb` aus und beendet sich. Außerdem bindet die Datei `keep_pending_time.rb` in railsserver und scheduler ein |
| [setup.rb](setup.rb) | Lädt die folgenden Dateien in dieser Reihenfolge und ändert zuletzt das Schema der Datenbank, weil Zammad danach neu startet |
| [groups.rb](groups.rb) | Gruppe Repairs mit der Untergruppe Requests, die Rollen Repair Agent und Repair Coordinator und der Agent Gast |
| [objects.rb](objects.rb) | Felder im Ticket, also Art des Geräts aus dem [Katalog](../katalog/) als durchsuchbares Baum-Feld ([ADR 59](../docs/adr/0059-art-des-geraets-als-durchsuchbares-baum-feld.adoc)), Marke, Bezeichnung, Baujahr, Alter und Angabe zum Alter, Stromversorgung, Defekt laut Anmeldung, festgestellter Defekt, Lösung, Ergebnis als Baum, Gefahren mit Mehrfachauswahl, VDE-Prüfung sowie Spenden und Bedarf für das Statistik-Ticket |
| [macros.rb](macros.rb) | Makros „Vorschlag hilfreich“ und „Vorschlag nicht hilfreich“, die je einen Tag setzen, siehe [ADR 32](../docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc) |
| [knowledge_base.rb](knowledge_base.rb) | Wissensdatenbank mit Deutsch als Hauptsprache und britischem Englisch wie bei der Open Repair Alliance, Farben und Aufbau wie im Dialog von Zammad. Eine vorhandene behält ihre Einstellungen und bekommt nur fehlende Sprachen |
| [translations.rb](translations.rb) | Deutsche Übersetzungen aller Bezeichnungen als eigene Übersetzungen in Zammad und die Wörter aus guest_wording.tsv |
| [guest_wording.tsv](guest_wording.tsv) | Gast statt Kunde in 52 Texten von Zammad, englisch und deutsch |
| [migrate_fields.rb](migrate_fields.rb) | Übernimmt die Werte älterer Felder in die neuen, stellt Regeln um und schaltet die alten Felder ab, erst als Probelauf |
| [result_tree.rb](result_tree.rb) | Werte des Ergebnisses englisch und deutsch, für `objects.rb` und `migrate_fields.rb` |
| [export_config.py](export_config.py) | Exportiert die Einstellungen eines bestehenden Zammad über die REST-API als JSON, nur lesend, die Dateien bleiben lokal |
| [event_tags.rb](event_tags.rb) | Initializer mit `ManuelEventTags.run`, stündlich über den Scheduler: Datums-Tag nach dem Termin, `next-event` aufräumen, unbestätigte Vorschläge als No-show, Monatsübersichten und ungenutzte Tags, siehe [ADR 62](../docs/adr/0062-datums-tags-und-monatsuebersichten-automatisch-pflegen.adoc) |
| [overviews.rb](overviews.rb) | Zwölf Übersichten je Monat, beim Anlegen aus |
| [scheduler.rb](scheduler.rb) | Eintrag im Scheduler für jedes geladene Modul |
| [migrate_tags.rb](migrate_tags.rb) und [legacy_tags.tsv](legacy_tags.tsv) | Gleicht alte Monats- und Sondertags an, erst als Probelauf |
| [contact_filter.rb](contact_filter.rb) | Initializer und Postmaster-Filter 6400, übernimmt Kontaktdaten aus Kontaktformular und sipgate und setzt den Typ der ersten Nachricht, siehe [ADR 63](../docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc) |
| [article_types.rb](article_types.rb) und [inbound.rb](inbound.rb) | Typ `walk-in` für den Empfang, Initializer und Anlegen samt Registrierung des Filters |
| [migrate_contacts.rb](migrate_contacts.rb) | Gleicht Nummern, Gäste von sipgate und Typen im Bestand an, erst als Probelauf |
| [ui_wording.tsv](ui_wording.tsv) | Eigene Begriffe, etwa Termin für Pending till und Kontaktformular für den Typ web |
| [keep_pending_time.rb](keep_pending_time.rb) | Initializer, der die Wartezeit behält, wenn ein Ticket den Status warten verlässt, siehe [ADR 53](../docs/adr/0053-termin-in-der-wartezeit-behalten.adoc) |

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
- Wer die Rolle Repair Agent hat, repariert und bearbeitet die Tickets beider Gruppen. Wer die Rolle Repair Coordinator hat, macht den Empfang, vereinbart Termine und führt die Statistik. Dafür pflegt die Rolle auch Makros und Textbausteine und sieht die Berichte. Artikel der Wissensdatenbank bearbeiten und freigeben beide Rollen. Die Rechte sind ein Vorschlag.
- Ein vorhandenes Zammad mit anderen Namen für Gruppen oder Rollen vorher umbenennen, sonst entsteht eine zweite. Bei uns wird die Gruppe Repair Café zu Repairs und Repair Café Anfragen zu deren Untergruppe Requests. Die Rollen Repair Café Agent und Repair Café Moderator heißen künftig Repair Agent und Repair Coordinator.
- Vorhandene Felder mit anderen Namen übernimmt `migrate_fields.rb` nach `setup.rb`, siehe [ADR 58](../docs/adr/0058-felder-des-bestehenden-zammad-uebernehmen.adoc). Ohne `MANUEL_MIGRATE=apply` ist es ein Probelauf.
- Die VDE-Prüfung kennt leer, empfohlen, ja und nein. Leer heißt, es ist noch nicht entschieden.
- Wer repariert hat, ist der Owner des Tickets. Hat der Gast selbst repariert, wird der Agent Gast Owner, siehe [ADR 32](../docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc). Er hat den Login `guest`, kein Passwort und keine E-Mail-Adresse und kann sich nicht anmelden. Ein vorhandener Agent für Gäste bekommt vorher den Login `guest`, sonst entsteht ein zweiter.
- Der Termin ist die Wartezeit mit Datum und Uhrzeit. Antwortet ein Gast, würde Zammad sie leeren. `keep_pending_time.rb` überschreibt dafür nur die Methode `reset_pending_time` statt die ganze `ticket.rb` zu ersetzen. Nach jedem Update von Zammad prüfen, ob es die Methode noch gibt, sonst steht ein Fehler im Log.
- Welche Felder wann sichtbar sind, etwa Spenden nur im Statistik-Ticket, regeln Core Workflows. Die fehlen hier noch.

Am 14.11.2026 lief `setup.rb` neunmal in der Testinstanz mit Zammad 7.2.2. Fehler und doppelte Einträge gab es nicht, beim letzten Lauf änderte sich nichts mehr. Danach lief der Dienst `manuel-setup` zweimal auf MANUEL, beim zweiten Mal ohne Änderung. Eine Antwort per Mail auf ein Ticket mit Wartezeit ließ diese ohne `keep_pending_time.rb` leer, mit der Datei blieb sie erhalten, und die Erinnerung zur Wartezeit kam weiterhin.
