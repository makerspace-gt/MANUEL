# Postfach

Regeln für das Postfach, das Zammad abholt, und ein Skript für die Aufbewahrung, siehe [ADR 65](../docs/adr/0065-postfach-archivieren-und-aufbewahrung-begrenzen.adoc). Beides ist unabhängig vom Anbieter. Sieve ist ein Standard (RFC 5228, `copy` nach RFC 3894), das Skript nutzt nur IMAP aus der Standardbibliothek von Python.

| Datei | Zweck |
|---|---|
| [sieve/repair-cafe.sieve](sieve/repair-cafe.sieve) | Kopien von Zammad nach Gesendet, alles andere zusätzlich ins Archiv, Spam in den Ordner Spam, das Kontaktformular nie |
| [retention.tsv](retention.tsv) | Ordner und Tage bis zum Löschen, Spam 30, Archiv und Gesendet 365 |
| [imap_retention.py](imap_retention.py) | Löscht Mails älter als die Frist, ohne `--apply` nur ein Probelauf |

## Einrichten

1. Die Domain in der ersten Regel des Sieve-Skripts auf die eigene ändern und das Skript beim Anbieter eintragen. Den Namen des Ordners für Gesendet beim Anbieter prüfen.
2. In Zammad `MANUEL_SENT_BCC` auf die Adresse des Postfachs setzen. `zammad/inbound.rb` trägt sie als `system_bcc` ein, damit jede Mail von Zammad als Kopie im Postfach landet.
3. `MANUEL_SPAM_FOLDER=Spam` setzen. `zammad/inbound.rb` legt dann einen zweiten Kanal an, der den Ordner Spam abholt, die Mails auf dem Server lässt und in die Gruppe Spam check legt. Er ist aktiv, wenn der Kanal für den Posteingang aktiv ist.
4. Auf einem Rechner, der ständig läuft, eine env-Datei mit `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` und `IMAP_PORT` anlegen, nur für den eigenen Nutzer lesbar, und das Skript täglich starten.

```
python3 mail/imap_retention.py --env ~/.config/manuel/imap.env           # Probelauf
python3 mail/imap_retention.py --env ~/.config/manuel/imap.env --apply   # löschen
```

Beispiel für einen systemd-Timer als Nutzer:

```ini
# ~/.config/systemd/user/imap-retention.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 %h/MANUEL/mail/imap_retention.py --env %h/.config/manuel/imap.env --apply

# ~/.config/systemd/user/imap-retention.timer
[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Gelöscht wird nach dem Datum, an dem der Server die Mail bekommen hat. Zugangsdaten gibt das Skript nie aus.

## Geprüft

Am 15.11.2026 lokal mit Dovecot 2.3.21 und erfundenen Mails. `sieve-test` legte eine Kopie von Zammad nur in Gesendet ab, eine normale Mail ins Archiv und in den Posteingang, Spam ins Archiv und nach Spam und eine Mail aus dem Kontaktformular mit Spam-Kopf in den Posteingang. `imap_retention.py` zählte im Probelauf die alten Mails richtig, löschte mit `--apply` nur diese, und ein zweiter Lauf fand nichts mehr.
