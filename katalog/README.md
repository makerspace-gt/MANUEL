# Katalog der Gegenstände

Der Katalog beschreibt die Gegenstände, die Gäste ins Repair Café bringen. Er dient zwei Zwecken. Menschen sehen, was mit einem Eintrag gemeint ist und wie er sich von ähnlichen Einträgen abgrenzt. MANUEL nutzt Beschreibung und Synonyme, um Tickets einzuordnen.

Jeder Eintrag hat einen deutschen und einen englischen Teil. Der deutsche Teil dient der Einordnung der Tickets. Mit dem englischen Teil lassen sich die Daten anderer Initiativen in den Open Repair Data zuordnen.

## Spalten von kategorien.tsv

| Spalte | Inhalt |
|---|---|
| name | bevorzugter Name |
| beschreibung | ein Satz, was gemeint ist und wovon es sich abgrenzt |
| synonyme | andere Wörter für denselben Gegenstand, getrennt durch einen senkrechten Strich |
| name_en, beschreibung_en, synonyme_en | dasselbe auf Englisch |
| ora_gruppe | Produktkategorie nach dem Open Repair Data Standard |
| zwischenkategorie | eigene feinere Gruppe, wo die ORA-Gruppe zu grob ist |
| strom | übliche Stromversorgung mit den Werten des Laufzettels |
| formular_ids | IDs der Kategorien im Laufzettel auf reparatur-initiativen.org |
| status | Entwurf oder bestätigt |

## Quellen

- Kategorien des Laufzettels der [anstiftung](https://www.reparatur-initiativen.de/), Code in [mapped-repair-events](https://github.com/anstiftung/mapped-repair-events). Der Katalog verweist nur über die IDs darauf.
- [Open Repair Data Standard](https://standard.openrepair.org/) der Open Repair Alliance für die ORA-Gruppen.
- [Open Repair Data](https://openrepair.org/open-data/downloads/) für die Häufigkeit der Einträge und die englischen Bezeichnungen, vor allem von Repair Café International und Repair Cafe Wales.

Die Daten der Quellen liegen nicht in diesem Repo.

## Lizenz

Der Katalog steht unter [CC BY-SA 4.0](../LICENSES/CC-BY-SA-4.0.txt). Ein Teil der englischen Bezeichnungen stammt aus den [Open Repair Data](https://openrepair.org/open-data/downloads/) der Open Repair Alliance, die ebenfalls unter CC BY-SA 4.0 stehen.

## Stand

Ein Entwurf für die 225 häufigsten Einträge. Sie decken 90 Prozent der deutschen Reparaturen in den Open Repair Data ab. [pruefen.py](pruefen.py) stellt sicher, dass kein Synonym zu zwei Einträgen gehört. Welche Gegenstände gleich gelten, entscheidet das Team in [gleichwertig.tsv](../eval/decision/gleichwertig.tsv).
