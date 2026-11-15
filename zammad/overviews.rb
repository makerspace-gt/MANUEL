# Overviews of a repair group, loaded by zammad/setup.rb, see
# docs/adr/0062-datums-tags-und-monatsuebersichten-automatisch-pflegen.adoc.
# The twelve monthly overviews are named after the default language of Zammad, so overviews that already
# exist under that name are kept. A new one starts switched off, ManuelEventTags.run in event_tags.rb fills
# in the date tags of its month and switches it on. Existing overviews keep their condition and state.

MONTH_VIEW = %w[title customer device_type problem_reported solution repair_result owner].freeze

month_names = if Setting.get('locale_default').to_s.start_with?('de')
                %w[Januar Februar März April Mai Juni Juli August September Oktober November Dezember].map { |m| "Gegenstände #{m}" }
              else
                %w[January February March April May June July August September October November December].map { |m| "Items #{m}" }
              end
roles = Role.where(name: ['Repair Agent', 'Repair Coordinator']).to_a

month_names.each_with_index do |name, index|
  overview = Overview.find_or_initialize_by(name: name)
  next if overview.persisted?

  overview.assign_attributes(
    link:          "items-#{index + 1}",
    prio:          9000 + index,
    condition:     { 'ticket.tags' => { 'operator' => 'contains one', 'value' => 'no-date-yet' } },
    order:         { 'by' => 'pending_time', 'direction' => 'ASC' },
    view:          { 'd' => MONTH_VIEW, 's' => MONTH_VIEW, 'm' => MONTH_VIEW, 'view_mode_default' => 's' },
    active:        false,
    roles:         roles,
    created_by_id: 1,
    updated_by_id: 1,
  )
  overview.save!
end

puts "Übersichten: #{Overview.where(name: month_names).count} je Monat, aktiv #{Overview.where(name: month_names, active: true).count}"

# Working overviews. Names are English with a German translation. Overviews of an older Zammad with the
# names in LEGACY_OVERVIEWS are renamed and then updated, their active state stays. A new one is active.
LEGACY_OVERVIEWS = {
  'Gegenstände #next-event' => 'Next event',
  'Meine Reparaturen'       => 'My repairs',
  'Repair Café'             => 'Open repairs',
}.freeze

LEGACY_OVERVIEWS.each do |old_name, new_name|
  overview = Overview.find_by(name: old_name)
  overview.update!(name: new_name, updated_by_id: 1) if overview && !Overview.exists?(name: new_name)
end

state_ids = ->(*names) { names.map { |name| Ticket::State.find_by!(name: name).id.to_s } }
group_ids = ->(*names) { names.map { |name| Group.find_by!(name: name).id.to_s } }
not_done = { 'name' => 'ticket.state_id', 'operator' => 'is not', 'value' => state_ids.('closed', 'merged') }
coordinator = Role.where(name: 'Repair Coordinator').to_a

WORK_OVERVIEWS = [
  ['Next event', 'Nächster Termin', 'next-event', roles, 'repair_result',
   %w[title customer device_type problem_reported owner pending_time], 'pending_time',
   [{ 'name' => 'ticket.tags', 'operator' => 'contains all', 'value' => 'next-event' }]],
  ['My repairs', 'Meine Reparaturen', 'my-repairs', roles, 'state',
   %w[title customer device_type problem_reported pending_time], 'pending_time',
   [not_done, { 'operator' => 'OR', 'conditions' => [
     { 'name' => 'ticket.owner_id', 'operator' => 'is', 'pre_condition' => 'current_user.id', 'value' => [] },
     { 'name' => 'ticket.mention_user_ids', 'operator' => 'is', 'pre_condition' => 'current_user.id', 'value' => [] },
   ] }]],
  ['Open repairs', 'Offene Reparaturen', 'open-repairs', roles, 'state',
   %w[title customer device_type problem_reported owner state pending_time], 'pending_time',
   [not_done, { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => group_ids.('Repairs', 'Repairs::Requests') },
    { 'name' => 'ticket.tags', 'operator' => 'contains one not', 'value' => 'spam, no-info, obsolete, delete' }]],
  ['Spam check', 'Spam prüfen', 'spam-check', coordinator, nil,
   %w[title customer created_at], 'created_at',
   [not_done, { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => group_ids.('Spam check') }]],
].freeze

WORK_OVERVIEWS.each_with_index do |(name, german, link, overview_roles, group_by, view, order, conditions), index|
  overview = Overview.find_or_initialize_by(name: tr(name, german))
  overview.assign_attributes(
    link:      overview.link.presence || link,
    prio:      overview.prio || (8000 + index),
    condition: { 'operator' => 'AND', 'conditions' => conditions },
    order:     { 'by' => order, 'direction' => 'ASC' },
    group_by:  group_by,
    view:      { 'd' => view, 's' => view, 'm' => view, 'view_mode_default' => 's' },
    roles:     overview_roles,
  )
  overview.active = true if overview.new_record?
  overview.created_by_id ||= 1
  overview.updated_by_id = 1
  overview.save! if overview.new_record? || overview.changed?
end

puts "Übersichten zum Arbeiten: #{Overview.where(name: WORK_OVERVIEWS.map(&:first)).pluck(:name).join(', ')}"
