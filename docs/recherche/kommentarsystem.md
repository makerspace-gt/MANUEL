# Kommentare zur Fallstudie ohne Konto

Stand 13.11.2026. Die Fallstudie liegt auf GitHub Pages, das selbst nichts speichern kann. Giscus braucht ein Konto bei GitHub, Hypothesis zum Schreiben ein eigenes Konto. Kommentare ohne Konto gehen deshalb nur mit einem selbst gehosteten Dienst auf einer VM des Vereins, eingebunden per Skript in die Seite.

| | Isso | Remark42 | Comentario |
|---|---|---|---|
| Ohne Konto | ja, Name und E-Mail sind optional | ja, mit `AUTH_ANON=true` | ja, je Domain einstellbar |
| Freigabe vor dem Erscheinen | ja, `[moderation] enabled = true` | in der Doku nicht gefunden, nur Löschen danach | ja, „Require moderator approval on comment“ |
| Speicher | SQLite | eingebettete Datenbank (bolt) | SQLite oder PostgreSQL |
| Mehrere Threads je Seite | Thread-ID über `data-isso-id` änderbar, mehrere auf einer Seite nicht belegt | mehrere Widgets je Seite, mehrere unabhängige Threads nicht belegt | nicht geprüft |
| Spam | Begrenzung je IP-Adresse, Freigabe | Schutz vor Bots, Aufräumen per Befehl | Freigabe nach Regeln, etwa bei Links |
| Datenschutz | E-Mail nur als Hash, IP für die Begrenzung, Speicherung nicht dokumentiert | je nach Anmeldung | je nach Einstellung |

Empfehlung für das Team ist **Isso mit Freigabe**. Es ist am schlankesten, ein Container mit einer SQLite-Datei, und neue Kommentare erscheinen erst nach Freigabe. Die Fallstudie ist eine einzige Seite. Ein Thread für die ganze Seite reicht, wenn Kommentierende das Kapitel nennen. Brauchen wir Threads je Kapitel, ist das bei allen drei Systemen erst zu testen.

Vor dem Einsatz klären:

- Wer schaltet Kommentare frei, und wie schnell?
- Eintrag ins Verzeichnis von Verarbeitungstätigkeiten und ein Satz im Datenschutzhinweis der Fallstudie
- Betrieb in it-infrastructure, mit Backup und Updates wie bei den anderen Diensten
- Eine Regel, damit niemand persönliche Angaben von Gästen in Kommentare schreibt

## Quellen

- Isso, https://isso-comments.de/docs/reference/server-config/ und https://isso-comments.de/docs/reference/client-config/
- Remark42, https://remark42.com/docs/configuration/parameters/ und https://remark42.com/docs/configuration/frontend/
- Comentario, https://docs.comentario.app/en/configuration/frontend/domain/moderation/ und https://docs.comentario.app/en/installation/requirements/
