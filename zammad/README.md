# Felder und Makros für Zammad

Diese Dateien legen in Zammad an, was MANUEL braucht. Sie laufen mit `rails runner` und lassen sich wiederholen, vorhandene Felder und Makros werden aktualisiert statt doppelt angelegt. Andere Initiativen können sie so in ihr eigenes Zammad einspielen.

| Datei | Inhalt |
|---|---|
| [objekte.rb](objekte.rb) | Felder im Ticket, also Art des Geräts aus dem [Katalog](../katalog/), Marke, Bezeichnung, Baujahr, Stromversorgung, Defekt, Lösung, Ergebnis als Baum, Repariert von, VDE-Prüfung, Termin sowie Spenden und Bedarf für das Statistik-Ticket |
| [makros.rb](makros.rb) | Makros „Vorschlag hilfreich“ und „Vorschlag nicht hilfreich“, die je einen Tag setzen, siehe [ADR 32](../docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc) |

Auf MANUEL laufen sie mit dem Befehl `zammad` in der Testinstanz, aus dem Wurzelverzeichnis des Repos:

```bash
zammad "$(cat zammad/objekte.rb)" < katalog/kategorien.tsv
zammad "$(cat zammad/makros.rb)"
```

- Die Art des Geräts ist ein einfaches Auswahlfeld mit dem Schlüssel des Katalogs als Wert und dem Namen als Bezeichnung. So bleibt der Schlüssel im Ticket, auch wenn sich ein Name ändert, und der Ticket Categorizer sieht Wert und Bezeichnung, siehe [ADR 13](../docs/adr/0013-eintraege-mit-hierarchischem-schluessel-kennzeichnen.adoc).
- Das Ergebnis folgt dem Baum unseres Zammad, wie er am 13.11.2026 in den Exporten stand.
- Die VDE-Prüfung kennt leer, empfohlen, ja und nein. Leer heißt, es ist noch nicht entschieden.
- Die Namen der Felder sind ein Vorschlag. Heißen sie in einem vorhandenen Zammad anders, vorher `FIELDS` in `objekte.rb` anpassen, sonst entsteht ein zweites Feld.
- Welche Felder wann sichtbar sind, etwa Spenden nur im Statistik-Ticket, regeln Core Workflows. Die fehlen hier noch.

Am 13.11.2026 liefen beide Dateien zweimal in der Testinstanz mit Zammad 7.2.2, ohne Fehler und ohne doppelte Felder oder Makros.
