# Brings an export of zammad/export_tickets.py into a fresh test instance, see
# docs/adr/0069-nur-tickets-des-repair-cafe-in-die-testinstanz-uebernehmen.adoc. Runs with rails runner
# inside the railsserver of the test instance, in two steps:
#   rails runner zammad/import_tickets.rb fields DIR   creates the fields of the old Zammad, then restarts
#   rails runner zammad/import_tickets.rb data DIR     users, tickets, articles, attachments and tags
# DIR holds tickets.json, users.json and attachments/ from the export, for the first step also
# object_manager_attributes.json from zammad/export_config.py.
#
# The old fields come first, so zammad/migrate_fields.rb can be tried on the real values as in the real
# Zammad. Import mode is on during the data step, so no trigger runs and no mail goes out. Tickets keep
# number, times, state and owner, users are matched by email. A second run skips tickets that exist.
# Never run this against the real Zammad.

step, dir = ARGV.first(2)
abort 'Aufruf: rails runner zammad/import_tickets.rb fields|data DIR' if %w[fields data].exclude?(step) || dir.blank?

# Groups of the old Zammad and their names here, see zammad/README.md
GROUP_MAP = {
  'Repair Café'          => 'Repairs',
  'Repair Café Anfragen' => 'Repairs::Requests',
}.freeze

read = ->(name) { JSON.parse(File.read(File.join(dir, name), encoding: 'utf-8')) }
UserInfo.current_user_id = 1

if step == 'fields'
  created = []
  read.('object_manager_attributes.json').each do |attr|
    next if %w[Ticket User].exclude?(attr['object']) || !attr['editable']
    next if ObjectManager::Attribute.get(object: attr['object'], name: attr['name'])

    ObjectManager::Attribute.add(
      object: attr['object'], name: attr['name'], display: attr['display'], data_type: attr['data_type'],
      data_option: attr['data_option'].deep_symbolize_keys, screens: attr['screens'] || {}, position: attr['position'] || 1500,
      active: attr['active'], editable: true, created_by_id: 1, updated_by_id: 1
    )
    created << "#{attr['object']}.#{attr['name']}"
  end
  puts "Alte Felder angelegt: #{created.join(', ').presence || 'keine'}"
  # Zammad restarts its processes after changing the schema
  ObjectManager::Attribute.migration_execute if created.any?
  return
end

tickets = read.('tickets.json')
users = read.('users.json')
ticket_columns = Ticket.column_names
user_columns = User.column_names
custom = ->(object) { ObjectManager::Attribute.where(object_lookup_id: ObjectLookup.by_name(object), editable: true).pluck(:name) }
ticket_custom = custom.('Ticket') & ticket_columns
user_custom = custom.('User') & user_columns
counts = Hash.new(0)

Setting.set('import_mode', true)
begin
  user_map = { 1 => 1 }
  agent_roles = Role.where(name: ['Agent', 'Repair Agent'])
  customer_roles = Role.where(name: 'Customer')
  users.each do |data|
    email = data['email'].to_s.downcase.presence
    login = (data['login'].presence || email || "guest-#{data['id']}").downcase
    user = (email && User.find_by(email: email)) || User.find_by(login: login)
    if user.nil?
      agent = Array(data['roles']).intersect?(%w[Agent Admin])
      user = User.new(login: login, email: email.to_s, firstname: data['firstname'], lastname: data['lastname'],
                      phone: data['phone'].to_s, mobile: data['mobile'].to_s, active: data['active'] != false,
                      roles: agent ? agent_roles : customer_roles, created_at: data['created_at'])
      user_custom.each { |field| user[field] = data[field] if data.key?(field) }
      user.save!
      counts['Nutzer neu'] += 1
    end
    user_map[data['id']] = user.id
  end

  groups = GROUP_MAP.transform_values { |name| Group.find_by!(name: name) }
  states = Ticket::State.all.index_by(&:name)
  priorities = Ticket::Priority.all.index_by(&:name)
  types = Ticket::Article::Type.all.index_by(&:name)
  senders = Ticket::Article::Sender.all.index_by(&:name)

  tickets.each do |data|
    next counts['Ticket schon da'] += 1 if Ticket.exists?(number: data['number'])

    group = groups[data['group']] or next counts["Gruppe #{data['group']} ohne Ziel"] += 1
    ticket = Ticket.new(
      number: data['number'], title: data['title'], group: group,
      state: states[data['state']] || states['open'], priority: priorities[data['priority']] || priorities['2 normal'],
      customer_id: user_map[data['customer_id']] || 1, owner_id: user_map[data['owner_id']] || 1,
      pending_time: data['pending_time'], created_at: data['created_at'], updated_at: data['updated_at'],
      created_by_id: user_map[data['created_by_id']] || 1, updated_by_id: user_map[data['updated_by_id']] || 1
    )
    ticket_custom.each { |field| ticket[field] = data[field] if data.key?(field) }
    ticket.save!

    Array(data['articles']).sort_by { |a| a['id'] }.each do |a|
      article = Ticket::Article.create!(
        ticket_id: ticket.id, type: types[a['type']] || types['note'], sender: senders[a['sender']] || senders['Customer'],
        from: a['from'], to: a['to'], cc: a['cc'], subject: a['subject'], reply_to: a['reply_to'],
        message_id: a['message_id'], in_reply_to: a['in_reply_to'], content_type: a['content_type'].presence || 'text/plain',
        body: a['body'].to_s, internal: a['internal'], created_at: a['created_at'], updated_at: a['updated_at'],
        created_by_id: user_map[a['created_by_id']] || 1, updated_by_id: user_map[a['updated_by_id']] || 1
      )
      # Zammad sets the author from the current user, the import keeps the one of the old Zammad
      article.update_columns(created_by_id: user_map[a['created_by_id']] || 1, updated_by_id: user_map[a['updated_by_id']] || 1) # rubocop:disable Rails/SkipsModelValidations
      Array(a['attachments']).each do |file|
        path = File.join(dir, file['file'].to_s)
        next if file['file'].blank? || !File.exist?(path)

        Store.create!(object: 'Ticket::Article', o_id: article.id, data: File.binread(path), filename: file['filename'],
                      preferences: file['preferences'] || {}, created_by_id: 1)
        counts['Anhänge'] += 1
      end
      counts['Nachrichten'] += 1
    end
    Array(data['tags']).each { |tag| ticket.tag_add(tag, 1) }
    # Saving sets these again, the old values matter for overviews, deletion periods and statistics
    ticket.update_columns(data.slice('created_at', 'updated_at', 'close_at', 'last_contact_at', 'last_contact_customer_at', # rubocop:disable Rails/SkipsModelValidations
                                     'last_contact_agent_at', 'first_response_at').compact)
    counts['Tickets'] += 1
  end
ensure
  Setting.set('import_mode', false)
end

puts "Import: #{counts.map { |k, v| "#{k} #{v}" }.join(', ')}"
puts 'Danach: setup.rb, migrate_fields.rb, migrate_tags.rb und migrate_contacts.rb erst als Probelauf, dann den Suchindex neu bauen.'
