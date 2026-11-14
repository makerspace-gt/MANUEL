# Groups and roles of a repair group, loaded by zammad/setup.rb. The names are neutral, because
# Repair Café is the name of one network and initiatives call themselves differently.
# Agents work on the tickets of both groups. Moderators also maintain macros, text modules and the
# knowledge base and see the reports. Admins keep the roles Zammad brings.
# Requests that have no date yet wait in the subgroup Requests, tickets with a date move to Repairs.
# Zammad does not translate group names, they show in English for everyone.
# An existing group with another name, for example Repair Café Anfragen, should be renamed and moved
# before the first run, otherwise a second group is created.

GROUPS = ['Repairs', 'Repairs::Requests'].freeze

ROLES = {
  'Repair agents'     => {
    note:        'Works on repairs and requests',
    permissions: %w[ticket.agent knowledge_base.reader user_preferences],
  },
  'Repair moderators' => {
    note:        'Works on repairs and requests and maintains macros, text modules and the knowledge base',
    permissions: %w[ticket.agent knowledge_base.editor admin.macro admin.text_module report user_preferences],
  },
}.freeze

# The parent comes first, Zammad finds it from the path in the name of the subgroup
GROUPS.each do |name|
  group = Group.find_or_initialize_by(name: name)
  group.update!(active: true, created_by_id: group.created_by_id || 1, updated_by_id: 1)
end

ROLES.each do |name, spec|
  role = Role.find_or_initialize_by(name: name)
  role.update!(note: spec[:note], active: true, default_at_signup: false,
               created_by_id: role.created_by_id || 1, updated_by_id: 1)
  spec[:permissions].each { |key| role.permission_grant(key) }
  role.group_names_access_map = role.group_names_access_map.merge(GROUPS.index_with('full'))
  role.save!
end

puts "Gruppen #{Group.where(name: GROUPS).pluck(:name).join(', ')}, Rollen #{Role.where(name: ROLES.keys).pluck(:name).join(', ')}"
