# Fotos eines Termins zum richtigen Ticket

Stand 13.11.2026. Am Termin entstehen Fotos von Geräten und Typenschildern. Heute kopiert rclone sie aus dem Docker-Volume von Signal in die Nextcloud. Dabei landen auch Vorschaubilder, Profilbilder und Bilder aus dem Status, die niemand will. Zugeordnet werden die Fotos von Hand.

## Signal

signal-cli-rest-api kennt Schalter, mit denen solche Bilder gar nicht erst geladen werden:

- `JSON_RPC_IGNORE_STORIES=true` für Bilder aus dem Status
- `JSON_RPC_IGNORE_AVATARS=true` für Profilbilder
- `JSON_RPC_IGNORE_STICKERS=true` für Sticker

Vorschaubilder von Links nennt die Doku nicht. Sauberer als rclone auf dem Volume ist deshalb, Nachrichten über die API abzuholen, etwa mit n8n, und nur die Anhänge einer Nachricht zu nehmen. Steht in der Nachricht die Ticketnummer, etwa „#172628“, hängt n8n das Foto direkt an dieses Ticket. Das ist der kürzeste Weg für die Zwischenzeit.

## Immich

Eine fertige Verbindung zwischen Zammad und Immich gibt es nicht. Denkbar ist ein Workflow in n8n, der die Fotos eines Termins aus einem Album in Immich holt. Damit er ein Foto einem Ticket zuordnen kann, braucht es ein Zeichen im Bild, etwa ein Kärtchen mit der Ticketnummer, das als Erstes fotografiert wird. Alle folgenden Fotos gehören zu diesem Ticket, bis das nächste Kärtchen kommt. Die Nummer liest das Modell mit Bildverständnis, ein Mensch bestätigt.

## Empfehlung

1. Sofort die drei Schalter in signal-cli-rest-api setzen, siehe it-infrastructure.
2. Für die Erprobung Fotos mit der Ticketnummer per Signal schicken und von n8n anhängen lassen.
3. Immich mit Kärtchen erst testen, wenn n8n läuft.

## Quellen

- signal-cli-rest-api, https://github.com/bbernhard/signal-cli-rest-api
- signal-cli, Ausgabe empfangener Nachrichten, https://github.com/AsamK/signal-cli/blob/master/man/signal-cli-jsonrpc.5.adoc
