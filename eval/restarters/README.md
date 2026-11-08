# Nachmeldung an Restarters.net

Die Reparaturen von 2024 bis 2026 sollen über die API von Restarters.net an die Open Repair Alliance gehen, bevor die Tickets nach drei Jahren gelöscht werden. Die Entscheidung steht in [ADR 36](../../docs/adr/0036-reparaturen-ab-2024-an-restarters-nachmelden.adoc).

[backfill.py](backfill.py) bereitet das vor und sendet nichts. Es liest die lokalen Exporte aus Zammad, die Sollwerte des Teams und die Statistik und schreibt eine Vorschau mit einer Zeile je Gerät. Spalten mit persönlichen Daten wie Kunde oder Owner liest es nicht. Die Vorschau enthält Ticketnummern und bleibt lokal wie die Exporte.

```
python3 eval/restarters/backfill.py --exports "../tickets-Repair Café-Created *.xlsx" \
    --targets ../tickets-kontrolle-d3.xlsx --statistics Repair-Café-Statistik.ods \
    --laufzettel ../Laufzettel-Download-Makerspace-Guetersloh-e-V-.csv --out VORSCHAU.tsv
```

## Wie die Felder entstehen

| Feld bei Restarters | Quelle |
|---|---|
| Event | letzter Termin der Statistik zwischen Anlegen und Schließen des Tickets, sonst Pending till, wenn es ein Termin ist |
| `category` | ORA-Gruppe des Eintrags im Katalog nach [ora_to_restarters.tsv](ora_to_restarters.tsv) |
| `item_type` | englischer Name des Eintrags im Katalog |
| `brand` | Feld Marke |
| `repair_status`, `barrier` | Feld Ergebnis, siehe ADR 36 |

Die Kategorie kommt aus dem Sollwert des Teams, also „Kategorie richtig“ oder der bestätigte Vorschlag in `tickets-kontrolle-d3.xlsx`.

## Befunde bei der Vorbereitung am 08.11.2026

- **Die API nimmt nur fünf Hindernisse an.** Laut Quellcode von Restarters fehlt „Item too worn out“. „nicht erfolgt::Abnutzung zu groß“ geht deshalb als End of life ohne Hindernis.
- **Defekt ist Freitext.** Das Feld hat 480 verschiedene Werte. Nach ADR 36 geht kein Freitext mit, `problem` bleibt deshalb leer.
- **Vergangene Events lassen sich per API anlegen**, mit `POST /api/v2/events`. Je nach Netzwerk muss ein Event erst freigegeben werden.
- **Sechs Termine der Statistik liegen nicht auf einem Samstag.** Von Januar bis Juni 2025 stehen dort Sonntage und Montage, etwa der 04.05.2025 für den Laufzettel vom 03.05.2025. Die Vorschau setzt sie auf den Samstag davor und vermerkt das. Besser ist, die Daten in der Statistik zu korrigieren.
- **Viele Tickets werden vor dem Termin geschlossen.** Ohne Termin dazwischen und ohne Pending till nennt die Vorschau den nächsten Termin nach dem Anlegen als Schätzung.

## Was das Team klären muss

Die Spalte `action` sagt, was mit einem Gerät geschieht. Gemeldet wird nur „melden“. Bei „klären“ steht der Grund in `note`.

- Ergebnisse ohne Entsprechung, etwa „teilweise gelungen“ oder „nicht erfolgt::Fehler nicht gefunden“
- Einträge ohne englischen Namen im Katalog
- Größe bei Laptops und Bildschirmen
- Termin, wo er sich nicht ableiten lässt

## Senden

Erst nach Durchsicht der Vorschau und ausdrücklicher Freigabe. Das Token liegt in Vaultwarden, nie im Repo oder im Chat. Zuerst geht ein Termin zur Probe.
