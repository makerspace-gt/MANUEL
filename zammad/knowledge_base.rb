# Knowledge base for repair guides, loaded by zammad/setup.rb. German is the primary language, because
# guests and helpers write German. British English is the second one for answers taken from the Open
# Repair Data, as the Open Repair Alliance and Restarters.net write it. Colours and layout are the defaults of the dialog in Zammad
# (app/assets/javascripts/app/controllers/knowledge_base/new_controller.coffee).
# An existing knowledge base keeps its settings and only gets missing languages. Zammad allows only one.

KB_LOCALES = %w[de-de en-gb].freeze

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

# House rules as an answer in every language of the knowledge base, from zammad/texts/house_rules.<lang>.md,
# see docs/adr/0060-ablaeufe-des-bestehenden-zammad-als-code-uebernehmen.adoc. A new answer is visible
# internally only. Publishing it is a decision of the team, a later run never changes the visibility.
KB_TEXTS = {
  'de' => { category: 'Informationen', title: 'Hausordnung' },
  'en' => { category: 'Information', title: 'House rules' },
}.freeze

def kb_html(path)
  items = File.readlines(path, chomp: true).filter_map { |line| line.delete_prefix('- ').strip.presence }
  "<ul>#{items.map { |item| "<li>#{CGI.escapeHTML(item)}</li>" }.join}</ul>"
end

kb_locales = knowledge_base.kb_locales.includes(:system_locale).to_a
lang = ->(kb_locale) { kb_locale.system_locale.locale[0, 2] }
category = KnowledgeBase::Category::Translation.find_by(title: KB_TEXTS.values.map { |t| t[:category] }, kb_locale: kb_locales)&.category
category ||= KnowledgeBase::Category.create!(knowledge_base: knowledge_base, category_icon: 'f05a',
                                             translations_attributes: kb_locales.filter_map { |l| KB_TEXTS[lang.(l)] && { kb_locale: l, title: KB_TEXTS[lang.(l)][:category] } })
answer = KnowledgeBase::Answer::Translation.find_by(title: KB_TEXTS.values.map { |t| t[:title] }, kb_locale: kb_locales)&.answer
answer ||= KnowledgeBase::Answer.create!(category: category, internal_at: Time.zone.now)
kb_locales.each do |kb_locale|
  texts = KB_TEXTS[lang.(kb_locale)]
  path = File.join(__dir__, 'texts', "house_rules.#{lang.(kb_locale)}.md")
  next if texts.nil? || !File.exist?(path)

  translation = answer.translations.find_or_initialize_by(kb_locale: kb_locale)
  body = kb_html(path)
  next if translation.persisted? && translation.title == texts[:title] && translation.content&.body == body

  translation.title = texts[:title]
  translation.content_attributes = { body: body }
  translation.save!
end
puts "Hausordnung in der Wissensdatenbank: #{answer.translations.map(&:title).join(', ')}, #{answer.can_be_published_aasm.current_state}"
