# Writes the translations collected by tr() in zammad/setup.rb as custom translations, the same as
# Admin, Translations in the Zammad interface. A string Zammad already translates itself, such as Yes,
# keeps the translation of Zammad.

TRANSLATIONS.each do |locale, strings|
  added = 0
  strings.each do |source, target|
    next if Translation.exists?(locale: locale, source: source, is_synchronized_from_codebase: true)

    translation = Translation.find_or_initialize_by(locale: locale, source: source)
    next if translation.persisted? && translation.target == target

    translation.update!(target: target, target_initial: target, created_by_id: translation.created_by_id || 1,
                        updated_by_id: 1)
    added += 1
  end
  puts "Übersetzungen #{locale}: #{strings.size}, davon neu oder geändert #{added}"
end
