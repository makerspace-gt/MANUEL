# AI provider and Ticket Categorizer of MANUEL, loaded by zammad/setup.rb before agents.rb.
#
# Provider: with MANUEL_OLLAMA_URL, for example http://manuel:11434, a connection to Ollama serves chat with
# MANUEL_OLLAMA_MODEL (default qwen3.6:35b-a3b, ADR 23) and embeddings with MANUEL_OLLAMA_EMBEDDING_MODEL
# (default bge-m3, ADR 21), and the setting ai_provider is switched on. Without the variable nothing changes,
# a connection set by hand stays.
#
# Categorizer: fills the device type of new tickets in Repairs::Requests and Repairs, see
# docs/adr/0040-mit-dem-ticket-categorizer-von-zammad-beginnen.adoc. It offers the A and B entries of
# MANUEL_CATEGORIZER_CLASSES (default eval/categorizer/abc.tsv, also in the image and the
# container). Zammad sends the key of a tree option as its
# label, so every description starts with the German name, see
# docs/adr/0059-art-des-geraets-als-durchsuchbares-baum-feld.adoc. d3:9b checks the result afterwards,
# see zammad/category_check.rb. Like agents.rb, a new trigger is active only when a provider is set, and a
# later run never changes active.

require 'csv'

CATEGORIZER_AGENT = 'MANUEL: Device type'.freeze

ollama_url = ENV['MANUEL_OLLAMA_URL'].presence
if ollama_url
  connection = AI::ProviderConnection.find_or_initialize_by(name: 'MANUEL Ollama')
  connection.assign_attributes(
    provider:          'ollama',
    config:            { 'url'             => ollama_url.chomp('/'),
                         'model'           => ENV.fetch('MANUEL_OLLAMA_MODEL', 'qwen3.6:35b-a3b'),
                         'embedding_model' => ENV.fetch('MANUEL_OLLAMA_EMBEDDING_MODEL', 'bge-m3') },
    default_chat:      true,
    default_embedding: true,
  )
  connection.save! if connection.new_record? || connection.changed?
  Setting.set('ai_provider', true) if !Setting.get('ai_provider')
  puts "KI-Anbieter #{connection.name} mit #{connection.config['model']} und #{connection.config['embedding_model']}"
end

provider = Setting.get('ai_provider').present?

classes_path = ENV.fetch('MANUEL_CATEGORIZER_CLASSES', File.expand_path('../eval/categorizer/abc.tsv', __dir__))
catalog_path = ENV.fetch('MANUEL_CATALOG', File.expand_path('../katalog/kategorien.tsv', __dir__))

if File.exist?(classes_path) && File.exist?(catalog_path) && ObjectManager::Attribute.get(object: 'Ticket', name: 'device_type')
  catalog = CSV.read(catalog_path, col_sep: "\t", headers: true, quote_char: "\x00").to_h { |row| [row['key'], row] }
  chosen = CSV.read(classes_path, col_sep: "\t", headers: true, quote_char: "\x00")
              .select { |row| %w[A B].include?(row['class']) && catalog.key?(row['key']) }
  descriptions = chosen.to_h do |row|
    entry = catalog[row['key']]
    [row['key'], [entry['name'], entry['description']].compact_blank.map { |text| text.strip.chomp('.') }.join('. ')]
  end

  agent = AI::Agent.find_or_initialize_by(name: CATEGORIZER_AGENT)
  agent.assign_attributes(
    agent_type:           'TicketCategorizer',
    type_enrichment_data: { 'category' => 'device_type', 'multiple' => false },
    definition:           { 'instruction_context' => { 'object_attributes' => { 'placeholder.category' => descriptions } } },
    action_definition:    {},
    note:                 'Device type of new tickets from the A and B entries of the catalog, ADR 40',
  )
  agent_save(agent, true)

  trigger = Trigger.find_or_initialize_by(name: tr('Repairs: Categorize device type', 'Repairs: Art des Geräts einordnen'))
  trigger.assign_attributes(
    condition: { 'operator' => 'AND', 'conditions' => [
      { 'name' => 'ticket.action', 'operator' => 'is', 'value' => 'create' },
      { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => workflow_group_ids('Repairs', 'Repairs::Requests') },
      { 'name' => 'ticket.tags', 'operator' => 'contains one not', 'value' => 'spam, no-info, delete, obsolete, EUReCA' },
    ] },
    perform:   { 'ai.ai_agent' => { 'ai_agent_id' => [agent.id] } },
    activator: 'action',
    note:      'Device type of new tickets, ADR 40',
  )
  agent_save(trigger, provider)
  puts "Agent #{agent.name} mit #{descriptions.size} Einträgen, Trigger aktiv #{trigger.active}"
else
  puts 'Categorizer übersprungen, Liste der Klassen, Katalog oder Feld device_type fehlt'
end
