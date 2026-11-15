# Press release and social media note before each Repair Café, loaded by zammad/setup.rb, see
# docs/adr/0066-pressemitteilung-und-beitraege-aus-vorlagen.adoc.
#
# The reminder mail of the event platform, sender MANUEL_EVENT_REMINDER_FROM and a subject containing
# MANUEL_EVENT_REMINDER_SUBJECT, starts all of it. Every active user of the organization Presse gets a
# trigger of their own, because Zammad sends trigger mails only to users and several recipients would
# share one mail. The text comes verbatim from zammad/texts/press_release.de.html, the medium in the
# salutation is the part of the trigger name after the prefix.
#
# New press triggers are inactive, a later run never changes active. Triggers of users who left the
# organization are switched off. No addresses are in the repo, the team keeps them in Zammad.

PRESS_ORGANIZATION = 'Presse'.freeze
PRESS_PREFIX = 'Press release: '.freeze
PRESS_SUBJECT = 'Pressemitteilung Repair Café'.freeze
SOCIAL_TRIGGER = 'Repairs: Social media announcement'.freeze

press = Organization.find_or_create_by!(name: PRESS_ORGANIZATION) do |organization|
  organization.note = 'Editorial offices that get the press release before each Repair Café, see MANUEL'
  organization.created_by_id = 1
  organization.updated_by_id = 1
end

reminder_from = ENV['MANUEL_EVENT_REMINDER_FROM'].presence
reminder_subject = ENV['MANUEL_EVENT_REMINDER_SUBJECT'].presence || 'nächste Woche:'

def press_condition(from, subject)
  {
    'ticket.action' => { 'operator' => 'is', 'value' => 'create' },
    'ticket.title'  => { 'operator' => 'contains', 'value' => subject },
    'article.from'  => { 'operator' => 'contains', 'value' => from },
  }
end

def press_text(file)
  File.read(File.join(__dir__, 'texts', file), encoding: 'utf-8')
end

# Plain text of a template as HTML for an article
def press_html(text)
  text.split(%r{\n{2,}}).map { |part| "<p>#{CGI.escapeHTML(part.strip).gsub("\n", '<br>')}</p>" }.join
end

def press_save(trigger, attributes)
  trigger.assign_attributes(attributes.except(:active))
  trigger.active = attributes.fetch(:active, false) if trigger.new_record?
  trigger.created_by_id ||= 1
  trigger.updated_by_id = 1
  trigger.save! if trigger.new_record? || trigger.changed?
end

if reminder_from
  condition = press_condition(reminder_from, reminder_subject)
  members = User.where(active: true).find_each.select { |user| user.all_organization_ids.include?(press.id) }
  recipient = ->(trigger) { trigger.perform.dig('notification.email', 'recipient') }
  existing = Trigger.where('name LIKE ?', "#{PRESS_PREFIX}%").to_a

  members.each do |user|
    trigger = existing.find { |t| recipient.(t) == ["userid_#{user.id}"] } || Trigger.new(name: "#{PRESS_PREFIX}#{user.fullname}")
    medium = trigger.name.delete_prefix(PRESS_PREFIX)
    press_save(trigger, {
                 condition:   condition,
                 perform:     { 'notification.email' => {
                   'recipient' => ["userid_#{user.id}"], 'subject' => PRESS_SUBJECT, 'internal' => 'false',
                   'include_attachments' => 'false', 'body' => press_text('press_release.de.html').gsub('%{medium}', CGI.escapeHTML(medium))
                 } },
                 activator:   'action',
                 execution_condition_mode: 'selective',
                 note:        "Press release to #{medium}, text from zammad/texts/press_release.de.html",
               })
  end

  member_ids = members.map { |user| "userid_#{user.id}" }
  existing.each do |trigger|
    next if !trigger.active || (recipient.(trigger) & member_ids).any?

    trigger.update!(active: false, updated_by_id: 1)
  end

  # Ready texts for Mastodon and Instagram as internal note, posting stays with a human (ADR 33)
  press_save(Trigger.find_or_initialize_by(name: SOCIAL_TRIGGER), {
               condition: condition,
               perform:   { 'article.note' => { 'subject' => 'Social media', 'internal' => 'true',
                                                'body' => press_html(press_text('social_announcement.de.md')) } },
               activator: 'action',
               execution_condition_mode: 'selective',
               note:      'Texts for social media before the Repair Café, from zammad/texts/social_announcement.de.md',
               active:    true,
             })
end

press_triggers = Trigger.where('name LIKE ?', "#{PRESS_PREFIX}%")
puts "Presse: #{press_triggers.count} Trigger, davon #{press_triggers.where(active: true).count} aktiv" \
     "#{reminder_from ? '' : ', ohne MANUEL_EVENT_REMINDER_FROM keine Trigger'}"
