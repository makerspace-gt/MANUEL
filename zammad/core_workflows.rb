# Core workflows that show our ticket fields only where they are needed, loaded by zammad/setup.rb
# after objects.rb, see docs/adr/0060-ablaeufe-des-bestehenden-zammad-als-code-uebernehmen.adoc.
#
# The first workflow hides all fields of objects.rb, the next ones show them again by group. Zammad runs
# core workflows by priority, a later one wins (app/models/core_workflow.rb). Requests and Repairs show
# the same device fields, because a request already holds the device. Events holds the statistics of one
# Repair Café, so it shows only donations and needs. Workflows of an older Zammad stay as they are.

DEVICE_FIELDS = %w[device_type brand device_model year_of_manufacture product_age product_age_qualifier power_supply
                   problem_reported problem_found solution repair_result hazards safety_test].freeze
EVENT_FIELDS = %w[donations needs].freeze

def core_workflow(name, german, priority:, groups: nil, fields:, operator:)
  record = CoreWorkflow.find_or_initialize_by(name: tr(name, german))
  record.assign_attributes(
    object:             'Ticket',
    preferences:        { 'screen' => %w[create_middle edit] },
    condition_saved:    {},
    condition_selected: groups ? { 'ticket.group_id' => { 'operator' => 'is', 'value' => groups.map { |g| Group.find_by!(name: g).id.to_s } } } : {},
    perform:            fields.to_h { |field| ["ticket.#{field}", { 'operator' => operator, operator => 'true' }] },
    active:             true,
    stop_after_match:   false,
    changeable:         true,
    priority:           priority,
  )
  record.created_by_id ||= 1
  record.updated_by_id = 1
  record.save! if record.new_record? || record.changed?
end

core_workflow('Repairs: Hide repair fields', 'Repairs: Reparaturfelder ausblenden', priority: 510,
              fields: DEVICE_FIELDS + EVENT_FIELDS, operator: 'hide')
core_workflow('Repairs: Show device fields', 'Repairs: Gerätefelder zeigen', priority: 520,
              groups: ['Repairs', 'Repairs::Requests'], fields: DEVICE_FIELDS, operator: 'show')
core_workflow('Repairs: Show event fields', 'Repairs: Felder des Termins zeigen', priority: 520,
              groups: ['Repairs::Events'], fields: EVENT_FIELDS, operator: 'show')

puts "Core Workflows: #{CoreWorkflow.where('name LIKE ?', 'Repairs: %').order(:priority).pluck(:name).join(', ')}"
