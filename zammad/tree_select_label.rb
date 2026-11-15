# Names instead of keys for tree fields whose values are keys, see
# docs/adr/0067-betreff-aus-marke-und-art-schreiben.adoc. Mounted as initializer by zammad/compose.yml.
#
# Zammad expects the value of a tree option to be its path of names. The device type stores keys after
# ADR 13, so Zammad showed "21.18.593" instead of "Aktenvernichter" in two places:
# - placeholders like #{ticket.device_type.value} in triggers (lib/notification_factory/renderer.rb)
# - the context of AI agents (app/services/service/ai/agent/run/context/entity/object_attributes/options.rb)
# Where an option has a name of its own, both get that name in the language of Zammad. Trees whose values
# are names stay as they are. Titles lose surrounding spaces, so the title of the trigger
# without brand gives "Beamer".

module ManuelTreeSelectLabel
  TREE_TYPES = %w[tree_select multi_tree_select].freeze

  module_function

  # The translated name of a tree option, nil when the value is already its name or unknown
  def name(attribute, value, locale = nil)
    return if attribute.nil? || TREE_TYPES.exclude?(attribute.data_type) || !value.is_a?(String)

    named = names(attribute)[value]
    return if named.blank? || named == value

    Translation.translate(locale.presence || Setting.get('locale_default').presence || 'en-us', named)
  end

  def names(attribute)
    historical = attribute.data_option[:historical_options]
    return historical if historical.is_a?(Hash) && historical.present?

    flatten = ->(list) { Array(list).flat_map { |o| [[o['value'], o['name']], *flatten.(o['children'])] } }
    flatten.(attribute.data_option[:options]).to_h
  end

  module Placeholder
    private

    def display_value(object, method_name, previous_method_names, key)
      result = super
      return result if method_name != 'value' || result != key

      attribute = object_manager_attributes(object).where(name: previous_method_names.split('.').last).first
      ManuelTreeSelectLabel.name(attribute, key, @locale) || result
    end
  end

  module TitleStrip
    extend ActiveSupport::Concern

    included do
      before_save :manuel_strip_title, if: -> { title.present? && will_save_change_to_title? }
    end

    private

    def manuel_strip_title
      self.title = title.strip
    end
  end

  module AgentContext
    def prepare
      result = super
      return result if result.blank? || result[:label] != result[:value]

      name = ManuelTreeSelectLabel.name(object_attribute, result[:value])
      name ? result.merge(label: name) : result
    end
  end
end

Rails.application.config.to_prepare do
  {
    NotificationFactory::Renderer                                       => ManuelTreeSelectLabel::Placeholder,
    Service::AI::Agent::Run::Context::Entity::ObjectAttributes::Options => ManuelTreeSelectLabel::AgentContext,
  }.each { |klass, patch| klass.prepend(patch) if klass.ancestors.exclude?(patch) }
  Ticket.include(ManuelTreeSelectLabel::TitleStrip) if Ticket.ancestors.exclude?(ManuelTreeSelectLabel::TitleStrip)
end
