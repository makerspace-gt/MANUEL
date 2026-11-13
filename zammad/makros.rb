# Creates the two macros to rate suggestions of MANUEL, see docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc.
# Runs with rails runner and can run again:
#   zammad "$(cat zammad/makros.rb)"
# Each macro adds a tag with one click and leaves the ticket open. A note on why a suggestion did not
# help is written by hand, a macro cannot ask for text.

MACROS = {
  'Vorschlag hilfreich'       => 'vorschlag-hilfreich',
  'Vorschlag nicht hilfreich' => 'vorschlag-nicht-hilfreich',
}.freeze

MACROS.each do |name, tag|
  macro = Macro.find_or_initialize_by(name: name)
  macro.update!(
    perform:         { 'ticket.tags' => { operator: 'add', value: tag } },
    ux_flow_next_up: 'none',
    note:            'Bewertung eines Vorschlags von MANUEL, gezählt für Kennzahl 3 nach ADR 32',
    active:          true,
    created_by_id:   macro.created_by_id || 1,
    updated_by_id:   1,
  )
end

puts "Makros: #{Macro.where(name: MACROS.keys).pluck(:name).join(', ')}"
