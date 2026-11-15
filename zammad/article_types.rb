# The article type walk-in for guests who come to the reception without registering, see
# docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc. Mounted as initializer by zammad/compose.yml.
# The interface of Zammad only offers call and email when an agent creates a ticket, so the template for
# walk-ins creates an incoming call. Right after that the first article and the ticket get the type
# walk-in. The template is recognised by its text WALK_IN_MARKER.

module ManuelWalkIn
  TYPE = 'walk-in'.freeze
  WALK_IN_MARKER = %r{\A\s*(?:<[^>]+>\s*)*(am Empfang erfasst|recorded at the reception)}i

  extend ActiveSupport::Concern

  included do
    after_create :manuel_walk_in
  end

  private

  def manuel_walk_in
    return if type&.name != 'phone' || body.to_s !~ WALK_IN_MARKER
    return if Ticket::Article.where(ticket_id: ticket_id).where.not(id: id).exists?

    walk_in = Ticket::Article::Type.find_by(name: TYPE)
    return if walk_in.nil?

    update_columns(type_id: walk_in.id) # rubocop:disable Rails/SkipsModelValidations
    ticket.update_columns(create_article_type_id: walk_in.id) # rubocop:disable Rails/SkipsModelValidations
  end
end

Rails.application.config.to_prepare do
  Ticket::Article.include(ManuelWalkIn) if Ticket::Article.ancestors.exclude?(ManuelWalkIn)
end
