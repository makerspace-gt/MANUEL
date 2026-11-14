# Katalog der Gegenstände

Der Katalog beschreibt die Gegenstände, die Gäste ins Repair Café bringen. Er dient zwei Zwecken. Menschen sehen, was mit einem Eintrag gemeint ist und wie er sich von ähnlichen Einträgen abgrenzt. MANUEL nutzt die Namen und Synonyme, um Tickets einzuordnen, und die Beschreibungen für Rückfragen mit nummerierten Vorschlägen. Dem Modell selbst helfen Beschreibungen nicht, siehe [Einordnung](../docs/einordnung.md), Schritt 14.

Jeder Eintrag hat einen deutschen und einen englischen Teil. Der deutsche Teil dient der Einordnung der Tickets. Mit dem englischen Teil lassen sich die Daten anderer Initiativen in den Open Repair Data zuordnen.

## Spalten von kategorien.tsv

Die Spalten haben nach [ADR 29](../docs/adr/0029-zielgruppe-und-sprache-festlegen.adoc) englische Namen, die Inhalte sind deutsch und englisch.

| Spalte | Inhalt |
|---|---|
| key | fester Schlüssel des Eintrags, siehe unten |
| name | bevorzugter Name |
| description | ein Satz, was gemeint ist und wovon es sich abgrenzt |
| synonyms | andere Wörter für denselben Gegenstand, getrennt durch einen senkrechten Strich |
| name_en, description_en, synonyms_en | dasselbe auf Englisch |
| ora_group | Produktkategorie nach dem Open Repair Data Standard |
| restarters_category | Kategorie auf Restarters.net, leer, wo die Größe entscheidet |
| intermediate_category | eigene feinere Gruppe, wo die ORA-Gruppe zu grob ist |
| power | übliche Stromversorgung mit den Werten des Laufzettels |
| form_ids | IDs der Kategorien im Laufzettel auf reparatur-initiativen.org, die zu diesem Eintrag gehören |
| status | Entwurf oder bestätigt |

## Schlüssel

Der Schlüssel hat die Form `ORA.Restarters.anstiftung` oder `ORA.Restarters.anstiftung.eigene`. Jeder Gegenstand soll damit eindeutig einer Gruppe der Open Repair Alliance, einer Kategorie auf Restarters.net und den Kategorien der anstiftung zugeordnet sein.

- Vorne steht die Nummer der ORA-Gruppe aus [ora-gruppen.tsv](../eval/decision/ora-gruppen.tsv). Die Gruppen ohne Strom haben in den Open Repair Data keine Nummer, sie bekommen 101 bis 106. Auch der Standard legt für sie keine Werte fest, denn der [Open Repair Data Standard](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L25-L28) ist für die Reparatur kleiner Elektrogeräte und Unterhaltungselektronik gemacht. Gegenstände ohne Strom nennt er nur in einer Überschrift, mit dem Hinweis, dass Elektrogeräte häufiger vorkommen und für die Politik wichtiger sind ([Standard](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L152-L157)). Die sechs Gruppen „Unpowered“ gibt es nur in den Daten unter [quellen/openrepair-data](../quellen/openrepair-data), in der Spalte `product_category` der Datei für Gegenstände ohne Strom. Pflicht ist im Standard nur die Kategorie des Partners, bei uns die der anstiftung. Die ORDS-Kategorie ist optional, die Zuordnung macht die ORA ([Standard](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L62-L77)).
- Als Zweites steht die ID der Kategorie auf Restarters.net aus [kategorien.csv](../quellen/restarters/kategorien.csv). Sie folgt aus der ORA-Gruppe nach [ora_to_restarters.tsv](../eval/restarters/ora_to_restarters.tsv). Bei Laptop und Flat screen entscheidet die Größe des Geräts, dort steht eine 0. Gegenstände ohne Strom aus Werkzeug und Garten bekommen Hand tool statt Misc.
- Als Drittes steht die führende ID im Laufzettel. Fasst ein Eintrag mehrere Kategorien zusammen, ist es die ID der Kategorie mit dem bevorzugten Namen oder die zuerst genannte. Synonyme und zusammengefasste Kategorien haben keinen eigenen Schlüssel, sie gehören zu ihrem Eintrag.
- Hinten steht eine eigene Unterscheidung, wo wir eine Kategorie der anstiftung aufteilen. Die Kopfhörer der anstiftung haben `11.24.459`, darunter liegen `11.24.459.1` für In-Ear und `11.24.459.2` für On- und Over-Ear. Beim allgemeinen Eintrag fragt MANUEL nach.

Beispiele sind `37.42.424` für Stabmixer mit dem Synonym Zauberstab, `23.32.404` für Radio mit Radiowecker und Kofferradio sowie `29.42.1209` für Elektrogrill mit Tischgrill und Partygrill.

Wo die Zuordnung zu Restarters offen ist, nennt die Spalte `status` den Grund, etwa „Entwurf, Größe für Restarters klären“.

Bis MANUEL in Zammad läuft, kann sich ein Schlüssel noch ändern, etwa wenn wir eine ORA-Gruppe korrigieren. Danach bleibt er fest. Ändert sich dann doch eine Gruppe, bekommt der Eintrag einen neuen Schlüssel, und der alte bleibt als Verweis stehen, damit alte Tickets zugeordnet bleiben.

## Hinweise für die Arbeit am Katalog

Stand 13.11.2026, als Vorlage für die Gruppe, die den Katalog für die Meldung an die Open Repair Alliance erarbeitet.

- **Was gemeldet wird.** Bei Restarters.net sind nur `category` und `item_type` Pflicht. In den Open Repair Data erscheint ein Gerät als „Kategorie ~ Gegenstand“, etwa „Misc ~ Telephone“. Bei groben Kategorien wie Misc ordnet die Alliance das Gerät über diesen Freitext einer Gruppe zu, aus „Misc ~ Telephone“ wird Mobile. Der Standard beschreibt dieses Vorgehen selbst. Die zusätzliche Angabe hilft bei der Zuordnung, und je einheitlicher die Kategorien des Partners sind, desto weniger Fehler, Übersetzungsprobleme und Ermessensfragen entstehen ([Standard](https://github.com/openrepair/datastandard/blob/c1a1f2979937a3a481782d3afbde1b62f9b24b58/standard.rst#L171-L181)).
- **Kann `item_type` schon die Kategorie der anstiftung tragen?** Technisch ja, es ist Freitext. In den offenen Daten stünde dann etwa „Kettle ~ Wasserkocher“, und die Alliance müsste Deutsch verstehen, um Geräte unter Misc zuzuordnen. Wir empfehlen deshalb den englischen Namen des Katalogs als `item_type`. Kategorie der anstiftung und Schlüssel des Katalogs passen ins Feld `notes` bei Restarters. Der Open Repair Data Standard exportiert dieses Feld nicht, die Zuordnung bleibt so bei uns, ohne die offenen Daten zu vermischen. Im Zweifel fragen wir bei Restarters oder der Alliance nach.
- **Was ein bestätigter Eintrag braucht.** `name_en`, `ora_group`, `restarters_category` und `power`. Danach setzt die Gruppe `status` auf bestätigt.

## Für MANUEL

[entries.py](entries.py) baut aus dem Katalog die Optionen für die Einordnung. Dafür braucht es die Liste der Kategorien des Laufzettels, die nicht in diesem Repo liegt. [check.py](check.py) prüft Schlüssel, Synonyme, ORA-Gruppen und die Stromversorgung.

## Quellen

- Kategorien des Laufzettels der [anstiftung](https://www.reparatur-initiativen.de/), Code in [mapped-repair-events](https://github.com/anstiftung/mapped-repair-events). Der Katalog verweist nur über die IDs darauf.
- [Open Repair Data Standard](https://standard.openrepair.org/) der Open Repair Alliance für die ORA-Gruppen.
- [Open Repair Data](https://openrepair.org/open-data/downloads/) für die Häufigkeit der Einträge und die englischen Bezeichnungen, vor allem von Repair Café International und Repair Cafe Wales.

Die Quellen liegen mit Stand im Ordner [quellen](../quellen), siehe [ADR 28](../docs/adr/0028-quellen-im-repo-ablegen.adoc).

## Lizenz

Der Katalog steht unter [CC BY-SA 4.0](../LICENSES/CC-BY-SA-4.0.txt). Ein Teil der englischen Bezeichnungen stammt aus den [Open Repair Data](https://openrepair.org/open-data/downloads/) der Open Repair Alliance, die ebenfalls unter CC BY-SA 4.0 stehen.

## Stand

Der Katalog enthält alle 1.089 Einträge, die nach den Zusammenfassungen übrig bleiben. Die 226 häufigsten haben Beschreibung und Synonyme auf Deutsch und Englisch, sie decken 90 Prozent der deutschen Reparaturen in den Open Repair Data ab. Bei den übrigen stehen bisher nur Name, ORA-Gruppe aus einem Entwurf und die IDs des Laufzettels. Warum Einträge zusammengefasst oder getrennt sind, steht in [gleichwertig.tsv](../eval/decision/gleichwertig.tsv).
