# Datenschutz vor dem Echtbetrieb

Stand 21.11.2026. Vorschläge für das Team bis zum 28.11.2026. Hinweis für Gäste und Verzeichnis der Verarbeitungen liegen im Repo [it-infrastructure](https://github.com/makerspace-gt/it-infrastructure/tree/main/docs/datenschutz) des Teams. Die Änderungen trägt das Team dort ein. Das ist keine Rechtsberatung.

## Hinweis für Gäste

Die Vorlage `docs/datenschutz/vorlagen/hinweis-gaeste.md` nennt MANUEL schon und sagt, dass keine Daten an externe KI-Anbieter gehen. Seit der Vorlage hat sich geändert:

- **Statistik an Restarters.net.** Reparaturen melden wir ohne Namen über die API von Restarters.net an The Restart Project, reparatur-initiativen.org bekommt nur noch die Termine, siehe [ADR 14](adr/0014-reparaturen-ueber-restarters-melden.adoc). Vorschlag für den Satz ist „Angaben zur Reparatur ohne deinen Namen melden wir an Restarters.net für die Statistik der Open Repair Alliance.“
- **Sprachnachrichten.** Wer auf den Anrufbeantworter spricht, dessen Nachricht wandelt MANUEL auf dem Rechner des Vereins in Text um, sobald [ADR 64](adr/0064-voicemails-lokal-transkribieren.adoc) angenommen ist. Bis dahin transkribiert sipgate. Ein Satz dazu gehört in den Hinweis, sobald der Test passt.
- **Hausordnung.** Der Hinweis kann auf die Hausordnung in der Wissensdatenbank verweisen, sobald sie öffentlich ist.

## Verzeichnis der Verarbeitungen, Nr. 1 Repair Café

- **Daten** um die Felder am Gast ergänzen, die es im Zammad schon gibt, also Einverständnis zur Hausordnung, Fördermitgliedschaft, Geburtsjahr, Newsletter und Werbung durch. Dazu Sprachnachrichten mit Transkript, siehe Nr. 17 Telefonie.
- **Empfänger** um Restarters.net ergänzen, nur Angaben zur Reparatur ohne Personenbezug.
- **Auswertungen.** Für die Erprobung und die Fallstudie liegen Exporte echter Tickets lokal auf MANUEL und auf dem Laptop eines Engagierten, siehe [ADR 2](adr/0002-echte-ticketdaten-nur-lokal-auswerten.adoc), [ADR 69](adr/0069-nur-tickets-des-repair-cafe-in-die-testinstanz-uebernehmen.adoc) und [ADR 70](adr/0070-aufwertung-des-datensatzes-je-modell-messen.adoc). In die Fallstudie gehen nur Summen. Vorschlag für die TOMs ist, dass der Laptop verschlüsselt ist und die Exporte nach dem Verwendungsnachweis im März 2027 gelöscht werden.

## Daten und Aufbewahrung

- **Open WebUI** steht dort mit „Chats unbegrenzt, zu prüfen“. Vorschlag ist, Chats nach 90 Tagen zu löschen, wie dort schon als Ziel steht, und vor dem Echtbetrieb festzulegen, wer das prüft.
- **Etherpad** für Anmerkungen zur Fallstudie läuft vorübergehend öffentlich auf MANUEL, ohne Daten von Gästen, siehe [ADR 71](adr/0071-etherpad-voruebergehend-fuer-anmerkungen-des-teams.adoc). Es kommt nicht ins Verzeichnis, wenn es vor dem Echtbetrieb wieder abgeschaltet ist.

## Verschlüsselung der SSD

Kapitel 11 der Fallstudie sieht die Verschlüsselung vor dem Umzug in den Makerspace vor. Fedora CoreOS richtet LUKS mit dem Schlüssel im TPM nur bei der Installation über Butane ein, also mit einer Neuinstallation.

| Weg | Aufwand | Schutz |
|---|---|---|
| Neuinstallation vor dem 05.12. | etwa einen halben Tag, dazu die Testinstanz und die Modelle neu laden | SSD allein ist unlesbar, etwa bei Diebstahl oder Entsorgung der SSD |
| Neuinstallation vor dem Umzug in den Makerspace | wie oben, aber ohne Zeitdruck vor dem Start | gleich, solange der Mini-PC bis dahin nicht im Makerspace steht |
| Mit TPM und zusätzlicher PIN beim Start | wie oben, nach jedem Neustart muss jemand die PIN eingeben | auch der ganze Mini-PC ist ohne PIN unlesbar, aber kein Neustart ohne Mensch |

Mit dem Schlüssel nur im TPM startet der Mini-PC nach Stromausfall von selbst. Wer den ganzen Mini-PC mitnimmt, kommt damit aber an die Daten. Vorschlag ist die Neuinstallation mit TPM vor dem Umzug, wenn der Mini-PC bis dahin nicht im Makerspace steht. Steht er schon beim Start am 05.12. dort, vorher.

Offen für das Team:

1. Steht MANUEL am 05.12. schon im Makerspace?
2. Reicht TPM allein, oder soll eine PIN dazu?
