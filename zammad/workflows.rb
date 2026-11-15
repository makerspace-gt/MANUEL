# Triggers and scheduled jobs of the Repair Café, loaded by zammad/setup.rb, see
# docs/adr/0060-ablaeufe-des-bestehenden-zammad-als-code-uebernehmen.adoc.
#
# Rules that only work inside Zammad, like the tag next-event or moving scheduled requests to Repairs,
# are active from the start. Rules that write to guests or delete tickets are created inactive, the team
# switches them on. A later run updates conditions, actions and texts but never changes active. Rules
# of an older Zammad get our names from LEGACY_NAMES in zammad/migrate_fields.rb before, so nothing is
# created twice and their active state stays.
#
# Texts for guests come from zammad/texts/*.de.md, plain paragraphs and lists with "- ". The signature
# is zammad/texts/signature.de.html, because trigger mails carry no group signature.

WORKFLOW_TEXTS = File.join(__dir__, 'texts')

# Names of the same rules in the Zammad of Makerspace Gütersloh before MANUEL. They are renamed before
# anything is created, active stays. Other initiatives add their own names here.
LEGACY_NAMES = {
  Trigger => {
    'tag date'                                                    => 'Repairs: Tag next-event',
    'remove next-event due abgelehnt'                             => 'Repairs: Remove next-event when obsolete',
    'Verschieben terminierter RepairCafé-Anfragen zu RepairCafé'  => 'Repairs: Move scheduled requests',
    'Verpasste Anrufe ignorieren'                                 => 'Repairs: Ignore missed calls',
    'Voicemail ohne Nachricht ignorieren'                         => 'Repairs: Ignore voicemail without message',
    'Automatische Antwort bei neuen Repair Café Tickets'          => 'Repairs: Auto reply',
    'Statistik'                                                   => 'Repairs: Statistics ticket',
  },
  Job     => {
    'Tag Date'                                                                => 'Repairs: Tag next-event',
    'reminded Tag entfernen'                                                  => 'Repairs: Remove reminded',
    'Automatisch ablehnen, wenn keinen Terminbestätigung erfolgt'             => 'Repairs: Cancel unconfirmed proposal',
    'Automatisch erinnern, wenndie Terminvereinbarung schon länger her ist'  => 'Repairs: Remind of appointment',
    'Delete spam'                                                             => 'Repairs: Delete spam',
    'Delete no-info'                                                          => 'Repairs: Delete no-info',
    'Delete test'                                                             => 'Repairs: Delete test',
    'Delete delete'                                                           => 'Repairs: Delete tagged delete',
    'Delete Repair Café Anfragen'                                             => 'Repairs: Delete closed requests',
    'Delete Repair Café'                                                      => 'Repairs: Delete closed repairs',
    'Delete merged'                                                           => 'Repairs: Delete merged',
  },
}.freeze

LEGACY_NAMES.each do |model, names|
  names.each do |old_name, new_name|
    record = model.find_by(name: old_name)
    next if record.nil? || model.exists?(name: new_name)

    record.update!(name: new_name, updated_by_id: 1)
    puts "Übernommen: #{model.name} #{old_name} heißt jetzt #{new_name}, aktiv #{record.active}"
  end
end

def workflow_group_ids(*names)
  names.map { |name| Group.find_by!(name: name).id.to_s }
end

def workflow_state_ids(*names)
  names.map { |name| Ticket::State.find_by!(name: name).id.to_s }
end

# Paragraphs, lines starting with "- " become a list, %{key} is replaced by HTML from values
def workflow_html(text, values = {})
  text.strip.split(%r{\n{2,}}).filter_map do |block|
    key = block.strip[%r{\A%\{(\w+)\}\z}, 1]
    next values[key.to_sym].presence if key

    lines = block.split("\n")
    if lines.all? { |line| line.start_with?('- ') }
      "<ul>#{lines.map { |line| "<li>#{CGI.escapeHTML(line.delete_prefix('- ').strip)}</li>" }.join}</ul>"
    else
      "<p>#{lines.map { |line| CGI.escapeHTML(line.strip) }.join('<br>')}</p>"
    end
  end.join
end

def workflow_mail(file, values = {})
  body = workflow_html(File.read(File.join(WORKFLOW_TEXTS, file), encoding: 'utf-8'), values)
  signature = File.read(File.join(WORKFLOW_TEXTS, 'signature.de.html'), encoding: 'utf-8')
  { 'recipient' => ['ticket_customer'], 'subject' => '#{ticket.title}', 'internal' => 'false', # rubocop:disable Lint/InterpolationCheck
    'include_attachments' => 'false', 'body' => "#{body}<br>#{signature}" }
end

# Every day at the given hours, or on the given weekdays only
def workflow_timeplan(hours, days: %w[Mon Tue Wed Thu Fri Sat Sun])
  {
    'days'    => %w[Mon Tue Wed Thu Fri Sat Sun].index_with { |day| days.include?(day) },
    'hours'   => (0..23).to_h { |hour| [hour.to_s, hours.include?(hour)] },
    'minutes' => (0..50).step(10).to_h { |minute| [minute.to_s, minute.zero?] },
  }
end

# Creates or updates one rule, active only when it is created
def workflow_rule(model, name, german, active:, **attributes)
  record = model.find_or_initialize_by(name: tr(name, german))
  record.assign_attributes(attributes)
  record.active = active if record.new_record?
  record.created_by_id ||= 1
  record.updated_by_id = 1
  record.save! if record.new_record? || record.changed?
  record
end

repair_groups = workflow_group_ids('Repairs', 'Repairs::Requests')
requests = workflow_group_ids('Repairs::Requests')
scheduled = workflow_state_ids('pending reminder')
proposed = workflow_state_ids('pending close')
closed = Ticket::State.find_by!(name: 'closed').id.to_s
with_email = { 'customer.email' => { 'operator' => 'contains', 'value' => '@' } }
trigger_defaults = { activator: 'action', execution_condition_mode: 'selective' }

# 1. Rules inside Zammad, active. Triggers run in the order of their names, so Tag next-event runs
# after Remove next-event and must leave out obsolete tickets itself.

workflow_rule(Trigger, 'Repairs: Tag next-event', 'Repairs: next-event setzen', active: true, **trigger_defaults,
              execution_condition_mode: 'always',
              condition: { 'ticket.pending_time' => { 'operator' => 'till (relative)', 'value' => '7', 'range' => 'day' },
                           'ticket.group_id' => { 'operator' => 'is', 'value' => repair_groups },
                           'ticket.state_id' => { 'operator' => 'is', 'value' => scheduled },
                           'ticket.tags' => { 'operator' => 'contains one not', 'value' => 'obsolete' } },
              perform:   { 'ticket.tags' => { 'operator' => 'add', 'value' => 'next-event' } },
              note:      'Marks devices of the next Repair Café, ADR 62')

workflow_rule(Job, 'Repairs: Tag next-event', 'Repairs: next-event setzen', active: true, object: 'Ticket',
              timeplan:  workflow_timeplan([5]),
              condition: { 'ticket.pending_time' => { 'operator' => 'till (relative)', 'value' => '7', 'range' => 'day' },
                           'ticket.group_id' => { 'operator' => 'is', 'value' => repair_groups },
                           'ticket.state_id' => { 'operator' => 'is', 'value' => scheduled },
                           'ticket.tags' => { 'operator' => 'contains one not', 'value' => 'obsolete' } },
              perform:   { 'ticket.tags' => { 'operator' => 'add', 'value' => 'next-event' } },
              note:      'Same as the trigger, for tickets that did not change in the last week, ADR 62')

workflow_rule(Trigger, 'Repairs: Remove next-event when obsolete', 'Repairs: next-event bei obsolete entfernen', active: true,
              **trigger_defaults, execution_condition_mode: 'always',
              condition: { 'ticket.tags' => { 'operator' => 'contains one', 'value' => 'obsolete' } },
              perform:   { 'ticket.tags' => { 'operator' => 'remove', 'value' => 'next-event' } })

workflow_rule(Trigger, 'Repairs: Move scheduled requests', 'Repairs: Terminierte Anfragen verschieben', active: true, **trigger_defaults,
              condition: { 'ticket.state_id' => { 'operator' => 'is', 'value' => scheduled },
                           'ticket.group_id' => { 'operator' => 'is', 'value' => requests } },
              perform:   { 'ticket.group_id' => { 'value' => workflow_group_ids('Repairs').first } })

workflow_rule(Trigger, 'Repairs: Remove asked-again', 'Repairs: asked-again entfernen', active: true, **trigger_defaults,
              execution_condition_mode: 'always',
              condition: { 'ticket.tags' => { 'operator' => 'contains one', 'value' => 'asked-again' },
                           'ticket.state_id' => { 'operator' => 'is not', 'value' => proposed } },
              perform:   { 'ticket.tags' => { 'operator' => 'remove', 'value' => 'asked-again' } },
              note:      'The guest answered or the proposal ended, ADR 60')

workflow_rule(Job, 'Repairs: Remove reminded', 'Repairs: reminded entfernen', active: true, object: 'Ticket',
              timeplan:  workflow_timeplan([5], days: %w[Tue]),
              condition: { 'operator' => 'AND', 'conditions' => [
                { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => workflow_group_ids('Repairs') },
                { 'name' => 'ticket.tags', 'operator' => 'contains one', 'value' => 'reminded' },
                { 'operator' => 'OR', 'conditions' => [
                  { 'name' => 'ticket.state_id', 'operator' => 'is', 'value' => [closed] },
                  { 'name' => 'ticket.pending_time', 'operator' => 'before (relative)', 'range' => 'day', 'value' => '2' },
                  { 'name' => 'ticket.pending_time', 'operator' => 'after (relative)', 'range' => 'day', 'value' => '7' },
                ] },
              ] },
              perform:   { 'ticket.tags' => { 'operator' => 'remove', 'value' => 'reminded' } })

# Title from brand and device once a ticket is in Repairs, see docs/adr/0067-betreff-aus-marke-und-art-schreiben.adoc.
# zammad/tree_select_label.rb makes the placeholder give the German name instead of the key. Confirming
# moves a request to Repairs in another trigger of the same run, has changed only sees the state. The
# macro sets the tag retitle, so the title can be rebuilt by hand. The title itself comes from the trigger on
# the server, the classic interface would fill a macro title in the browser, where the names are missing.
# always, because a new tag is no changed attribute and selective would ignore the macro
workflow_rule(Trigger, 'Repairs: Title from brand and device', 'Repairs: Betreff aus Marke und Gerät', active: true, **trigger_defaults,
              execution_condition_mode: 'always',
              condition: { 'operator' => 'AND', 'conditions' => [
                { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => workflow_group_ids('Repairs') },
                { 'name' => 'ticket.device_type', 'operator' => 'matches regex', 'value' => '.' },
                { 'name' => 'ticket.tags', 'operator' => 'contains one not', 'value' => 'spam, no-info, obsolete, delete' },
                { 'operator' => 'OR', 'conditions' => [
                  { 'name' => 'ticket.action', 'operator' => 'is', 'value' => 'create' },
                  { 'operator' => 'AND', 'conditions' => [
                    { 'name' => 'ticket.state_id', 'operator' => 'has changed', 'value' => [] },
                    { 'name' => 'ticket.state_id', 'operator' => 'is', 'value' => scheduled },
                  ] },
                  { 'name' => 'ticket.device_type', 'operator' => 'has changed', 'value' => [] },
                  { 'name' => 'ticket.brand', 'operator' => 'has changed', 'value' => [] },
                  { 'name' => 'ticket.tags', 'operator' => 'contains one', 'value' => 'retitle' },
                ] },
              ] },
              perform:   { 'ticket.title' => { 'value' => '#{ticket.brand} #{ticket.device_type.value}' }, # rubocop:disable Lint/InterpolationCheck
                           'ticket.tags' => { 'operator' => 'remove', 'value' => 'retitle' } },
              note:      'Title as brand and device, ADR 67')

macro = Macro.find_or_initialize_by(name: tr('Title from brand and device', 'Betreff aus Marke und Gerät'))
# The classic interface adds tags through their own API without changing the ticket, so the macro also sets
# a plain title. That change starts the triggers, the placeholder title is replaced right away.
macro.assign_attributes(perform: { 'ticket.tags' => { 'operator' => 'add', 'value' => 'retitle' },
                                   'ticket.title' => { 'value' => 'Betreff wird gesetzt' } }, ux_flow_next_up: 'none',
                        note: 'Rebuilds the title through the trigger Repairs: Title from brand and device, ADR 67')
macro.active = true if macro.new_record?
macro.created_by_id ||= 1
macro.updated_by_id = 1
macro.save! if macro.new_record? || macro.changed?

# Calls without message, from sipgate. Voicemails get a transcript from zammad/voicemail.rb, ADR 64
workflow_rule(Trigger, 'Repairs: Ignore missed calls', 'Repairs: Verpasste Anrufe ignorieren', active: true, **trigger_defaults,
              condition: { 'ticket.title' => { 'operator' => 'contains', 'value' => 'Verpasster Anruf:' },
                           'ticket.action' => { 'operator' => 'is', 'value' => 'create' } },
              perform:   { 'ticket.state_id' => { 'value' => closed }, 'ticket.tags' => { 'operator' => 'add', 'value' => 'no-info' } })

workflow_rule(Trigger, 'Repairs: Ignore voicemail without message', 'Repairs: Voicemail ohne Nachricht ignorieren', active: true,
              **trigger_defaults,
              condition: { 'ticket.title' => { 'operator' => 'contains', 'value' => 'Neue Voicemail von' },
                           'article.body' => { 'operator' => 'contains not', 'value' => 'Folgende Nachricht wurde hinterlassen' },
                           'ticket.action' => { 'operator' => 'is', 'value' => 'create' } },
              perform:   { 'ticket.state_id' => { 'value' => closed }, 'ticket.tags' => { 'operator' => 'add', 'value' => 'no-info' } },
              note:      'Relies on the transcript of sipgate, replaced by zammad/voicemail.rb after the test of ADR 64')

# 2. Mails to guests, inactive until the team switches them on

kb_answer = KnowledgeBase::Answer::Translation.find_by(title: 'Hausordnung')&.answer
links = if kb_answer&.can_be_published_aasm&.current_state == :published && kb_answer.category.knowledge_base.active
          kb_answer.translations.map { |t| "<a href=\"#{CGI.escapeHTML(t.public_url)}\">#{CGI.escapeHTML(t.title)}</a>" }
        end
house_rules = {
  house_rules:      workflow_html(File.read(File.join(WORKFLOW_TEXTS, 'house_rules.de.md'), encoding: 'utf-8')),
  house_rules_link: links && "<p>Die Hausordnung steht auch online unter #{links.join(' und ')}.</p>",
}

# Senders that never get the auto reply, like the event platform or sipgate. Exceptions set by hand stay.
auto_reply = Trigger.find_by(name: 'Repairs: Auto reply')
except = Array(auto_reply&.condition&.dig('ticket.customer_id', 'value'))
except |= ENV.fetch('MANUEL_AUTO_REPLY_EXCEPT', '').split(',').filter_map { |email| User.find_by(email: email.strip.downcase)&.id&.to_s }
except |= [ENV['MANUEL_EVENT_REMINDER_FROM']].compact.filter_map { |email| User.find_by(email: email.downcase)&.id&.to_s }
condition = { 'ticket.action' => { 'operator' => 'is', 'value' => 'create' },
              'article.sender_id' => { 'operator' => 'is', 'value' => [Ticket::Article::Sender.find_by!(name: 'Customer').id.to_s] },
              'ticket.group_id' => { 'operator' => 'is', 'value' => requests },
              'article.type_id' => { 'operator' => 'is', 'value' => Ticket::Article::Type.where(name: %w[email web]).ids.map(&:to_s) } }
condition['ticket.customer_id'] = { 'operator' => 'is not', 'pre_condition' => 'specific', 'value' => except } if except.any?
workflow_rule(Trigger, 'Repairs: Auto reply', 'Repairs: Eingangsbestätigung', active: false, **trigger_defaults,
              condition: condition,
              perform:   { 'notification.email' => workflow_mail('auto_reply.de.md', house_rules) },
              note:      'Confirms new requests by mail or contact form and sends the house rules, ADR 60')

proposal = { 'ticket.state_id' => { 'operator' => 'is', 'value' => proposed },
             'ticket.group_id' => { 'operator' => 'is', 'value' => repair_groups } }.merge(with_email)
cancel = Job.find_by(name: 'Repairs: Cancel unconfirmed proposal')
# The follow-ups belong to the cancellation, they start in the same state, so an active cancellation
# taken over from an older Zammad never waits for a follow-up that is off
follow_up_active = cancel&.active || false

workflow_rule(Job, 'Repairs: Follow up proposal', 'Repairs: Terminvorschlag nachfragen', active: follow_up_active, object: 'Ticket',
              timeplan:  workflow_timeplan([8, 15]),
              condition: proposal.merge(
                'ticket.tags' => { 'operator' => 'contains one not', 'value' => 'asked-again' },
                'ticket.last_contact_at' => { 'operator' => 'before (relative)', 'value' => '2', 'range' => 'day' },
                'ticket.pending_time' => { 'operator' => 'within next (relative)', 'value' => '9', 'range' => 'day' },
              ),
              perform:   { 'notification.email' => workflow_mail('proposal_follow_up.de.md'),
                           'ticket.tags' => { 'operator' => 'add', 'value' => 'asked-again' } },
              note:      'Asks once before the proposal is cancelled, ADR 60')

workflow_rule(Job, 'Repairs: Follow up proposal shortly before', 'Repairs: Terminvorschlag kurz vorher nachfragen', active: follow_up_active,
              object: 'Ticket', timeplan: workflow_timeplan([8, 15]),
              condition: proposal.merge(
                'ticket.tags' => { 'operator' => 'contains one not', 'value' => 'asked-again' },
                'ticket.last_contact_at' => { 'operator' => 'before (relative)', 'value' => '28', 'range' => 'hour' },
                'ticket.pending_time' => { 'operator' => 'within next (relative)', 'value' => '23', 'range' => 'hour' },
              ),
              perform:   { 'notification.email' => workflow_mail('proposal_follow_up_short.de.md'),
                           'ticket.tags' => { 'operator' => 'add', 'value' => 'asked-again' } },
              note:      'Only asks, a proposal still open after the date becomes no-show at night, zammad/event_tags.rb')

workflow_rule(Job, 'Repairs: Cancel unconfirmed proposal', 'Repairs: Unbestätigten Terminvorschlag absagen', active: false, object: 'Ticket',
              timeplan:  workflow_timeplan([8, 15]),
              condition: proposal.merge(
                'ticket.tags' => { 'operator' => 'contains one', 'value' => 'asked-again' },
                'ticket.last_contact_at' => { 'operator' => 'before (relative)', 'value' => '4', 'range' => 'day' },
                'ticket.pending_time' => { 'operator' => 'within next (relative)', 'value' => '7', 'range' => 'day' },
              ),
              perform:   { 'notification.email' => workflow_mail('proposal_cancel.de.md'),
                           'ticket.state_id' => { 'value' => closed },
                           'ticket.tags' => { 'operator' => 'add', 'value' => 'obsolete' } },
              note:      'Frees the slot after the follow-up, ADR 60')

workflow_rule(Job, 'Repairs: Remind of appointment', 'Repairs: An Termin erinnern', active: false, object: 'Ticket',
              timeplan:  workflow_timeplan([8, 15]),
              condition: { 'ticket.group_id' => { 'operator' => 'is', 'value' => workflow_group_ids('Repairs') },
                           'ticket.state_id' => { 'operator' => 'is', 'value' => scheduled },
                           'ticket.last_contact_at' => { 'operator' => 'before (relative)', 'value' => '11', 'range' => 'day' },
                           'ticket.pending_time' => { 'operator' => 'within next (relative)', 'value' => '3', 'range' => 'day' },
                           'ticket.tags' => { 'operator' => 'contains one not', 'value' => 'reminded' } }.merge(with_email),
              perform:   { 'notification.email' => workflow_mail('appointment_reminder.de.md'),
                           'ticket.tags' => { 'operator' => 'add', 'value' => 'reminded' } })

# One ticket per Repair Café for the statistics, from the reminder mail of the event platform, like the
# press release of zammad/press.rb. It lands in Repairs::Events, so next-event and the monthly overviews
# leave it out. Without MANUEL_EVENT_REMINDER_FROM nothing is created.
if ENV['MANUEL_EVENT_REMINDER_FROM'].present?
  links = { ENV['MANUEL_STATISTICS_SHEET_URL'] => 'Tabelle der Statistik', ENV['MANUEL_FORUM_URL'] => 'Forum' }
          .select { |url, _| url.present? }.map { |url, label| "<a href=\"#{CGI.escapeHTML(url)}\">#{label}</a>" }
  perform = {
    'ticket.title'        => { 'value' => Setting.get('locale_default').to_s.start_with?('de') ? 'Statistik' : 'Statistics' },
    'ticket.group_id'     => { 'value' => workflow_group_ids('Repairs::Events').first },
    'ticket.state_id'     => { 'value' => scheduled.first },
    'ticket.pending_time' => { 'operator' => 'relative', 'value' => '7', 'range' => 'day' },
    'article.note'        => { 'subject' => 'Statistik', 'internal' => 'true',
                               'body' => workflow_html(File.read(File.join(WORKFLOW_TEXTS, 'statistics_note.de.md'), encoding: 'utf-8'),
                                                       links: links.any? ? "<p>#{links.join('<br>')}</p>" : nil) },
  }
  customer = User.find_by(login: ENV['MANUEL_STATISTICS_CUSTOMER'].to_s.downcase) if ENV['MANUEL_STATISTICS_CUSTOMER'].present?
  perform['ticket.customer_id'] = { 'pre_condition' => 'specific', 'value' => customer.id.to_s } if customer
  workflow_rule(Trigger, 'Repairs: Statistics ticket', 'Repairs: Statistik-Ticket', active: false, **trigger_defaults,
                condition: { 'ticket.action' => { 'operator' => 'is', 'value' => 'create' },
                             'ticket.title' => { 'operator' => 'contains', 'value' => ENV['MANUEL_EVENT_REMINDER_SUBJECT'].presence || 'nächste Woche:' },
                             'article.from' => { 'operator' => 'contains', 'value' => ENV['MANUEL_EVENT_REMINDER_FROM'] } },
                perform:   perform,
                note:      'Statistics ticket for one Repair Café in Repairs::Events, ADR 60')
end

# 3. Deletion periods, inactive until the team switches them on, see chapter 11 of the case study

close_before = ->(value, range) { { 'name' => 'ticket.close_at', 'operator' => 'before (relative)', 'range' => range, 'value' => value.to_s } }
tagged = ->(tag) { { 'name' => 'ticket.tags', 'operator' => 'contains all', 'value' => tag } }
in_groups = ->(*names) { { 'name' => 'ticket.group_id', 'operator' => 'is', 'value' => workflow_group_ids(*names) } }

DELETIONS = {
  'Repairs: Delete spam'            => ['Repairs: Spam löschen', [tagged.('spam'), close_before.(1, 'month')]],
  'Repairs: Delete no-info'         => ['Repairs: no-info löschen', [tagged.('no-info'), close_before.(1, 'month')]],
  'Repairs: Delete test'            => ['Repairs: test löschen', [tagged.('test'), close_before.(1, 'month')]],
  # Tickets with the tag info are kept even when tagged delete
  'Repairs: Delete tagged delete'   => ['Repairs: delete löschen', [tagged.('delete'), close_before.(1, 'month'),
                                                                    { 'name' => 'ticket.tags', 'operator' => 'contains all not', 'value' => 'info' }]],
  'Repairs: Delete closed requests' => ['Repairs: Geschlossene Anfragen löschen', [in_groups.('Repairs::Requests'), close_before.(3, 'month')]],
  'Repairs: Delete closed repairs'  => ['Repairs: Geschlossene Reparaturen löschen', [in_groups.('Repairs', 'Repairs::Events'), close_before.(3, 'year')]],
  'Repairs: Delete merged'          => ['Repairs: Zusammengeführte löschen',
                                        [{ 'name' => 'ticket.state_id', 'operator' => 'is', 'value' => workflow_state_ids('merged') }]],
}.freeze

DELETIONS.each do |name, (german, conditions)|
  workflow_rule(Job, name, german, active: false, object: 'Ticket', timeplan: workflow_timeplan([2], days: %w[Mon]),
                condition: { 'operator' => 'AND', 'conditions' => conditions }, perform: { 'ticket.action' => { 'value' => 'delete' } })
end

ours = Trigger.where('name LIKE ?', 'Repairs: %').to_a + Job.where('name LIKE ?', 'Repairs: %').to_a
puts "Abläufe: #{ours.size} Regeln, aktiv #{ours.select(&:active).map(&:name).join(', ')}"
