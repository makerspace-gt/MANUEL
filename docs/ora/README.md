# Auswertung der Open Repair Data

Diese Tabellen entstehen mit [category_matrix.py](../../eval/ora/category_matrix.py) aus den [Open Repair Data](https://github.com/openrepair/data/tree/d1b2ab5a7b05c96645f5d4afec7951fc912639e1) der Open Repair Alliance, Version 0.3 vom Juli 2026. Wie die Quelle stehen sie unter [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

| Datei | Inhalt |
|---|---|
| [partner.tsv](partner.tsv) | Partner mit Zahl der Einträge, Ländern, Jahren, Aufbau der Kategorien und Anteil gefüllter Felder |
| [kategorien-matrix.tsv](kategorien-matrix.tsv) | je ORA-Gruppe die drei häufigsten Kategorien jedes Partners und die Einträge unseres Katalogs |
| [kategorien-matrix-teil1.tsv](kategorien-matrix-teil1.tsv), [kategorien-matrix-teil2.tsv](kategorien-matrix-teil2.tsv) | dieselbe Matrix in zwei Teilen für das PDF der Fallstudie |
| [kategorien-zuordnung.tsv](kategorien-zuordnung.tsv) | jede Kategorie eines Partners mit allen ORA-Gruppen, denen die Alliance sie zugeordnet hat, bei Freitext nur Werte ab 10 Einträgen |
| [felder/uebersicht.tsv](felder/uebersicht.tsv) | je Feld Zahl der Zeilen, verschiedenen und leeren Werte und der häufigste Wert, aus [fields.R](../../eval/ora/fields.R) in R nach [ADR 49](../adr/0049-daten-mit-r-auswerten.adoc) |
| [felder/](felder) | je Feld alle verschiedenen Werte mit Anzahl bei Elektrogeräten (`eee`) und Gegenständen ohne Strom (`non_eee`). `id.tsv` und `problem.tsv` sind mit 16 und 29 MB zu groß fürs Repo und entstehen nur lokal |
