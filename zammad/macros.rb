# Two macros to rate suggestions of MANUEL, loaded by zammad/setup.rb, see
# docs/adr/0032-kennzahlen-der-erprobung-erheben.adoc.
# Each macro adds a tag with one click and leaves the ticket open. A note on why a suggestion did not
# help is written by hand, a macro cannot ask for text.

MACROS = {
  'Suggestion helpful'     => ['Vorschlag hilfreich', 'suggestion-helpful'],
  'Suggestion not helpful' => ['Vorschlag nicht hilfreich', 'suggestion-not-helpful'],
}.freeze

MACROS.each do |name, (german, tag)|
  macro = Macro.find_or_initialize_by(name: tr(name, german))
  macro.update!(
    perform:         { 'ticket.tags' => { operator: 'add', value: tag } },
    ux_flow_next_up: 'none',
    note:            'Rates a suggestion of MANUEL, counted for indicator 3 of ADR 32',
    active:          true,
    created_by_id:   macro.created_by_id || 1,
    updated_by_id:   1,
  )
end

puts "Makros: #{Macro.where(name: MACROS.keys).pluck(:name).join(', ')}"
