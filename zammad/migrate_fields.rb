# Moves the values of older ticket fields into the fields of zammad/objects.rb, for a Zammad that was
# used before MANUEL, see docs/adr/0058-felder-des-bestehenden-zammad-uebernehmen.adoc. Runs with rails
# runner after zammad/setup.rb, because the new fields must exist:
#   rails runner zammad/migrate_fields.rb           shows what would change
#   MANUEL_MIGRATE=apply rails runner zammad/migrate_fields.rb
#
# It copies a value only where the new field is still empty, so it can run again. Tickets are written
# without callbacks, so no trigger fires and no guest gets an email. Triggers, scheduled jobs, macros,
# overviews and core workflows that use an old field are switched to the new one. Rules that code in
# zammad/ replaces, listed in REPLACED_RULES, are switched off. Press triggers and tags with older names
# are renamed. Last, the old fields are deactivated, their values stay in the database.
#
# The mapping below is the one of the Repair Café of Makerspace Gütersloh. Other initiatives replace
# OLD_FIELDS with their own names and values.

APPLY = ENV['MANUEL_MIGRATE'] == 'apply'

# old name => [new name, { old value => new value }], nil as value map copies the value unchanged
OLD_FIELDS = {
  'marke'                  => ['brand', nil],
  'bezeichnung'            => ['device_model', nil],
  'baujahr'                => ['year_of_manufacture', nil],
  'notiz'                  => ['problem_reported', nil],
  'hack'                   => ['solution', nil],
  'stromversorgung'        => ['power_supply', { '230 V' => 'mains', 'mit Netzteil' => 'adapter',
                                                 'Akku' => 'rechargeable', 'Batterie' => 'battery' }],
  # No was the default and proves no test, so it becomes empty
  'vde_0701_0702_geprueft' => ['safety_test', { true => 'yes', 'true' => 'yes', false => nil, 'false' => nil }],
  'ergebnis'               => ['repair_result', nil],
}.freeze

# The German values of the result tree come from RESULT_TREE in objects.rb, plus older spellings
def result_map
  map = {}
  RESULT_TREE.each do |(english, german), children|
    map[german] = english
    children.each { |child_en, child_de| map["#{german}::#{child_de}"] = "#{english}::#{child_en}" }
  end
  map.merge(
    'vertagt::Ersatzteilbesorgung durch Repair Café'    => 'Postponed::Spare part ordered by the repair group',
    'abgebrochen: Gerät darf nicht mehr genutzt werden' => 'Aborted::Item must not be used any more',
  )
end

load File.join(__dir__, 'result_tree.rb') unless defined?(RESULT_TREE)

FIELD_MAP = OLD_FIELDS.to_h do |old, (new, values)|
  [old, [new, old == 'ergebnis' ? result_map : values]]
end.freeze

# Rules of our Zammad that code in zammad/ replaces. They are switched off, not deleted.
REPLACED_RULES = {
  Macro => ['1. Tag Date', '2. Untag next-event'],
  # The cancellation of zammad/workflows.rb asks first, a proposal left open after the date becomes no-show
  Job   => ['Automatisch am Vortag schließen, wenn keinen Terminbestätigung erfolgt'],
}.freeze

replaced = []
REPLACED_RULES.each do |model, names|
  model.where(name: names, active: true).find_each do |record|
    replaced << "#{model.name} #{record.name}"
    record.update!(active: false) if APPLY
  end
end
puts "Ersetzte Regeln #{APPLY ? 'abgeschaltet' : 'würden abgeschaltet'}: #{replaced.join(', ').presence || 'keine'}"

# Press triggers named "Pressemitteilung <medium>" get the name zammad/press.rb looks for, their recipient
# joins the organization Presse. active stays as it is, the next run of setup.rb takes the text from
# zammad/texts/press_release.de.html, see docs/adr/0066-pressemitteilung-und-beitraege-aus-vorlagen.adoc.
press = Organization.find_by(name: 'Presse')
renamed = Trigger.where('name LIKE ?', 'Pressemitteilung %').map do |trigger|
  medium = trigger.name.delete_prefix('Pressemitteilung ')
  users = User.where(id: Array(trigger.perform.dig('notification.email', 'recipient')).filter_map { |r| r[%r{\Auserid_(\d+)\z}, 1] })
  if APPLY
    trigger.update!(name: "Press release: #{medium}", updated_by_id: 1)
    users.each do |user|
      next if press.nil? || user.all_organization_ids.include?(press.id)

      user.organization_id.nil? ? user.update!(organization_id: press.id) : user.update!(organization_ids: user.organization_ids | [press.id])
    end
  end
  "#{medium} (#{users.size} Empfänger)"
end
puts "Pressemitteilungen #{APPLY ? 'übernommen' : 'würden übernommen'}: #{renamed.join(', ').presence || 'keine'}" \
     "#{press ? '' : ', Organisation Presse fehlt, erst zammad/setup.rb ausführen'}"

# Tags are English like all names in Zammad. Tag::Item.rename also changes overviews, triggers, jobs and
# postmaster filters, macros it leaves out. When the new tag exists already, rename merges and changes no
# rule, so both steps run here for every model.
RENAMED_TAGS = { 'abgelehnt' => 'obsolete' }.freeze

RENAMED_TAGS.each do |old_name, new_name|
  item = Tag::Item.find_by(name: old_name)
  rules = (Tag::Item.all_objects + Macro.all).select do |record|
    %i[condition perform].any? { |field| record.has_attribute?(field) && record[field].to_json.include?(%("#{old_name}")) }
  end
  puts "Tag #{old_name} #{APPLY ? 'heißt jetzt' : 'hieße'} #{new_name}, #{item ? Tag.where(tag_item_id: item.id).count : 0} Tickets, " \
       "Regeln #{rules.map(&:name).join(', ').presence || 'keine'}"
  next if !APPLY

  Tag::Item.rename(id: item.id, name: new_name) if item
  rules.each do |record|
    changed = %i[condition perform].map { |field| record.has_attribute?(field) && Tag::Item.update_tag_values(record[field], old_name, new_name) }.any?
    record.save! if changed
  end
end

existing = OLD_FIELDS.keys.select { |name| Ticket.column_names.include?(name) }
missing_new = OLD_FIELDS.values.map(&:first).reject { |name| Ticket.column_names.include?(name) }
abort "Neue Felder fehlen: #{missing_new.join(', ')}. Erst zammad/setup.rb ausführen." if missing_new.any?
if existing.empty?
  puts 'Keine alten Felder gefunden, nichts zu tun'
  return
end

def convert(old, value)
  _new, values = FIELD_MAP[old]
  return value if values.nil? || value.nil?
  return values[value] if values.key?(value)

  warn "Unbekannter Wert #{value.inspect} in #{old}, bleibt leer"
  nil
end

# 1. Values in the tickets
copied = Hash.new(0)
unknown = Hash.new(0)
Ticket.where(existing.map { |name| "#{name} IS NOT NULL" }.join(' OR ')).find_each do |ticket|
  changes = {}
  existing.each do |old|
    value = ticket[old]
    next if value.nil? || value == ''

    new, = FIELD_MAP[old]
    next if ticket[new].present?

    converted = convert(old, value)
    unknown[old] += 1 if converted.nil? && FIELD_MAP[old][1] && !FIELD_MAP[old][1].key?(value)
    next if converted.nil?

    changes[new] = converted
    copied[new] += 1
  end
  next if changes.empty? || !APPLY

  ticket.update_columns(changes) # rubocop:disable Rails/SkipsModelValidations
  ticket.search_index_update_backend if SearchIndexBackend.enabled?
end

# 2. Rules that use an old field
def rewrite(data)
  case data
  when Hash
    data.each_with_object({}) do |(key, value), result|
      old = key.to_s.delete_prefix('ticket.')
      if key.to_s.start_with?('ticket.') && FIELD_MAP.key?(old)
        result["ticket.#{FIELD_MAP[old][0]}"] = rewrite_values(old, value)
      elsif key.to_s == 'by' && value.is_a?(String) && FIELD_MAP.key?(value)
        result[key] = FIELD_MAP[value][0]
      elsif key.to_s == 'name' && value.is_a?(String) && value.start_with?('ticket.') && FIELD_MAP.key?(value.delete_prefix('ticket.'))
        result[key] = "ticket.#{FIELD_MAP[value.delete_prefix('ticket.')][0]}"
        result['__old'] = value.delete_prefix('ticket.')
      else
        result[key] = rewrite(value)
      end
    end.then { |hash| fix_condition_values(hash) }
  when Array
    data.map { |item| item.is_a?(String) && FIELD_MAP.key?(item) ? FIELD_MAP[item][0] : rewrite(item) }
  else
    data
  end
end

# Conditions in the newer format name the field in "name" and keep the value beside it
def fix_condition_values(hash)
  old = hash.delete('__old')
  return hash if old.nil?

  hash.key?('value') ? hash.merge('value' => map_value(old, hash['value'])) : hash
end

def rewrite_values(old, value)
  return value unless value.is_a?(Hash) && value.key?('value')

  value.merge('value' => map_value(old, value['value']))
end

def map_value(old, value)
  return value.filter_map { |item| convert(old, item) } if value.is_a?(Array)

  value.nil? ? nil : convert(old, value)
end

rules = Hash.new(0)
{ Trigger => %i[condition perform], Job => %i[condition perform], Macro => %i[perform],
  Overview => %i[condition order view], CoreWorkflow => %i[condition_selected condition_saved perform] }.each do |model, columns|
  model.find_each do |record|
    changed = columns.select do |column|
      before = record.send(column)
      next false if before.blank?

      after = rewrite(before.deep_dup)
      next false if after == before

      record.send(:"#{column}=", after)
      true
    end
    next if changed.empty?

    rules[model.name] += 1
    record.save! if APPLY
  end
end

# 3. Deactivate the old fields, their values stay
active = existing.select { |name| ObjectManager::Attribute.get(object: 'Ticket', name: name)&.active }
active.each { |name| ObjectManager::Attribute.get(object: 'Ticket', name: name).update!(active: false) } if APPLY

mode = APPLY ? 'übernommen' : 'würden übernommen (Probelauf, MANUEL_MIGRATE=apply zum Ausführen)'
puts "Werte #{mode}: #{copied.map { |name, n| "#{name} #{n}" }.join(', ').presence || 'keine'}"
puts "Unbekannte Werte: #{unknown.map { |name, n| "#{name} #{n}" }.join(', ')}" if unknown.any?
puts "Regeln umgestellt: #{rules.map { |name, n| "#{name} #{n}" }.join(', ').presence || 'keine'}"
puts "Alte Felder #{APPLY ? 'abgeschaltet' : 'würden abgeschaltet'}: #{active.join(', ').presence || 'keine'}"
ObjectManager::Attribute.migration_execute if APPLY && active.any?
