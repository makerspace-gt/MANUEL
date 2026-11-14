# Felder und Werte der Plattformen

Je Plattform eine CSV-Datei. Die Kopfzeile nennt die Felder so, wie die Plattform sie selbst nennt. Darunter stehen alle Werte, die ein Feld annehmen kann, je Zeile einer. Freitext und Zahlen haben keine festen Werte, ihre Spalte bleibt leer. Wo zwei Spalten zusammengehören, etwa eine Kategorie und ihre Oberkategorie, stehen sie in derselben Zeile.

Die Dateien entstehen mit [platform_values.py](../../eval/fields/platform_values.py) aus den Quellen im Ordner [quellen](../../quellen).

| Datei | Plattform | Felder | Quelle |
|---|---|---|---|
| [ora.csv](ora.csv) | Open Repair Data Standard | 14 Spalten der Open Repair Data | Werte für Status und Hindernis aus [standard.rst](../../quellen/openrepair-datastandard/standard.rst), Produktkategorien aus der Liste der Open Repair Data. Die sechs Gruppen ohne Strom nennt der Standard nicht, sie stammen aus den Daten und haben die Nummer 0 |
| [anstiftung.csv](anstiftung.csv) | reparatur-initiativen.org | 12 Felder des Laufzettels mit den Namen der Tabelle `info_sheets` | Gespeicherter Laufzettel in [quellen/anstiftung](../../quellen/anstiftung). Die Oberkategorie heißt in der Datenbank `parent_id` der Tabelle `categories`, die Stromversorgung steht in `info_sheets_form_field_options` |
| [restarters.csv](restarters.csv) | Restarters.net | 23 Felder eines Geräts in der API | Beschreibung der API in [Device.php](../../quellen/restarters/Device.php), Kategorien aus [kategorien.csv](../../quellen/restarters/kategorien.csv) |

## Hinweise

- Die Werte stehen als Text da. Gespeichert werden sie zum Teil als Zahl. Die anstiftung speichert IDs, die IDs stehen in den Dateien unter `quellen/anstiftung`. Der Standard erlaubt für Status und Hindernis Text oder Nummer.
- Der Standard ist bei einem Hindernis uneinheitlich. Im Text heißt es „No way to open the product“, in der Tabelle der Werte „No way to open product“. Hier steht die Fassung der Tabelle, Restarters nutzt die andere. Die Tabelle des Standards kennt außerdem „Item too worn out“, das in der Aufzählung im Text und bei Restarters fehlt.
- Bei Restarters gelten `next_steps` und `spare_parts` nur für Repairable und `barrier` nur für End of life.
- Bei der anstiftung kommen manche Kategorien unter mehreren Oberkategorien vor, etwa „Sonstiges“. Marken mit gleichem Namen und verschiedener ID stehen nur einmal da.
