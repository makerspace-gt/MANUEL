# AI agents of MANUEL, loaded by zammad/setup.rb. They only write internal notes and tags, never to guests,
# see docs/adr/0017-einen-menschen-entscheiden-lassen.adoc.
#
# The solution agent writes a first diagnosis and repair approach, or questions for the guest when the
# ticket says too little, see docs/adr/0061-loesungsansatz-eine-woche-vor-dem-termin-schreiben.adoc. Role and
# instruction come from zammad/prompts/. A trigger runs it once a ticket has the tag next-event and sets
# solution-suggested, so it runs once per ticket. The macro runs it by hand. New rules are active only when
# an AI provider is set, a later run never changes active.

PROMPTS = File.join(__dir__, 'prompts')
SOLUTION_AGENT = 'MANUEL: Solution approach'.freeze
SOLUTION_CONTEXT = %w[device_type brand device_model year_of_manufacture product_age product_age_qualifier
                      power_supply problem_reported problem_found hazards].freeze

def agent_prompt(name)
  File.read(File.join(PROMPTS, name), encoding: 'utf-8').strip
end

provider = Setting.get('ai_provider').present?

agent = AI::Agent.find_or_initialize_by(name: SOLUTION_AGENT)
agent.assign_attributes(
  agent_type:        'CustomAIAgent',
  definition:        {
    'role_description' => agent_prompt('solution_approach.role.md'),
    'instruction'      => agent_prompt('solution_approach.instruction.md'),
    'entity_context'   => { 'object_attributes' => SOLUTION_CONTEXT.select { |f| ObjectManager::Attribute.get(object: 'Ticket', name: f) },
                            'articles' => 'all' },
    'result_structure' => { 'note' => 'string' },
  },
  action_definition: {
    'mapping' => {
      'article.note' => {
        'subject'  => 'Lösungsansatz von MANUEL',
        'body'     => '#{ai_agent_result.note}<p><i>Vorschlag von MANUEL, bitte prüfen und mit den Makros als hilfreich oder nicht hilfreich markieren.</i></p>', # rubocop:disable Lint/InterpolationCheck
        'internal' => 'true',
      },
    },
  },
  note:              'Diagnosis and repair approach as internal note, ADR 61',
)
agent_save(agent, true)

trigger = Trigger.find_or_initialize_by(name: tr('Repairs: Write solution approach', 'Repairs: Lösungsansatz schreiben'))
trigger.assign_attributes(
  condition:                { 'operator' => 'AND', 'conditions' => [
    { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => workflow_group_ids('Repairs', 'Repairs::Requests') },
    { 'name' => 'ticket.tags', 'operator' => 'contains one', 'value' => 'next-event' },
    { 'name' => 'ticket.tags', 'operator' => 'contains one not', 'value' => 'solution-suggested, spam, no-info, delete, obsolete, EUReCA' },
  ] },
  perform:                  { 'ai.ai_agent' => { 'ai_agent_id' => [agent.id] },
                              'ticket.tags' => { 'operator' => 'add', 'value' => 'solution-suggested' } },
  activator:                'action',
  # always, because next-event is a tag and no changed attribute. Its name sorts after Tag next-event.
  execution_condition_mode: 'always',
  note:                     'Solution approach once a week before the appointment, ADR 61',
)
agent_save(trigger, provider)

macro = Macro.find_or_initialize_by(name: tr('Solution approach by MANUEL', 'Lösungsansatz von MANUEL'))
macro.assign_attributes(perform: { 'ai.ai_agent' => { 'ai_agent_id' => [agent.id] } }, ux_flow_next_up: 'none',
                        note: 'Runs the solution agent by hand, ADR 61')
agent_save(macro, true)

puts "Agent #{agent.name}, aktiv #{agent.active}, Trigger aktiv #{trigger.active}, Makro #{macro.name}"
