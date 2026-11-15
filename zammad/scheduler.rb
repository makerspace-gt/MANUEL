# Scheduler entries for the initializers in zammad/, loaded by zammad/setup.rb. An entry is only added when
# its module is loaded, see zammad/compose.yml, otherwise the scheduler would call a missing method.

SCHEDULES = {
  'ManuelEventTags.run' => ['Keep date tags, next-event and monthly overviews up to date', 1.hour],
  'ManuelVoicemail.run'  => ['Transcribe voicemails locally', 5.minutes],
}.freeze

SCHEDULES.each do |method, (name, period)|
  next if !Object.const_defined?(method.split('.').first)

  entry = Scheduler.find_or_initialize_by(method: method)
  entry.update!(name: name, period: period, prio: 2, active: true, created_by_id: entry.created_by_id || 1,
                updated_by_id: 1)
end

puts "Scheduler: #{Scheduler.where(method: SCHEDULES.keys).pluck(:method).join(', ').presence || 'keine Einträge, Module nicht geladen'}"
