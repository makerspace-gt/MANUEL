# Zammad für eine Reparatur-Initiative einrichten

Diese Dateien richten ein Zammad so ein, wie MANUEL es erwartet, so viel wie möglich als Code ([ADR 54](../docs/adr/0054-zammad-als-code-einrichten.adoc)). Sie enthalten nichts, was nur für das Repair Café des Makerspace Gütersloh gilt, auch nicht den Namen Repair Café, den nur ein Netzwerk nutzt, und lassen sich mit docker compose bei jeder Initiative nachnutzen. Alle Läufe lassen sich wiederholen, vorhandene Einträge werden aktualisiert statt doppelt angelegt.

| Datei | Inhalt |
|---|---|
| [compose.yml](compose.yml) | Dienst `manuel-setup` zusätzlich zu `docker-compose.yml` aus [zammad-docker-compose](../quellen/zammad-docker-compose). Er wartet auf `zammad-init`, führt `setup.rb` aus und beendet sich. Außerdem bindet die Datei `keep_pending_time.rb` in railsserver und scheduler ein |
| [setup.rb](setup.rb) | Lädt die folgenden Dateien in dieser Reihenfolge und ändert zuletzt das Schema der Datenbank, weil Zammad danach neu startet |
| [system.rb](system.rb) | Macht auf einer frischen Instanz, was der Assistent von Zammad macht, also Adresse, Organisation, Sprache, Zeitzone und das erste Admin-Konto. Nur mit Adresse und Passwort des Admins aus der Umgebung, sonst wartet `setup.rb` auf den Assistenten im Browser |
| [groups.rb](groups.rb) | Gruppe Repairs mit den Untergruppen Requests und Events, die Gruppe Spam check, die Rollen Repair Agent und Repair Coordinator und der Agent Gast |
| [objects.rb](objects.rb) | Felder im Ticket, also Art des Geräts aus dem [Katalog](../katalog/) als durchsuchbares Baum-Feld ([ADR 59](../docs/adr/0059-art-des-geraets-als-durchsuchbares-baum-feld.adoc)), Marke, Bezeichnung, Baujahr, Alter und Angabe zum Alter, Stromversorgung, Defekt laut Anmeldung, festgestellter Defekt, Lösung, Ergebnis als Baum, Gefahren mit Mehrfachauswahl, VDE-Prüfung sowie Spenden und Bedarf für das Statistik-Ticket |
| [macros.rb](macros.rb) | Makros „Vorschlag hilfreich“ und „Vorschlag nicht hilfreich“, die je einen Tag setzen, siehe [ADR 32](../docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc) |
| [knowledge_base.rb](knowledge_base.rb) | Hausordnung aus `texts/house_rules.*.md` als Antwort, zunächst intern. Wissensdatenbank mit Deutsch als Hauptsprache und britischem Englisch wie bei der Open Repair Alliance, Farben und Aufbau wie im Dialog von Zammad. Eine vorhandene behält ihre Einstellungen und bekommt nur fehlende Sprachen |
| [translations.rb](translations.rb) | Deutsche Übersetzungen aller Bezeichnungen als eigene Übersetzungen in Zammad und die Wörter aus guest_wording.tsv |
| [guest_wording.tsv](guest_wording.tsv) | Gast statt Kunde in 52 Texten von Zammad, englisch und deutsch |
| [migrate_fields.rb](migrate_fields.rb) | Übernimmt die Werte älterer Felder in die neuen, stellt Regeln um und schaltet die alten Felder ab, erst als Probelauf |
| [migrate_guest_fields.rb](migrate_guest_fields.rb) | Übernimmt die Werte der älteren Felder am Gast, etwa `einverstaendnis_hausordnung` in `house_rules_consent`, stellt Regeln um und schaltet die alten Felder ab. Ohne `MANUEL_MIGRATE=apply` ein Probelauf, siehe [ADR 58](../docs/adr/0058-felder-des-bestehenden-zammad-uebernehmen.adoc) |
| [result_tree.rb](result_tree.rb) | Werte des Ergebnisses englisch und deutsch, für `objects.rb` und `migrate_fields.rb` |
| [export_tickets.py](export_tickets.py) und [import_tickets.rb](import_tickets.rb) | Liest nur die Tickets gewählter Gruppen über die API aus und spielt sie in eine frische Testinstanz ein, mit den alten Feldern für die Probe von `migrate_fields.rb`, siehe [ADR 69](../docs/adr/0069-nur-tickets-des-repair-cafe-in-die-testinstanz-uebernehmen.adoc) |
| [export_config.py](export_config.py) | Exportiert die Einstellungen eines bestehenden Zammad über die REST-API als JSON, nur lesend, die Dateien bleiben lokal |
| [event_tags.rb](event_tags.rb) | Initializer mit `ManuelEventTags.run`, stündlich über den Scheduler: Datums-Tag nach dem Termin, `next-event` aufräumen, unbestätigte Vorschläge als No-show, Monatsübersichten und ungenutzte Tags, siehe [ADR 62](../docs/adr/0062-datums-tags-und-monatsuebersichten-automatisch-pflegen.adoc) |
| [overviews.rb](overviews.rb) | Zwölf Übersichten je Monat, beim Anlegen aus, dazu Next event, My repairs, Open repairs und Spam check |
| [scheduler.rb](scheduler.rb) | Eintrag im Scheduler für jedes geladene Modul |
| [migrate_tags.rb](migrate_tags.rb) und [legacy_tags.tsv](legacy_tags.tsv) | Gleicht alte Monats- und Sondertags an, erst als Probelauf |
| [contact_filter.rb](contact_filter.rb) | Initializer und Postmaster-Filter 6400, übernimmt Kontaktdaten aus Kontaktformular und sipgate, setzt den Typ der ersten Nachricht und formatiert Telefonnummern bei jedem Speichern eines Kontakts, siehe [ADR 63](../docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc) |
| [article_types.rb](article_types.rb) und [inbound.rb](inbound.rb) | Typ `walk-in` für den Empfang, Initializer und Anlegen samt Registrierung des Filters. `inbound.rb` setzt außerdem `system_bcc` aus `MANUEL_SENT_BCC` und legt mit `MANUEL_SPAM_FOLDER` einen Kanal für Spam check an, siehe [ADR 65](../docs/adr/0065-postfach-archivieren-und-aufbewahrung-begrenzen.adoc) |
| [migrate_contacts.rb](migrate_contacts.rb) | Gleicht Nummern, Gäste von sipgate und Typen im Bestand an, erst als Probelauf |
| [press.rb](press.rb) | Organisation Presse, ein Trigger mit der Pressemitteilung je Redaktion, beim Anlegen aus, und eine Notiz für soziale Medien, beides auf die Erinnerung vor dem Termin, siehe [ADR 66](../docs/adr/0066-pressemitteilung-und-beitraege-aus-vorlagen.adoc) |
| [workflows.rb](workflows.rb) | Trigger und geplante Aufgaben, also `next-event`, Verschieben nach Repairs, Eingangsbestätigung mit Hausordnung, Nachfrage und Absage bei Terminvorschlägen, Erinnerung und Löschfristen. Regeln für Mails an Gäste und Löschungen sind beim Anlegen aus, ein späterer Lauf ändert `active` nie. Alte Namen übernimmt `LEGACY_NAMES` |
| [texts/](texts/) | Texte für Mails an Gäste, Hausordnung, Pressemitteilung und Signatur |
| [checklists.rb](checklists.rb), [text_modules.rb](text_modules.rb) und [templates.rb](templates.rb) | Checkliste „Repairs“ mit 9 Punkten aus `texts/checklist.<Sprache>.txt`, Textbausteine aus `texts/text_modules.de.tsv` und die Vorlage „Walk-in“ für Spontane. Alte Namen werden übernommen |
| [tree_select_label.rb](tree_select_label.rb) | Initializer, setzt bei Baum-Feldern in Platzhaltern und im Kontext der KI-Agenten den Namen der Option statt des Schlüssels ein, für den Betreff aus Marke und Gerät, siehe [ADR 67](../docs/adr/0067-betreff-aus-marke-und-art-schreiben.adoc) |
| [category_check.rb](category_check.rb) | Initializer, fragt alle fünf Minuten den Dienst in [category_check/](../category_check/README.md) nach der Art des Geräts und schreibt bei Abweichung eine Notiz, siehe [ADR 68](../docs/adr/0068-art-des-geraets-mit-d3-pruefen.adoc) |
| [ai.rb](ai.rb) | Ollama als KI-Anbieter, wenn `MANUEL_OLLAMA_URL` gesetzt ist, und Ticket Categorizer für die Art des Geräts mit den A- und B-Einträgen. Die Beschreibung jeder Option beginnt mit dem deutschen Namen, weil Zammad den Schlüssel als Label schickt, siehe [ADR 40](../docs/adr/0040-mit-dem-ticket-categorizer-von-zammad-beginnen.adoc) und [ADR 59](../docs/adr/0059-art-des-geraets-als-durchsuchbares-baum-feld.adoc) |
| [agents.rb](agents.rb) und [prompts/](prompts/) | Custom AI Agent für Lösungsansatz oder Nachfragen als interne Notiz, Trigger bei `next-event` und Makro „Lösungsansatz von MANUEL“, siehe [ADR 61](../docs/adr/0061-loesungsansatz-eine-woche-vor-dem-termin-schreiben.adoc) |
| [agent_note.rb](agent_note.rb) | Initializer, damit KI-Agenten interne Notizen anlegen können |
| [core_workflows.rb](core_workflows.rb) | Blendet die Felder aus `objects.rb` aus und zeigt sie je Gruppe, Gerätefelder in Repairs und Requests, Spenden und Bedarf in Events |
| [ui_wording.tsv](ui_wording.tsv) | Eigene Begriffe, etwa Termin für Pending till und Kontaktformular für den Typ web |
| [voicemail.rb](voicemail.rb) | Initializer, schickt neue Voicemails an whisper.cpp unter `MANUEL_WHISPER_URL` und schreibt den Text als interne Notiz, siehe [ADR 64](../docs/adr/0064-voicemails-lokal-transkribieren.adoc) |
| [keep_pending_time.rb](keep_pending_time.rb) | Initializer, der die Wartezeit behält, wenn ein Ticket den Status warten verlässt, siehe [ADR 53](../docs/adr/0053-termin-in-der-wartezeit-behalten.adoc) |

## Einstellungen

Optionale Umgebungsvariablen für `manuel-setup` und den Scheduler in [compose.yml](compose.yml). Ohne Wert fällt der Teil weg.

| Variable | Wirkung |
|---|---|
| `MANUEL_SENT_BCC` | Adresse für Kopien gesendeter Mails, wird `system_bcc`, siehe [ADR 65](../docs/adr/0065-postfach-archivieren-und-aufbewahrung-begrenzen.adoc) |
| `MANUEL_SPAM_FOLDER` | Ordner, den ein zweiter Kanal in die Gruppe Spam check holt, etwa `Spam` |
| `MANUEL_EVENT_REMINDER_FROM` und `MANUEL_EVENT_REMINDER_SUBJECT` | Absender und Teil des Betreffs der Erinnerung vor dem Termin, Auslöser für Pressemitteilung und Notiz, siehe [ADR 66](../docs/adr/0066-pressemitteilung-und-beitraege-aus-vorlagen.adoc) |
| `MANUEL_STATISTICS_CUSTOMER`, `MANUEL_STATISTICS_SHEET_URL` und `MANUEL_FORUM_URL` | Gast des Statistik-Tickets als Login und die Links in dessen Notiz. Der Link zum Bearbeiten der Tabelle gehört nicht ins Repo |
| `MANUEL_URL`, `MANUEL_ORGANIZATION`, `MANUEL_LOCALE`, `MANUEL_ADMIN_EMAIL`, `MANUEL_ADMIN_PASSWORD` und `MANUEL_ADMIN_NAME` | Einrichtung einer frischen Instanz ohne den Assistenten im Browser, siehe [system.rb](system.rb). Ohne Adresse und Passwort des Admins wartet `setup.rb` auf den Assistenten. Das Passwort gehört nicht ins Repo |
| `MANUEL_AUTO_REPLY_EXCEPT` | Adressen durch Komma getrennt, die nie eine Eingangsbestätigung bekommen, etwa sipgate. Von Hand eingetragene Ausnahmen bleiben |
| `MANUEL_OLLAMA_URL`, `MANUEL_OLLAMA_MODEL` und `MANUEL_OLLAMA_EMBEDDING_MODEL` | Ollama als KI-Anbieter mit Sprach- und Embedding-Modell, siehe [ai.rb](ai.rb). Ohne Adresse bleibt ein von Hand eingetragener Anbieter unverändert |
| `MANUEL_CATEGORIZER_CLASSES` | Liste der Klassen A, B und C, Standard `eval/categorizer/abc.tsv`. Der Categorizer bekommt die A- und B-Einträge, siehe [ADR 40](../docs/adr/0040-mit-dem-ticket-categorizer-von-zammad-beginnen.adoc) |
| `MANUEL_CATEGORY_CHECK_URL` | Adresse des Dienstes zur Prüfung der Art mit `d3:9b`, siehe [ADR 68](../docs/adr/0068-art-des-geraets-mit-d3-pruefen.adoc) |
| `MANUEL_WHISPER_URL` | Adresse von whisper.cpp für Voicemails, siehe [ADR 64](../docs/adr/0064-voicemails-lokal-transkribieren.adoc) |

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
- Wer die Rolle Repair Agent hat, repariert und bearbeitet die Tickets in Repairs. Wer die Rolle Repair Coordinator hat, macht den Empfang, vereinbart Termine und führt die Statistik, dafür hat die Rolle auch Requests, Events und Spam check. Setup setzt die Zugriffe auf diese Gruppen genau, Zugriffe auf andere Gruppen bleiben. Dafür pflegt die Rolle auch Makros und Textbausteine und sieht die Berichte. Artikel der Wissensdatenbank bearbeiten und freigeben beide Rollen. Die Rechte sind ein Vorschlag.
- Ein vorhandenes Zammad mit anderen Namen für Gruppen oder Rollen vorher umbenennen, sonst entsteht eine zweite. Bei uns wird die Gruppe Repair Café zu Repairs und Repair Café Anfragen zu deren Untergruppe Requests. Die Rollen Repair Café Agent und Repair Café Moderator heißen künftig Repair Agent und Repair Coordinator.
- Vorhandene Felder mit anderen Namen übernehmen `migrate_fields.rb` für Tickets und `migrate_guest_fields.rb` für Gäste nach `setup.rb`, siehe [ADR 58](../docs/adr/0058-felder-des-bestehenden-zammad-uebernehmen.adoc). Ohne `MANUEL_MIGRATE=apply` ist es ein Probelauf.
- Die VDE-Prüfung kennt leer, empfohlen, ja und nein. Leer heißt, es ist noch nicht entschieden.
- Wer repariert hat, ist der Owner des Tickets. Hat der Gast selbst repariert, wird der Agent Gast Owner, siehe [ADR 32](../docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc). Er hat den Login `guest`, kein Passwort und keine E-Mail-Adresse und kann sich nicht anmelden. Ein vorhandener Agent für Gäste bekommt vorher den Login `guest`, sonst entsteht ein zweiter.
- Der Termin ist die Wartezeit mit Datum und Uhrzeit. Antwortet ein Gast, würde Zammad sie leeren. `keep_pending_time.rb` überschreibt dafür nur die Methode `reset_pending_time` statt die ganze `ticket.rb` zu ersetzen. Nach jedem Update von Zammad prüfen, ob es die Methode noch gibt, sonst steht ein Fehler im Log.
- Welche Felder wann sichtbar sind, etwa Spenden nur im Statistik-Ticket, regeln die Core Workflows aus [core_workflows.rb](core_workflows.rb).

Am 14.11.2026 lief `setup.rb` neunmal in der Testinstanz mit Zammad 7.2.2. Fehler und doppelte Einträge gab es nicht, beim letzten Lauf änderte sich nichts mehr. Danach lief der Dienst `manuel-setup` zweimal auf MANUEL, beim zweiten Mal ohne Änderung. Eine Antwort per Mail auf ein Ticket mit Wartezeit ließ diese ohne `keep_pending_time.rb` leer, mit der Datei blieb sie erhalten, und die Erinnerung zur Wartezeit kam weiterhin.


## Übernahme ins bestehende Zammad

Reihenfolge für das Zammad auf der neuen Helpdesk-VM. Vorher ein Backup. Jedes Skript mit Probelauf läuft zuerst ohne `MANUEL_MIGRATE=apply`, die Ausgabe sieht sich ein Mensch an.

1. **Version prüfen.** Zammad 7.3 oder neuer, mit Anbietern unter KI, Ticket Categorizer und Custom AI Agent. Nach jedem Update von Zammad den Suchindex mit `zammad:searchindex:rebuild` neu bauen und prüfen, ob es `reset_pending_time` noch gibt, siehe Hinweise oben und [ADR 74](../docs/adr/0074-zammad-7-3-vor-dem-start.adoc).
2. **Dateien einbinden** wie in [compose.yml](compose.yml), also die Initializer `keep_pending_time.rb`, `event_tags.rb`, `contact_filter.rb`, `article_types.rb`, `voicemail.rb`, `tree_select_label.rb`, `category_check.rb` und `agent_note.rb`, dazu `zammad/`, den Katalog und `eval/categorizer/abc.tsv` unter `/opt/manuel`. Das ersetzt die Kopie der `ticket.rb` im alten Zammad.
3. **Umbenennen**, damit nichts doppelt entsteht. Gruppe Repair Café wird Repairs, Repair Café Anfragen wird deren Untergruppe Requests, die Rollen heißen Repair Agent und Repair Coordinator, der vorhandene Agent Gast bekommt den Login `guest`.
4. **Umgebung setzen** nach der Tabelle oben. `MANUEL_OLLAMA_URL` und `MANUEL_CATEGORY_CHECK_URL` zeigen auf MANUEL über NetBird, dazu `MANUEL_WHISPER_URL`, `MANUEL_EVENT_REMINDER_FROM`, `MANUEL_AUTO_REPLY_EXCEPT`, `MANUEL_SENT_BCC` und `MANUEL_SPAM_FOLDER`. Die Variablen für den ersten Admin bleiben leer, sie gelten nur für eine frische Instanz.
5. **`setup.rb`** laufen lassen, ein zweiter Lauf ändert nichts. Neue Regeln, die Gästen schreiben, sind aus. Trigger der KI sind an, weil der Anbieter jetzt gesetzt ist.
6. **`migrate_fields.rb`** übernimmt die alten Felder, schaltet ersetzte Regeln ab, benennt `abgelehnt` in `obsolete` um und nimmt die Empfänger der Pressemitteilung in die Organisation Presse auf, siehe [ADR 58](../docs/adr/0058-felder-des-bestehenden-zammad-uebernehmen.adoc). Danach übernimmt **`migrate_guest_fields.rb`** auf dieselbe Weise die vier Felder am Gast.
7. **`migrate_tags.rb`** gleicht die Tags der Termine an. Vor dem echten Lauf in [legacy_tags.tsv](legacy_tags.tsv) die Daten für Klimawoche und Repair Day 2024 eintragen, siehe [ADR 62](../docs/adr/0062-datums-tags-und-monatsuebersichten-automatisch-pflegen.adoc).
8. **`migrate_contacts.rb`** bringt Nummern ins Format und ordnet Anrufe zu. Die Liste unklarer Nummern sieht ein Mensch durch, siehe [ADR 63](../docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc).
9. **`setup.rb` noch einmal**, damit die Trigger der Pressemitteilung zu den übernommenen Empfängern passen.
10. **Prüfen** mit einem Ticket von einer Adresse unter example.org in Requests. Es bekommt eine Art, bei Abweichung den Tag `category-differs`, mit Termin in fünf Tagen `next-event` und danach den Lösungsansatz als interne Notiz. Der Anbieter steht unter KI auf grün, kein Gast bekommt eine Mail von MANUEL, Repair Agent sieht Requests nicht. Danach das Ticket löschen.

Die Mails an Gäste schaltet das Team erst ein, wenn es die Texte freigegeben hat, siehe [ADR 60](../docs/adr/0060-ablaeufe-des-bestehenden-zammad-als-code-uebernehmen.adoc).

### Plan B, das alte Zammad

Steht die neue Helpdesk-VM am 01.12.2026 nicht, startet MANUEL am 05.12. am alten Zammad. Es läuft über die Rolle `zammad` im Repo [docker-compose-server](https://github.com/makerspace-gt/docker-compose-server) mit `VERSION=7.2`, also dem neuesten 7.2.x wie die Testinstanz. Die Routen für KI-Agenten und Anbieter gibt es dort, am 22.11.2026 ohne Anmeldung mit 403 statt 404 geprüft. Die genaue Version steht unter Admin, System, Info.

Die Rolle kann das seit dem Branch `manuel-anbindung` von docker-compose-server, noch nicht auf main. Ohne die Variable `zammad_manuel` bleibt alles wie bisher.

1. **Netzweg.** Der Server braucht Zugang zum Tailnet und eine Regel, nach der er auf MANUEL nur Ollama und die Prüfung mit d3 erreicht, siehe [ADR 47](../docs/adr/0047-dienste-zum-testen-im-tailnet-oeffnen.adoc). Später übernimmt das NetBird.
2. **Variablen** für den Host in `group_vars` oder `host_vars`:

   ```yaml
   zammad_manuel: true
   zammad_manuel_version: <Commit dieses Repos>
   zammad_manuel_env:
     MANUEL_OLLAMA_URL: http://manuel:11434
     MANUEL_CATEGORY_CHECK_URL: http://manuel:8090/check
   ```

   Die Rolle holt dieses Repo dann nach `/opt/containers/zammad/manuel`, bindet die Initializer statt `files/app/models/ticket.rb` ein und legt den Dienst `manuel-setup` im Profil `manuel` an.
3. **Backup** über resticker, dann die Rolle ausrollen.
4. **Umbenennen** wie in Schritt 3 oben, vor dem ersten `setup.rb`.
5. **Skripte** mit dem Tag `manuel-run`, erst `setup.rb`, dann die Migrationen wie in Schritt 6 bis 8 oben als Probelauf und mit `MANUEL_MIGRATE=apply`:

   ```bash
   ansible-playbook ... --tags manuel-run
   ansible-playbook ... --tags manuel-run -e zammad_manuel_run_script=migrate_fields.rb
   ansible-playbook ... --tags manuel-run -e zammad_manuel_run_script=migrate_fields.rb -e '{"zammad_manuel_run_env": {"MANUEL_MIGRATE": "apply"}}'
   ```

Danach weiter mit Schritt 9 und 10 oben.

Beim Umzug auf die Helpdesk-VM kommt alles mit dem Backup mit, `setup.rb` läuft dort nur noch einmal ohne Änderung.
