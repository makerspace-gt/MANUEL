# Moves the values of older guest fields into the fields of zammad/objects.rb, for a Zammad that was used
# before MANUEL, see docs/adr/0058-felder-des-bestehenden-zammad-uebernehmen.adoc. Runs with rails runner
# after zammad/setup.rb, because the new fields must exist:
#   rails runner zammad/migrate_guest_fields.rb           shows what would change
#   MANUEL_MIGRATE=apply rails runner zammad/migrate_guest_fields.rb
#
# A value is copied only where the new field is still empty, so the script can run again. Users are written
# without callbacks, so no trigger fires. Triggers, scheduled jobs, macros, overviews and core workflows
# that name an old field are switched to the new one. Last, the old fields are deactivated, their values
# stay in the database. Other initiatives replace OLD_GUEST_FIELDS with their own names.

APPLY = ENV['MANUEL_MIGRATE'] == 'apply' unless defined?(APPLY)

# old name => new name, the values are yes or no in both
OLD_GUEST_FIELDS = {
  'einverstaendnis_hausordnung' => 'house_rules_consent',
  'foerdermitgliedschaft'       => 'supporting_member',
  'newsletter_repair_cafe'      => 'newsletter_repair_events',
  'newsletter_bearbeitet'       => 'newsletter_processed',
}.freeze

existing = OLD_GUEST_FIELDS.keys.select { |name| User.column_names.include?(name) }
missing_new = OLD_GUEST_FIELDS.values.reject { |name| User.column_names.include?(name) }
abort "Neue Felder fehlen: #{missing_new.join(', ')}. Erst zammad/setup.rb ausführen." if missing_new.any?
if existing.empty?
  puts 'Keine alten Felder am Gast gefunden, nichts zu tun'
  return
end

# 1. Values of the users. The new fields start as false, so true is copied, false needs no copy.
copied = Hash.new(0)
User.where(existing.map { |name| "#{name} = TRUE" }.join(' OR ')).find_each do |user|
  changes = existing.each_with_object({}) do |old, result|
    new = OLD_GUEST_FIELDS[old]
    next if user[old] != true || user[new] == true

    result[new] = true
    copied[new] += 1
  end
  next if changes.empty? || !APPLY

  user.update_columns(changes) # rubocop:disable Rails/SkipsModelValidations
  user.search_index_update_backend if SearchIndexBackend.enabled?
end

# 2. Rules that name an old field, as customer.<name> or user.<name> in conditions, views and orders
pattern = %r{\b(customer|user)\.(#{existing.join('|')})\b}
rules = Hash.new(0)
{ Trigger => %i[condition perform], Job => %i[condition perform], Macro => %i[perform],
  Overview => %i[condition order view], CoreWorkflow => %i[condition_selected condition_saved perform] }.each do |model, columns|
  model.find_each do |record|
    changed = columns.select do |column|
      before = record.send(column)
      next false if before.blank?

      json = before.to_json
      next false if !json.match?(pattern)

      record.send(:"#{column}=", JSON.parse(json.gsub(pattern) { "#{::Regexp.last_match(1)}.#{OLD_GUEST_FIELDS[::Regexp.last_match(2)]}" }))
      true
    end
    next if changed.empty?

    rules[model.name] += 1
    puts "#{model.name} #{record.name}: #{changed.join(', ')}"
    record.save! if APPLY
  end
end

# 3. Deactivate the old fields, their values stay
active = existing.select { |name| ObjectManager::Attribute.get(object: 'User', name: name)&.active }
active.each { |name| ObjectManager::Attribute.get(object: 'User', name: name).update!(active: false) } if APPLY

mode = APPLY ? 'übernommen' : 'würden übernommen (Probelauf, MANUEL_MIGRATE=apply zum Ausführen)'
puts "Werte am Gast #{mode}: #{copied.map { |name, n| "#{name} #{n}" }.join(', ').presence || 'keine'}"
puts "Regeln umgestellt: #{rules.map { |name, n| "#{name} #{n}" }.join(', ').presence || 'keine'}"
puts "Alte Felder am Gast #{APPLY ? 'abgeschaltet' : 'würden abgeschaltet'}: #{active.join(', ').presence || 'keine'}"
ObjectManager::Attribute.migration_execute if APPLY && active.any?
