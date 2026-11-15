# Prüfung der Art des Geräts

Ein kleiner Dienst auf MANUEL, der die Art des Geräts mit dem Decision-Modell `d3:9b` prüft, siehe [ADR 68](../docs/adr/0068-art-des-geraets-mit-d3-pruefen.adoc). Zammad fragt ihn aus [zammad/category_check.rb](../zammad/category_check.rb).

Er nutzt die Kette aus ADR 10 und 11 mit denselben Dateien wie die Auswertungen:
- die Einträge aus `katalog/kategorien.tsv` und `quellen/anstiftung/kategorien.csv` über `katalog/entries.py`
- die Ähnlichkeitssuche mit `bge-m3`
- die Wahl durch `d3:9b`
- die Regeln für Rückfragen aus `eval/decision/follow_up.py`

Er braucht nur die Standardbibliothek von Python.

```
OLLAMA_URL=http://127.0.0.1:11434 python3 category_check/server.py
curl -s localhost:8090/check -d '{"text": "Toaster defekt. Wird nicht mehr warm", "subject": "Toaster defekt"}'
```

Die Antwort nennt Schlüssel, Name, gewählten Namen, Wahrscheinlichkeit und den Grund für eine Rückfrage. Texte werden weder gespeichert noch protokolliert. Die Vektoren der Namen liegen in `CACHE` und werden neu berechnet, wenn sich der Katalog ändert.

In der Testumgebung läuft er als Dienst `category-check` aus [compose.override.yml](../testumgebung/compose.override.yml).
