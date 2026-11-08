# Katalog der Gegenstände

Der Katalog beschreibt die Gegenstände, die Gäste ins Repair Café bringen. Er dient zwei Zwecken. Menschen sehen, was mit einem Eintrag gemeint ist und wie er sich von ähnlichen Einträgen abgrenzt. MANUEL nutzt die Namen und Synonyme, um Tickets einzuordnen, und die Beschreibungen für Rückfragen mit nummerierten Vorschlägen. Dem Modell selbst helfen Beschreibungen nicht, siehe [Einordnung](../docs/einordnung.md), Schritt 14.

Jeder Eintrag hat einen deutschen und einen englischen Teil. Der deutsche Teil dient der Einordnung der Tickets. Mit dem englischen Teil lassen sich die Daten anderer Initiativen in den Open Repair Data zuordnen.

## Spalten von kategorien.tsv

| Spalte | Inhalt |
|---|---|
| schluessel | fester Schlüssel des Eintrags, siehe unten |
| name | bevorzugter Name |
| beschreibung | ein Satz, was gemeint ist und wovon es sich abgrenzt |
| synonyme | andere Wörter für denselben Gegenstand, getrennt durch einen senkrechten Strich |
| name_en, beschreibung_en, synonyme_en | dasselbe auf Englisch |
| ora_gruppe | Produktkategorie nach dem Open Repair Data Standard |
| zwischenkategorie | eigene feinere Gruppe, wo die ORA-Gruppe zu grob ist |
| strom | übliche Stromversorgung mit den Werten des Laufzettels |
| formular_ids | IDs der Kategorien im Laufzettel auf reparatur-initiativen.org, die zu diesem Eintrag gehören |
| status | Entwurf oder bestätigt |

## Schlüssel

Der Schlüssel hat die Form `ORA.anstiftung` oder `ORA.anstiftung.eigene`.

- Vorne steht die Nummer der ORA-Gruppe aus [ora-gruppen.tsv](../eval/decision/ora-gruppen.tsv). Die Gruppen ohne Strom haben in den Open Repair Data keine Nummer, sie bekommen 101 bis 106.
- In der Mitte steht die führende ID im Laufzettel. Fasst ein Eintrag mehrere Kategorien zusammen, ist es die ID der Kategorie mit dem bevorzugten Namen oder die zuerst genannte. Synonyme und zusammengefasste Kategorien haben keinen eigenen Schlüssel, sie gehören zu ihrem Eintrag.
- Hinten steht eine eigene Unterscheidung, wo wir eine Kategorie der anstiftung aufteilen. Die Kopfhörer der anstiftung haben `11.459`, darunter liegen `11.459.1` für In-Ear und `11.459.2` für On- und Over-Ear. Beim allgemeinen Eintrag fragt MANUEL nach.

Beispiele sind `37.424` für Stabmixer mit dem Synonym Zauberstab, `23.404` für Radio mit Radiowecker und Kofferradio sowie `29.1209` für Elektrogrill mit Tischgrill und Partygrill.

Bis MANUEL in Zammad läuft, kann sich ein Schlüssel noch ändern, etwa wenn wir eine ORA-Gruppe korrigieren. Danach bleibt er fest. Ändert sich dann doch eine Gruppe, bekommt der Eintrag einen neuen Schlüssel, und der alte bleibt als Verweis stehen, damit alte Tickets zugeordnet bleiben.

## Für MANUEL

[eintraege.py](eintraege.py) baut aus dem Katalog die Optionen für die Einordnung. Dafür braucht es die Liste der Kategorien des Laufzettels, die nicht in diesem Repo liegt. [pruefen.py](pruefen.py) prüft Schlüssel, Synonyme, ORA-Gruppen und die Stromversorgung.

## Quellen

- Kategorien des Laufzettels der [anstiftung](https://www.reparatur-initiativen.de/), Code in [mapped-repair-events](https://github.com/anstiftung/mapped-repair-events). Der Katalog verweist nur über die IDs darauf.
- [Open Repair Data Standard](https://standard.openrepair.org/) der Open Repair Alliance für die ORA-Gruppen.
- [Open Repair Data](https://openrepair.org/open-data/downloads/) für die Häufigkeit der Einträge und die englischen Bezeichnungen, vor allem von Repair Café International und Repair Cafe Wales.

Die Quellen liegen mit Stand im Ordner [quellen](../quellen), siehe [ADR 28](../docs/adr/0028-quellen-im-repo-ablegen.adoc).

## Lizenz

Der Katalog steht unter [CC BY-SA 4.0](../LICENSES/CC-BY-SA-4.0.txt). Ein Teil der englischen Bezeichnungen stammt aus den [Open Repair Data](https://openrepair.org/open-data/downloads/) der Open Repair Alliance, die ebenfalls unter CC BY-SA 4.0 stehen.

## Stand

Der Katalog enthält alle 1.089 Einträge, die nach den Zusammenfassungen übrig bleiben. Die 226 häufigsten haben Beschreibung und Synonyme auf Deutsch und Englisch, sie decken 90 Prozent der deutschen Reparaturen in den Open Repair Data ab. Bei den übrigen stehen bisher nur Name, ORA-Gruppe aus einem Entwurf und die IDs des Laufzettels. Warum Einträge zusammengefasst oder getrennt sind, steht in [gleichwertig.tsv](../eval/decision/gleichwertig.tsv).
