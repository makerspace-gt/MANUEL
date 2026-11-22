# Für das Team bis 28.11.2026

Damit MANUEL am 05.12.2026 im Repair Café starten kann, braucht es bis Freitag, den 28.11., ein paar Entscheidungen und Handgriffe. Alles Technische ist vorbereitet.

## Entscheidungen

1. **Texte für Mails an Gäste freigeben.** Eingangsbestätigung, Nachfrage beim Terminvorschlag, Absage und Erinnerung liegen in [zammad/texts/](../zammad/texts/). Bis zur Freigabe bleiben diese Mails aus. Die Checkliste für jede Reparatur liegt in [checklist.de.txt](../zammad/texts/checklist.de.txt).
2. **Verschlüsselung der SSD.** Steht MANUEL am 05.12. schon im Makerspace? Reicht der Schlüssel im TPM, oder soll zusätzlich eine PIN beim Start nötig sein? Die Optionen stehen in [privacy_review.md](privacy_review.md).
3. **Namen in die Tabelle Rollen** im [PLAN](../PLAN.md#rollen), je Rolle eine Person und eine Vertretung.

## Handgriffe

1. **Datenschutz.** Die Vorschläge aus [privacy_review.md](privacy_review.md) ins Repo it-infrastructure übernehmen, also den Hinweis für Gäste und das Verzeichnis der Verarbeitungen.
2. **Helpdesk-VM.** Steht sie bis 01.12., zieht MANUEL dort ein. Sonst startet MANUEL am alten Zammad, die Schritte stehen in [zammad/README.md](../zammad/README.md#plan-b-das-alte-zammad).
3. **Anmerkungen zur Fallstudie** im Etherpad bis 28.11., danach wird es abgeschaltet.

## Am 05.12.

- Der Empfang legt für jedes Gerät ein eigenes Ticket an.
- MANUEL schlägt die Art des Geräts vor. Jemand prüft sie am Termin und korrigiert sie bei Bedarf. Weicht die Prüfung mit `d3:9b` ab, steht der Tag `category-differs` am Ticket.
- Lösungsansätze von MANUEL stehen eine Woche vorher als interne Notiz im Ticket. Wer sie liest, markiert sie mit den Makros „Vorschlag hilfreich“ oder „Vorschlag nicht hilfreich“. Das ist die Kennzahl für die Rückmeldungen.
- Wer repariert, trägt sich als Bearbeiter des Tickets ein. Hat der Gast selbst repariert, wird der Agent Gast eingetragen.
