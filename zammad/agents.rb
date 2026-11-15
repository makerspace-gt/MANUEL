# AI agents of MANUEL that only change internal data, loaded by zammad/setup.rb, see
# docs/adr/0067-betreff-aus-marke-und-art-schreiben.adoc.
#
# The title agent is the built-in type Ticket Title Rewriter with our own instruction and context. Zammad
# lays the definition of an agent over the defaults of its type (app/models/ai/agent.rb). It sees brand,
# device type and the first article, not the current title and writes "Miele Staubsauger", the brand only when known.
# A trigger runs it once a ticket is in Repairs, so the subject of the guest stays while it is a request,
# and again when device type or brand change there. New rules are active only when an AI provider is
# set, a later run never changes active.

TITLE_AGENT = 'MANUEL: Title from brand and device'.freeze

title_agent = AI::Agent.find_or_initialize_by(name: TITLE_AGENT)
title_agent.assign_attributes(
  agent_type: 'TicketTitleRewriter',
  definition: {
    'role_description' => 'You write short ticket titles for a repair café, so helpers see at a glance which device a guest brings.',
    'instruction'      => <<~TEXT.strip,
      Stick to the following principles:

      - Write the title as the brand followed by the kind of device in German, for example "Miele Staubsauger" or "Philips Wasserkocher".
      - The ticket attributes brand and device_type always win over the first article, which may name an older device.
      - Take brand and device from the first article only when the attribute is empty.
      - Leave the brand out when it is unknown, never guess it. Then the title is only the kind of device, for example "Staubsauger".
      - No model numbers, no defect, no names of persons, at most 50 characters.
      - Never explain your given answer.
      - Only answer with the value in the "title" field inside the JSON structure.
    TEXT
    # Without the current title, otherwise the model keeps the old device or brand when they change
    'entity_context'   => { 'object_attributes' => %w[brand device_type], 'articles' => 'first' },
  },
  note:       'Title as brand and device for the Repair Café, ADR 67',
)
title_agent.active = true if title_agent.new_record?
title_agent.created_by_id ||= 1
title_agent.updated_by_id = 1
title_agent.save! if title_agent.new_record? || title_agent.changed?

repairs = Group.find_by!(name: 'Repairs').id.to_s
trigger = Trigger.find_or_initialize_by(name: tr('Repairs: Title by MANUEL', 'Repairs: Betreff durch MANUEL'))
trigger.assign_attributes(
  condition:                { 'operator' => 'AND', 'conditions' => [
    { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => [repairs] },
    { 'name' => 'ticket.tags', 'operator' => 'contains one not', 'value' => 'spam, no-info, obsolete, delete' },
    { 'operator' => 'OR', 'conditions' => [
      { 'name' => 'ticket.action', 'operator' => 'is', 'value' => 'create' },
      # Confirming moves the ticket to Repairs in another trigger of the same run, has changed only sees the state
      { 'operator' => 'AND', 'conditions' => [
        { 'name' => 'ticket.state_id', 'operator' => 'has changed', 'value' => [] },
        { 'name' => 'ticket.state_id', 'operator' => 'is', 'value' => [Ticket::State.find_by!(name: 'pending reminder').id.to_s] },
      ] },
      { 'name' => 'ticket.device_type', 'operator' => 'has changed', 'value' => [] },
      { 'name' => 'ticket.brand', 'operator' => 'has changed', 'value' => [] },
    ] },
  ] },
  perform:                  { 'ai.ai_agent' => { 'ai_agent_id' => [title_agent.id] } },
  activator:                'action',
  execution_condition_mode: 'selective',
  note:                     'Title from brand and device once the appointment is confirmed, ADR 67',
)
trigger.active = Setting.get('ai_provider').present? if trigger.new_record?
trigger.created_by_id ||= 1
trigger.updated_by_id = 1
trigger.save! if trigger.new_record? || trigger.changed?

puts "Agent #{title_agent.name}, aktiv #{title_agent.active}, Trigger aktiv #{trigger.active}"
