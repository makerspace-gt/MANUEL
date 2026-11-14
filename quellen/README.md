# Quellen

Hier liegen die Quellen, auf denen Katalog, Einordnung und Fallstudie beruhen. Jede Quelle bleibt unverändert oder wird mit einem Skript ausgelesen, das daneben liegt. Warum die Quellen im Repo liegen, steht in [ADR 28](../docs/adr/0028-quellen-im-repo-ablegen.adoc).

## Open Repair Alliance

| Ordner | Inhalt | Lizenz | Stand |
|---|---|---|---|
| [openrepair-data](https://github.com/openrepair/data/tree/d1b2ab5a7b05c96645f5d4afec7951fc912639e1) | Submodul mit den Datensätzen der Open Repair Alliance, Open Repair Data v0.3 vom Juli 2026 | CC BY-SA 4.0 | Commit `d1b2ab5` vom 21.10.2026 |
| [openrepair-datastandard](https://github.com/openrepair/datastandard/tree/c1a1f2979937a3a481782d3afbde1b62f9b24b58) | Submodul mit dem Open Repair Data Standard samt PDFs der Versionen 0.1 bis 0.3 | CC BY-SA 4.0 | Commit `c1a1f29` vom 30.05.2024 |
| [ords-extra](https://codeberg.org/zenlan/ords-extra/src/commit/08e185b8289094ae31c19437a3e86a1248e96635) | Submodul mit Zusatzdaten zu den Open Repair Data von Monique Szpak, verknüpft über `id`. Englische Übersetzungen der Gegenstände und der Problemtexte, einheitliche Marken, UNU-Keys und unter `dat/misc/fault_types` Listen von Fehlerarten mit Suchmustern für Desktop, Laptop, Handy, Drucker, Tablet und Staubsauger. Die Daten liegen in Git LFS | CC BY-NC-ND 4.0 | Commit `08e185b` vom 08.11.2026 |

Die Lizenz von ords-extra erlaubt keine Bearbeitungen und keine kommerzielle Nutzung. Wir lesen die Daten für Auswertungen und verweisen darauf. Abgeleitete Tabellen daraus veröffentlichen wir erst nach Rücksprache mit der Autorin.

## anstiftung

| Ort | Inhalt | Stand |
|---|---|---|
| [../mapped-repair-events](https://github.com/anstiftung/mapped-repair-events/tree/a507956b91fca2f30dd372e847f015a24138abf7) | Submodul mit dem Quellcode von reparatur-initiativen.org, darin `database.sql` mit 386 Kategorien | GPL-3.0 |
| [anstiftung/laufzettel-erstellen.html](anstiftung/laufzettel-erstellen.html) | Seite "Laufzettel erstellen", gespeichert am 06.11.2026, ohne Token der Sitzung und ohne Anmeldenamen | 06.11.2026 |
| [anstiftung/kategorien.csv](anstiftung/kategorien.csv) | 1.208 Kategorien aus dem Formular, 21 davon unbestätigt | 06.11.2026 |
| [anstiftung/marken.csv](anstiftung/marken.csv) | 3.379 Marken aus dem Formular | 06.11.2026 |
| [anstiftung/felder.csv](anstiftung/felder.csv) | übrige Auswahlfelder, etwa Gründe für vertagt oder nicht erfolgt | 06.11.2026 |

Die Liste in `database.sql` ist nicht aktuell, das Formular enthält deutlich mehr Kategorien. [parse_form.py](anstiftung/parse_form.py) erzeugt die CSV-Dateien und die bereinigte Seite aus der gespeicherten Seite.

## Restarters.net

| Ort | Inhalt | Stand |
|---|---|---|
| [restarters/kategorien.csv](restarters/kategorien.csv) | 47 Kategorien aus der öffentlichen API, mit Kennung und Strom | 08.11.2026 |

[fetch_categories.py](restarters/fetch_categories.py) ruft die Liste neu ab.

| Ordner | Inhalt | Lizenz | Stand |
|---|---|---|---|
| [restarters.net](https://github.com/TheRestartProject/restarters.net/tree/d46501cb20a0bda1216ffb2e48a19f074e86f776) | Submodul mit dem Quellcode von Restarters.net, flach geklont, Zweig `develop`. Die Felder eines Geräts in der API beschreibt `app/Http/Resources/Device.php` | GPL-3.0 | Commit `d46501c` vom 12.11.2026 |

## Zammad

| Ordner | Inhalt | Lizenz | Stand |
|---|---|---|---|
| [zammad](https://github.com/zammad/zammad/tree/3b0c2ed25738922dd1651c81cd9bee815b4cd6e8) | Submodul mit dem Quellcode von Zammad, flach geklont, Zweig `develop`, Version 7.4.x in Entwicklung | AGPL-3.0 | Commit `3b0c2ed` vom 09.11.2026 |

Wichtig für MANUEL sind die KI-Agenten in `app/models/ai/agent/type/`, die Anbieter in `lib/ai/provider/` und die Texterkennung in Bildern in `app/services/service/ai/ticket/pre_process_article_content.rb`. Der Zweig `develop` kann Funktionen enthalten, die in unserer Version noch fehlen.

| Ordner | Inhalt | Lizenz | Stand |
|---|---|---|---|
| [zammad-docker-compose](https://github.com/zammad/zammad-docker-compose/tree/16f43d8) | Submodul mit der Compose-Datei von Zammad für die Testumgebung auf MANUEL, derselbe Commit wie im IT-Plan. Sie kommt ins Image, siehe [ADR 43](../docs/adr/0043-eine-testumgebung-auf-manuel-betreiben.adoc) | AGPL-3.0 | Commit `16f43d8`, Zammad 7.2.2 |

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
