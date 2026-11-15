# Checklist template for a repair at the Repair Café, loaded by zammad/setup.rb, see
# docs/adr/0060-ablaeufe-des-bestehenden-zammad-als-code-uebernehmen.adoc.
# Zammad does not translate checklists, so the items come from zammad/texts/checklist.<lang>.txt in the
# default language of Zammad. The item on suggestions of MANUEL reminds of the two macros for indicator 3
# of ADR 32. A template of an older Zammad named "Repair Café" is renamed and gets the items.

CHECKLIST_NAME = 'Repairs'.freeze

language = Setting.get('locale_default').to_s.start_with?('de') ? 'de' : 'en'
checklist_items = File.readlines(File.join(__dir__, 'texts', "checklist.#{language}.txt"), chomp: true).compact_blank

template = ChecklistTemplate.find_by(name: CHECKLIST_NAME)
template ||= ChecklistTemplate.find_by(name: 'Repair Café')&.tap { |legacy| legacy.update!(name: CHECKLIST_NAME, updated_by_id: 1) }
template ||= ChecklistTemplate.create!(name: CHECKLIST_NAME, active: true, created_by_id: 1, updated_by_id: 1)
current = template.sorted_item_ids.filter_map { |id| template.items.find_by(id: id)&.text }
template.replace_items!(checklist_items) if current != checklist_items

puts "Checkliste #{template.name}: #{template.items.count} Punkte, aktiv #{template.active}"
