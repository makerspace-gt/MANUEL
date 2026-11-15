# Keeps the tags around the dates of a repair group up to date, see
# docs/adr/0062-datums-tags-und-monatsuebersichten-automatisch-pflegen.adoc. Mounted as initializer by
# zammad/compose.yml, zammad/setup.rb adds a scheduler entry that calls ManuelEventTags.run every hour.
#
# 1. A ticket with next-event whose appointment lay before today gets the date tag YYYY-MM-DD and loses
#    next-event. This replaces the macros that set the date and removed next-event by hand.
# 2. A ticket with next-event whose appointment moved more than 7 days ahead loses next-event.
# 3. An unconfirmed proposal (pending close) whose appointment lay before today counts as no-show, like
#    the macro "Not shown up": tag no-show, result No-show, closed.
# 4. The monthly overviews get the date tags of their month within the last 12 months, without tags
#    they are switched off, because an overview without condition would show every ticket.
# 5. Tags that no ticket uses are removed, except those named in rules or in KEEP_TAGS. Without
#    MANUEL_TAG_CLEANUP=apply this only writes to the log.

module ManuelEventTags
  GROUPS = ['Repairs', 'Repairs::Requests'].freeze
  NEXT_EVENT = 'next-event'.freeze
  DATE_TAG = %r{\A\d{4}-\d{2}-\d{2}\z}
  # Tags that stay selectable even without a ticket, in case tag_new is off
  KEEP_TAGS = %w[highlight next-event asked-again contact-check transcribed category-checked category-differs retitle spam
                 no-info info delete test obsolete no-show reminded statistics].freeze
  MONTHS = {
    'de' => %w[Januar Februar März April Mai Juni Juli August September Oktober November Dezember],
    'en' => %w[January February March April May June July August September October November December],
  }.freeze
  OVERVIEW_PREFIX = { 'de' => 'Gegenstände', 'en' => 'Items' }.freeze

  module_function

  def run
    UserInfo.current_user_id = 1
    Time.use_zone(Setting.get('timezone_default').presence || 'Europe/Berlin') do
      today = Time.zone.today
      tag_past_events(today)
      no_shows(today)
      update_month_overviews(today)
    end
    remove_unused_tags
    true
  end

  def group_ids
    Group.where(name: GROUPS).pluck(:id)
  end

  def tickets_with(tag)
    ids = Tag.tag_references(tag: tag, object: 'Ticket').map(&:last)
    Ticket.where(id: ids, group_id: group_ids)
  end

  def tag_past_events(today)
    tickets_with(NEXT_EVENT).find_each do |ticket|
      next if ticket.pending_time.nil?

      day = ticket.pending_time.in_time_zone.to_date
      if day < today
        ticket.tag_add(day.iso8601, 1)
        ticket.tag_remove(NEXT_EVENT, 1)
      elsif day > today + 7
        ticket.tag_remove(NEXT_EVENT, 1)
      end
    end
  end

  def no_shows(today)
    state = Ticket::State.find_by(name: 'pending close')
    closed = Ticket::State.find_by(name: 'closed')
    return if state.nil? || closed.nil?

    Ticket.where(state_id: state.id, group_id: group_ids).where(pending_time: ...today.beginning_of_day).find_each do |ticket|
      ticket.tag_add('no-show', 1)
      changes = { state_id: closed.id }
      changes[:repair_result] = 'No-show' if Ticket.column_names.include?('repair_result')
      ticket.update!(changes)
    end
  end

  def language
    Setting.get('locale_default').to_s.start_with?('de') ? 'de' : 'en'
  end

  def month_overview_names
    MONTHS[language].map { |month| "#{OVERVIEW_PREFIX[language]} #{month}" }
  end

  def update_month_overviews(today)
    dates = Tag::Item.pluck(:name).grep(DATE_TAG)
    month_overview_names.each_with_index do |name, index|
      overview = Overview.find_by(name: name)
      next if overview.nil?

      # The latest occurrence of this month within the last 12 months
      year = index + 1 > today.month ? today.year - 1 : today.year
      prefix = format('%<year>04d-%<month>02d-', year: year, month: index + 1)
      tags = dates.select { |tag| tag.start_with?(prefix) }.sort
      if tags.empty?
        overview.update!(active: false) if overview.active
        next
      end
      condition = { 'ticket.tags' => { 'operator' => 'contains one', 'value' => tags.join(', ') } }
      next if overview.active && overview.condition == condition

      overview.update!(condition: condition, active: true)
    end
  end

  def tags_in_rules
    texts = [Overview, Trigger, Job, Macro, CoreWorkflow, PostmasterFilter].flat_map do |model|
      model.all.map { |record| record.attributes.slice('condition', 'perform', 'match', 'condition_saved', 'condition_selected').to_json }
    end
    texts.join("\n")
  end

  def remove_unused_tags
    used = Tag.distinct.pluck(:tag_item_id)
    rules = tags_in_rules
    candidates = Tag::Item.where.not(id: used).reject do |item|
      KEEP_TAGS.include?(item.name) || rules.include?("\"#{item.name}\"") || rules.match?(%r{[", ]#{Regexp.escape(item.name)}[",]})
    end
    return if candidates.empty?

    if ENV['MANUEL_TAG_CLEANUP'] == 'apply'
      candidates.each { |item| Tag::Item.remove(item.id) }
      Rails.logger.info "ManuelEventTags: removed unused tags #{candidates.map(&:name).join(', ')}"
    else
      Rails.logger.info "ManuelEventTags: would remove unused tags #{candidates.map(&:name).join(', ')}"
    end
  end
end
