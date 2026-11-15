# Checks the device type set by the Ticket Categorizer with the decision model d3:9b, see
# docs/adr/0068-art-des-geraets-mit-d3-pruefen.adoc. Mounted as initializer by zammad/compose.yml,
# zammad/scheduler.rb adds a scheduler entry for ManuelCategoryCheck.run every five minutes.
#
# Zammad cannot use d3:9b as agent, it asks all agents over one chat connection. So this asks the service in
# category_check/ at MANUEL_CATEGORY_CHECK_URL. It sends the subject the guest wrote and the problem or
# the first message, never the title, which the title agent writes from the device type. The fields stay
# as they are. When d3:9b chooses another entry, is below 70 percent or a rule of ADR 11 asks back, an
# internal note asks the team to check. Every checked ticket gets the tag category-checked, a different
# choice also category-differs, the numbers for ADR 40. A new device type removes both, so it is checked again.

require 'net/http'

module ManuelCategoryCheck
  CHECKED = 'category-checked'.freeze
  DIFFERS = 'category-differs'.freeze
  GROUPS = ['Repairs', 'Repairs::Requests'].freeze
  MAX_AGE = 30.days
  NOTE_PREFIX = 'Prüfung der Art des Geräts mit d3:9b'.freeze
  REASONS = {
    'unsicher'       => 'd3:9b ist unter 70 Prozent sicher',
    'Sammelbegriff'  => 'der Eintrag ist ein Sammelbegriff, bei dem das Team die Bauart unterscheiden will',
    'Bauteil'        => 'der Eintrag ist ein Bauteil, das Gerät steht meist erst in der Nachricht',
    'Dienstleistung' => 'der Betreff nennt eine Dienstleistung statt eines Geräts',
  }.freeze

  module_function

  def url
    ENV['MANUEL_CATEGORY_CHECK_URL'].presence
  end

  def candidates
    Ticket.where(group: Group.where(name: GROUPS), created_at: MAX_AGE.ago..)
          .where.not(device_type: [nil, ''])
          .find_each.reject { |ticket| ticket.tag_list.include?(CHECKED) }
  end

  def plain(html)
    ActionController::Base.helpers.strip_tags(html.to_s).squish
  end

  def text_for(ticket)
    first = ticket.articles.order(:id).first
    subject = first&.subject.presence || ticket.title
    problem = ticket[:problem_reported].presence || plain(first&.body)
    [subject, problem].compact_blank.join('. ')[0, 2000]
  end

  def ask(text, subject)
    uri = URI(url)
    request = Net::HTTP::Post.new(uri, 'Content-Type' => 'application/json')
    request.body = { text: text, subject: subject }.to_json
    response = Net::HTTP.start(uri.host, uri.port, read_timeout: 300) { |http| http.request(request) }
    raise "category check answered #{response.code}" if !response.is_a?(Net::HTTPSuccess)

    JSON.parse(response.body)
  end

  def label(key)
    attribute = ObjectManager::Attribute.get(object: 'Ticket', name: 'device_type')
    name = Array(attribute&.data_option&.dig(:options)).find { |o| o['value'] == key }&.dig('name') || key
    Translation.translate(Setting.get('locale_default').presence || 'en-us', name)
  end

  def note(ticket, result)
    lines = ["Gesetzt ist #{label(ticket[:device_type])}. d3:9b wählt #{result['name']} mit #{(result['p'].to_f * 100).round} Prozent Sicherheit."]
    lines << "Rückfrage, weil #{REASONS.fetch(result['reason'], result['reason'])}." if result['reason']
    lines << 'Bitte die Art des Geräts prüfen und bei Bedarf ändern. Die Felder ändert MANUEL nicht.'
    Ticket::Article.create!(ticket_id: ticket.id, subject: NOTE_PREFIX, body: "#{NOTE_PREFIX}\n\n#{lines.join("\n")}",
                            content_type: 'text/plain', internal: true,
                            sender: Ticket::Article::Sender.find_by!(name: 'System'),
                            type: Ticket::Article::Type.find_by!(name: 'note'))
  end

  def run
    return if url.nil?

    UserInfo.current_user_id = 1
    candidates.each do |ticket|
      first = ticket.articles.order(:id).first
      result = ask(text_for(ticket), first&.subject.to_s)
      differs = result['key'] != ticket[:device_type]
      note(ticket, result) if differs || result['reason']
      ticket.tag_add(DIFFERS, 1) if differs
      ticket.tag_add(CHECKED, 1)
    rescue => e
      Rails.logger.error "ManuelCategoryCheck: ticket #{ticket.id} #{e.class} #{e.message}"
    end
    true
  end

  # A new device type, by a person or the categorizer, is checked again
  module Recheck
    extend ActiveSupport::Concern

    included do
      after_update :manuel_category_recheck, if: -> { has_attribute?(:device_type) && saved_change_to_attribute?(:device_type) }
    end

    private

    def manuel_category_recheck
      [CHECKED, DIFFERS].each { |tag| tag_remove(tag, 1) if tag_list.include?(tag) }
    end
  end
end

Rails.application.config.to_prepare do
  Ticket.include(ManuelCategoryCheck::Recheck) if Ticket.ancestors.exclude?(ManuelCategoryCheck::Recheck)
end
