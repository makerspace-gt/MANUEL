# Sharecard

Die Sharecard fasst einen Termin des Repair Café in einem Bild zusammen. Sie ersetzt das Resümee als Text im Forum und lässt sich auch in sozialen Medien, im Messenger des Teams, auf der Website und im Newsletter teilen. Die Entscheidung dazu steht in [ADR 33](../docs/adr/0033-resuemee-als-sharecard-teilen.adoc).

## Was auf der Karte steht

- Datum und die Zahlen angemeldet, bearbeitet und nicht erschienen. Angemeldet ist wie in der Statistik bearbeitet plus nicht erschienen, spontane Gäste zählen also mit. Sobald die Spalte „spontan“ gefüllt ist, steht dahinter „davon … spontan“.
- Ein Raster mit einem Feld je angemeldetem Gerät. Die Farbe und ein Symbol zeigen das Ergebnis, ein leeres Feld steht für nicht erschienen.
- Ein Punktdiagramm aller Termine der letzten drei Jahre mit dem Rang des Termins. 31 % heißt, dass 31 % dieser Termine höchstens so viele angemeldete Geräte hatten. Ausgefallene Termine zählen nicht mit.
- Spenden mit dem Betrag je bearbeitetem Gerät, auf Wunsch ein Highlight, der nächste Termin und der Förderhinweis der DSEE.
- Ein Alternativtext für soziale Medien in einer eigenen Datei.

Die Bestellliste bleibt im Text für das Team und kommt nicht auf die Karte.

## Aufruf

Im Wurzelverzeichnis des Repos:

```
python3 sharecard/sharecard.py Repair-Café-Statistik.ods --date 2026-11-07
python3 sharecard/sharecard.py Repair-Café-Statistik.ods --date 2026-11-07 --highlight "Ein Radio von 1985 spielt wieder"
```

Das Skript schreibt `sharecard/cards/JJJJ-MM-TT.svg`, `.png` und `.txt` mit dem Alternativtext. Für das PNG muss `rsvg-convert` installiert sein. Mit `--metric processed` zeigt die Verteilung bearbeitete statt angemeldeter Geräte, mit `--signup` lässt sich der Hinweis zur Anmeldung ändern, mit `--out` der Ordner.

## Daten und Datenschutz

Das Skript liest nur das Blatt „Eingabe“ der Statistik-Tabelle, auch eingeklappte Zeilen. Andere Blätter wie die Namensschilder überspringt es beim Einlesen. Die Tabelle selbst bleibt lokal und gehört nicht ins Repo, auf der Karte stehen nur Summen.

Bevor eine Karte entsteht, prüft das Skript die Summen. Ergeben die Ergebnisse nicht die Zahl der bearbeiteten Geräte oder ist angemeldet nicht bearbeitet plus nicht erschienen, bricht es mit einer Meldung ab.

Ein Mensch sieht jede Karte durch, bevor sie geteilt wird. Erst danach kommt sie in `sharecard/cards/` ins Repo.

## Prüfen

```
python3 -m unittest sharecard/test_sharecard.py
```

Die Tests bauen eine kleine Tabelle mit erfundenen Zahlen und einem Blatt mit Namensschildern, dessen Inhalt nie auf der Karte landen darf.

## Später aus Zammad

In der zweiten Stufe holt n8n die Zahlen direkt aus den Ergebnisfeldern der Tickets in Zammad. Spontane Gäste erkennt es nach [ADR 34](../docs/adr/0034-jedes-geraet-mit-ticket-und-typenschild-erfassen.adoc) daran, dass ihr Ticket am Tag des Termins angelegt wurde. Dann lassen sich spontane Geräte auch einzeln im Raster markieren. Highlights markieren die Engagierten mit dem Tag `highlight`, MANUEL formuliert daraus einen Satz, und ein Mensch gibt die Karte frei.
