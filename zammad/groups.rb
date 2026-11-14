# Group and roles of the Repair Café, loaded by zammad/setup.rb.
# Agents work on the tickets of the group. Moderators also maintain macros, text modules and the
# knowledge base and see the reports. Admins keep the roles Zammad brings. The names stay English,
# as in our Zammad.
# An existing group with another name, for example Repair Café Anfragen, should be renamed to
# Repair Café before the first run, otherwise a second group is created.

GROUP = 'Repair Café'.freeze

ROLES = {
  'Repair Café Agents'     => {
    note:        'Works on the tickets of the Repair Café',
    permissions: %w[ticket.agent knowledge_base.reader user_preferences],
  },
  'Repair Café Moderators' => {
    note:        'Works on the tickets of the Repair Café and maintains macros, text modules and the knowledge base',
    permissions: %w[ticket.agent knowledge_base.editor admin.macro admin.text_module report user_preferences],
  },
}.freeze

group = Group.find_or_initialize_by(name: GROUP)
group.update!(active: true, created_by_id: group.created_by_id || 1, updated_by_id: 1)

ROLES.each do |name, spec|
  role = Role.find_or_initialize_by(name: name)
  role.update!(note: spec[:note], active: true, default_at_signup: false,
               created_by_id: role.created_by_id || 1, updated_by_id: 1)
  spec[:permissions].each { |key| role.permission_grant(key) }
  role.group_names_access_map = role.group_names_access_map.merge(GROUP => 'full')
  role.save!
end

puts "Gruppe #{group.name}, Rollen #{Role.where(name: ROLES.keys).pluck(:name).join(', ')}"
