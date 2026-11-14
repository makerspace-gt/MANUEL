# Writes the translations collected by tr() in zammad/setup.rb as custom translations, the same as
# Admin, Translations in the Zammad interface. A string Zammad already translates itself, such as Yes,
# keeps the translation of Zammad.
#
# guest_wording.tsv is the exception. There is no commercial relationship with the people who bring
# their items, so Zammad's own words like Customer become Guest and Gast. These rows change Zammad's
# translations the same way as editing them under Admin, Translations. Zammad keeps such changes when
# it updates, and "Reset" there brings back its own wording.

require 'csv'

def save_translation(locale, source, target, override:)
  translation = Translation.find_or_initialize_by(locale: locale, source: source)
  return false if translation.persisted? && translation.target == target
  return false if translation.is_synchronized_from_codebase && !override

  translation.target = target
  translation.target_initial = target if translation.new_record?
  translation.created_by_id ||= 1
  translation.updated_by_id = 1
  translation.save!
  true
end

TRANSLATIONS.each do |locale, strings|
  changed = strings.count { |source, target| save_translation(locale, source, target, override: false) }
  puts "Übersetzungen #{locale}: #{strings.size}, davon neu oder geändert #{changed}"
end

wording = CSV.read(File.join(__dir__, 'guest_wording.tsv'), col_sep: "\t", headers: true, quote_char: "\x00")
changed = wording.sum do |row|
  %w[en-us de-de].count { |locale| save_translation(locale, row['source'], row[locale], override: true) }
end
puts "Gast statt Kunde: #{wording.size} Texte, davon neu oder geändert #{changed}"
