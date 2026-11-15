# Article type walk-in and the pre filter for contact data, loaded by zammad/setup.rb, see
# docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc. The filter is only registered when its
# class is loaded, see zammad/compose.yml.

Ticket::Article::Type.find_or_create_by!(name: 'walk-in') do |type|
  type.communication = true
  type.created_by_id = 1
  type.updated_by_id = 1
end

if Object.const_defined?(:ManuelContactFilter)
  Setting.create_if_not_exists(
    title:       'Defines postmaster filter.',
    name:        '6400_postmaster_filter_manuel_contact',
    area:        'Postmaster::PreFilter',
    description: 'Takes over contact data from the contact form and from sipgate, see MANUEL.',
    options:     {},
    state:       'ManuelContactFilter',
    frontend:    false,
  )
end

puts "Eingangswege: Typ walk-in, Filter #{Setting.find_by(name: '6400_postmaster_filter_manuel_contact') ? 'registriert' : 'nicht geladen'}"
