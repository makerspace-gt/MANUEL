# Knowledge base for repair guides, loaded by zammad/setup.rb. German is the primary language, because
# guests and helpers write German, English is the second one for the answers MANUEL takes from the Open
# Repair Data. Colours and layout are the defaults of the dialog in Zammad
# (app/assets/javascripts/app/controllers/knowledge_base/new_controller.coffee).
# An existing knowledge base keeps its settings and only gets missing languages. Zammad allows only one.

KB_LOCALES = %w[de-de en-us].freeze

Setting.set('kb_multi_lingual_support', true) if KB_LOCALES.many? && !Setting.get('kb_multi_lingual_support')

system_locales = KB_LOCALES.map { |name| Locale.find_by!(locale: name) }
system_locales.each { |locale| locale.update!(active: true) if !locale.active }

knowledge_base = KnowledgeBase.first

if knowledge_base
  missing = system_locales.reject { |locale| knowledge_base.kb_locales.exists?(system_locale_id: locale.id) }
  if missing.any?
    knowledge_base.update!(kb_locales_attributes: missing.map { |locale| { system_locale_id: locale.id, primary: false } })
  end
else
  knowledge_base = KnowledgeBase.create!(
    iconset:               'FontAwesome',
    color_highlight:       '#38ae6a',
    color_header:          '#f9fafb',
    color_header_link:     'hsl(206,8%,50%)',
    homepage_layout:       'grid',
    category_layout:       'grid',
    active:                true,
    kb_locales_attributes: system_locales.each_with_index.map { |locale, index| { system_locale_id: locale.id, primary: index.zero? } }
  )
end

languages = knowledge_base.kb_locales.map { |kb_locale| kb_locale.system_locale.locale }
puts "Wissensdatenbank #{knowledge_base.translations.map(&:title).first}, Sprachen #{languages.join(', ')}, aktiv #{knowledge_base.active}"
