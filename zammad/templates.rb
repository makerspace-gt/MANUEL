# Template for guests who come without appointment, loaded by zammad/setup.rb, see
# docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc. The text "am Empfang erfasst" lets
# zammad/article_types.rb switch the first article to the type walk-in. The appointment is now, so the
# ticket counts for today. A template of an older Zammad named "Repair Café spontan" is renamed.

template = Template.find_by(name: 'Walk-in') || Template.find_by(name: 'Repair Café spontan') || Template.new(active: true)
template.assign_attributes(
  name:    'Walk-in',
  options: {
    'article.body'          => { 'value' => 'am Empfang erfasst' },
    'ticket.group_id'       => { 'value' => Group.find_by!(name: 'Repairs').id.to_s },
    'ticket.state_id'       => { 'value' => Ticket::State.find_by!(name: 'pending reminder').id.to_s },
    'ticket.pending_time'   => { 'operator' => 'relative', 'value' => '1', 'range' => 'minute' },
    'ticket.formSenderType' => { 'value' => 'phone-in' },
  },
)
template.created_by_id ||= 1
template.updated_by_id = 1
template.save! if template.new_record? || template.changed?

puts "Vorlage #{template.name}, aktiv #{template.active}"
