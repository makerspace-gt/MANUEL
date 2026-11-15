# Names instead of keys for tree fields in the context of AI agents, see
# docs/adr/0067-betreff-aus-marke-und-art-schreiben.adoc. Mounted as initializer by zammad/compose.yml.
#
# Zammad expects the value of a tree option to be its path of names and gives agents the value as label
# (app/services/service/ai/agent/run/context/entity/object_attributes/options.rb). The device type stores
# keys after ADR 13, so agents saw "21.18.593" instead of "Aktenvernichter". Where an option has a name of
# its own, the label becomes that name in the default language. Trees whose values are names stay as they are.

module ManuelTreeSelectLabel
  def prepare
    result = super
    return result if result.blank? || result[:label] != result[:value]
    return result if %w[tree_select multi_tree_select].exclude?(object_attribute.data_type)

    name = manuel_option_names[result[:value]]
    return result if name.blank? || name == result[:value]

    result.merge(label: Translation.translate(Setting.get('locale_default').presence || 'en-us', name))
  end

  private

  def manuel_option_names
    historical = object_attribute.data_option[:historical_options]
    return historical if historical.is_a?(Hash) && historical.present?

    flatten = ->(list) { Array(list).flat_map { |o| [[o['value'], o['name']], *flatten.(o['children'])] } }
    flatten.(object_attribute.data_option[:options]).to_h
  end
end

Rails.application.config.to_prepare do
  options = Service::AI::Agent::Run::Context::Entity::ObjectAttributes::Options
  options.prepend(ManuelTreeSelectLabel) if options.ancestors.exclude?(ManuelTreeSelectLabel)
end
