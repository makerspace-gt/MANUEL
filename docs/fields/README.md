# Felder und Werte der Plattformen

Je Plattform eine CSV-Datei. Die Kopfzeile nennt die Felder so, wie die Plattform sie selbst nennt. Darunter stehen alle Werte, die ein Feld annehmen kann, je Zeile einer. Freitext und Zahlen haben keine festen Werte, ihre Spalte bleibt leer. Wo zwei Spalten zusammengehören, etwa eine Kategorie und ihre Oberkategorie, stehen sie in derselben Zeile.

Die Dateien entstehen bisher in einem Schritt mit [platform_values.py](../../eval/fields/platform_values.py). Künftig folgen sie den drei Schritten Import, Tidy und Transform, damit sich eine Quelle einfach aktualisieren lässt und jeder Schritt nachvollziehbar bleibt.

## Ablauf

1. **Import.** Jede Quelle wird möglichst unverändert eine Tabelle in [import](import).
   - [import_sources.py](../../eval/fields/import_sources.py) liest die Quellen, die noch keine Tabellen sind:
     - die Codes für Status und Hindernis aus `standard.rst`
     - fünf Tabellen aus `database.sql` der anstiftung
     - die Felder eines Geräts und einer Kategorie aus der API von Restarters
     - die Abbildung nach ORDS aus `config/ords.php`
     - alle Texte der deutschen Sprachdateien von Restarters als zweite Übersetzungstabelle `restarters_translations.csv`
   - [import_partners.R](../../eval/fields/import_partners.R) schreibt aus den aggregierten Open Repair Data je Partner eine Datei mit jeder Kategorie des Partners, der ORA-Gruppe, die die Alliance zugeordnet hat, und der Zahl der Einträge.
   - Tabellen wie die Kategorien des Laufzettels in [quellen/anstiftung](../../quellen/anstiftung) liest der nächste Schritt direkt. Dazu gehören auch die 21 unbestätigten Kategorien, die Spalte `confirmed` bleibt erhalten.
2. **Tidy.** Steht noch aus.
3. **Transform.** Steht noch aus. Danach ersetzt es `platform_values.py`.

| Datei | Plattform | Felder | Quelle |
|---|---|---|---|
| [ora.csv](ora.csv) | Open Repair Data Standard | 14 Spalten der Open Repair Data | Werte für Status und Hindernis aus [standard.rst](../../quellen/openrepair-datastandard/standard.rst), Produktkategorien aus der Liste der Open Repair Data. Die sechs Gruppen ohne Strom nennt der Standard nicht, sie stammen aus den Daten und haben die Nummer 0 |
| [anstiftung.csv](anstiftung.csv) | reparatur-initiativen.org | 12 Felder des Laufzettels mit den Namen der Tabelle `info_sheets`, dazu die Werte für ORDS | Gespeicherter Laufzettel in [quellen/anstiftung](../../quellen/anstiftung). Die Oberkategorie heißt in der Datenbank `parent_id` der Tabelle `categories`, die Stromversorgung steht in `info_sheets_form_field_options` |
| [restarters.csv](restarters.csv) | Restarters.net | 23 Felder eines Geräts in der API und `powered` der Kategorie, dazu deutsche Spalten und die Werte für ORDS | Beschreibung der API in [Device.php](../../quellen/restarters.net/app/Http/Resources/Device.php) im Submodul, Kategorien aus [kategorien.csv](../../quellen/restarters/kategorien.csv) |

## Hinweise

- Die Werte stehen als Text da. Gespeichert werden sie zum Teil als Zahl. Die anstiftung speichert IDs, die IDs stehen in den Dateien unter `quellen/anstiftung`. Der Standard erlaubt für Status und Hindernis Text oder Nummer.
- Der Standard ist bei einem Hindernis uneinheitlich. Im Text heißt es „No way to open the product“, in der Tabelle der Werte „No way to open product“. Hier steht die Fassung der Tabelle, Restarters nutzt die andere. Die Tabelle des Standards kennt außerdem „Item too worn out“, das in der Aufzählung im Text und bei Restarters fehlt.
- Bei Restarters gelten `next_steps` und `spare_parts` nur für Repairable und `barrier` nur für End of life.
- Bei der anstiftung kommen manche Kategorien unter mehreren Oberkategorien vor, etwa „Sonstiges“. Marken mit gleichem Namen und verschiedener ID stehen nur einmal da.
- In `restarters.csv` steht neben jeder Spalte mit festen Werten eine Spalte `_de` mit der deutschen Fassung, die restarters.net zeigt. Sie kommt aus `lang/de.json`, `lang/de/partials.php` und `lang/de/devices.php` im Submodul.
- Beim Anlegen eines Geräts fragt Restarters zuerst, ob es elektrisch ist, und zeigt danach nur die passenden Kategorien. Deshalb steht `powered` vor `category`. „Misc“ gibt es einmal elektrisch und einmal nicht.
- Restarters exportiert seine Daten selbst im Format von ORDS. Die Abbildung steht in `config/ords.php` im Submodul. Die Spalten `ords_product_category`, `ords_product_category_id` und `ords_repair_barrier_if_end_of_life` übernehmen sie. Bildschirme und Laptops fasst sie je zu einer ORA-Gruppe zusammen, „Hand tool“ und „Misc“ ohne Strom werden beide zu „Unpowered - Other“.
- Die anstiftung bildet selbst auf ORDS ab, in `database.sql` von mapped-repair-events. `ords_category_id` kommt aus `categories.ords_category_id`, die Spalten `_repair_status` und `_repair_barrier_if_end_of_life` neben den Gründen aus `form_field_options_extra_infos`, so geschrieben wie dort, etwa `end of life` und `product too worn out`. Der Stand von `database.sql` ist alt. Er ordnet nur 114 der 1.208 Kategorien zu und kennt „Fehler nicht gefunden“ noch nicht.
- Deshalb steht daneben `ora_product_category`, die Gruppe, der die Alliance die Kategorie in den Open Repair Data am häufigsten zugeordnet hat, mit ihrem Anteil. Das sind 1.179 Kategorien. Die übrigen kamen nach dem Stand der Daten vom Juli 2026 dazu oder wurden nie genutzt. Bei 28 Kategorien weichen die beiden Zuordnungen voneinander ab, die Alliance nutzt dort oft die groben Gruppen „Small home electrical“ und „Large home electrical“.
