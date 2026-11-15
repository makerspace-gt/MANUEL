# Values of the field repair_result as [English, German], loaded by objects.rb and migrate_fields.rb.
# The German labels follow the result tree of our Zammad as exported on 13.11.2026.

RESULT_TREE = {
  ['No-show', 'No-Show']                    => [],
  %w[Fixed gelungen]                        => [],
  ['Partly fixed', 'teilweise gelungen']    => [],
  %w[Postponed vertagt]                     => [
    ['Spare part ordered by the visitor', 'Ersatzteilbesorgung durch Gast'],
    ['Spare part ordered by the repair group', 'Ersatzteilbesorgung durch die Initiative'],
    ['Item incomplete', 'Gerät nicht komplett'],
    ['Tool or accessory missing', 'Hilfsmittel oder Zubehör fehlt'],
    ['Waiting time too long', 'zu lange Wartezeit'],
  ],
  ['Not repaired', 'nicht erfolgt']         => [
    ['Too worn out', 'Abnutzung zu groß'],
    ['Spare part not available', 'Ersatzteil nicht erhältlich'],
    ['Spare part too expensive', 'Ersatzteil zu teuer'],
    ['Fault not found', 'Fehler nicht gefunden'],
    ['Item incomplete', 'Gerät nicht komplett'],
    ['Total effort too high', 'Gesamtaufwand zu hoch'],
    ['Tool or accessory missing', 'Hilfsmittel oder Zubehör fehlt'],
    ['Repair information not available', 'Reparaturinformationen nicht verfügbar'],
    ['Partly usable', 'Teilnutzung möglich'],
    ['Still under warranty', 'hat noch Garantie'],
    ['Waiting time too long', 'zu lange Wartezeit'],
    ['Item cannot be opened', 'Öffnung des Gerätes nicht möglich'],
  ],
  %w[Aborted abgebrochen]                   => [
    ['Item must not be used any more', 'Gerät darf nicht mehr genutzt werden'],
  ],
}.freeze
