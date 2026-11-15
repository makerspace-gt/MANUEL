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
