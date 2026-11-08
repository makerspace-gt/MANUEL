# Quellen

Hier liegen die Quellen, auf denen Katalog, Einordnung und Fallstudie beruhen. Jede Quelle bleibt unverändert oder wird mit einem Skript ausgelesen, das daneben liegt. Warum die Quellen im Repo liegen, steht in [ADR 28](../docs/adr/0028-quellen-im-repo-ablegen.adoc).

## Open Repair Alliance

| Ordner | Inhalt | Lizenz | Stand |
|---|---|---|---|
| [openrepair-data](openrepair-data) | Submodul mit den Datensätzen der Open Repair Alliance, Open Repair Data v0.3 vom Juli 2026 | CC BY-SA 4.0 | Commit `d1b2ab5` vom 21.10.2026 |
| [openrepair-datastandard](openrepair-datastandard) | Submodul mit dem Open Repair Data Standard samt PDFs der Versionen 0.1 bis 0.3 | CC BY-SA 4.0 | Commit `c1a1f29` vom 30.05.2024 |

## anstiftung

| Ort | Inhalt | Stand |
|---|---|---|
| [../mapped-repair-events](../mapped-repair-events) | Submodul mit dem Quellcode von reparatur-initiativen.org, darin `database.sql` mit 386 Kategorien | GPL-3.0 |
| [anstiftung/laufzettel-erstellen.html](anstiftung/laufzettel-erstellen.html) | Seite "Laufzettel erstellen", gespeichert am 06.11.2026, ohne Token der Sitzung und ohne Anmeldenamen | 06.11.2026 |
| [anstiftung/kategorien.csv](anstiftung/kategorien.csv) | 1.208 Kategorien aus dem Formular, 21 davon unbestätigt | 06.11.2026 |
| [anstiftung/marken.csv](anstiftung/marken.csv) | 3.379 Marken aus dem Formular | 06.11.2026 |
| [anstiftung/felder.csv](anstiftung/felder.csv) | übrige Auswahlfelder, etwa Gründe für vertagt oder nicht erfolgt | 06.11.2026 |

Die Liste in `database.sql` ist nicht aktuell, das Formular enthält deutlich mehr Kategorien. [formular_auslesen.py](anstiftung/formular_auslesen.py) erzeugt die CSV-Dateien und die bereinigte Seite aus der gespeicherten Seite.

## Restarters.net

| Ort | Inhalt | Stand |
|---|---|---|
| [restarters/kategorien.csv](restarters/kategorien.csv) | 47 Kategorien aus der öffentlichen API, mit Kennung und Strom | 08.11.2026 |

[kategorien_abrufen.py](restarters/kategorien_abrufen.py) ruft die Liste neu ab. Der Quellcode liegt unter [TheRestartProject/restarters.net](https://github.com/TheRestartProject/restarters.net).

## Weitere Partner der Open Repair Alliance

Für diese Partner gibt es keine öffentliche Liste ihrer Kategorien. Ihre Kategorien sind nur über die Open Repair Data zugänglich, ausgewertet in [docs/ora](../docs/ora).

| Partner | Werkzeug | Stand der Suche |
|---|---|---|
| Repair Café International | Repair Monitor | keine Liste gefunden, der Repair Monitor wird laut Jahresbericht 2024 neu gebaut, Anfrage an info@repaircafe.org möglich |
| Repair Cafe Wales | Online-Formular | keine Liste gefunden |
| Repair Café Denmark | Tabellen, einige Cafés nutzen Let'sRepair.net | keine Liste gefunden |
| Repair Café Toronto | eigene Software | keine Liste gefunden |
| Fixit Clinic | Online-Formulare, Freitext | keine feste Liste |
| Repair Connects | Plattform von Repair Together | nutzt die ORA-Gruppen direkt |
| iFixit | nutzt die Kategorien von Restarters | siehe Restarters.net |
