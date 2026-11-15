# Brings existing guests and tickets in line with zammad/contact_filter.rb, see
# docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc. Runs with rails runner after the filter
# file, which it loads:
#   rails runner zammad/migrate_contacts.rb           shows what would change
#   MANUEL_MIGRATE=apply rails runner zammad/migrate_contacts.rb
#
# 1. Phone and mobile of all guests get the format +49 5241 1234567, numbers it cannot read are listed.
# 2. Tickets whose guest is sipgate get the guest with the caller's number, several matches are listed.
# 3. First articles get their way in: phone for sipgate, web for the contact form, walk-in for texts of
#    the reception. Articles are changed without callbacks, so no trigger fires.

load File.join(__dir__, 'contact_filter.rb') unless defined?(ManuelContact)

APPLY = ENV['MANUEL_MIGRATE'] == 'apply'
# Texts the reception used for walk-ins, as in eval/decision/real4.py
WALK_IN = %r{\A\s*(kam spontan vorbei|wurde spontan mitgebracht|am Empfang erfasst|handschriftliche notiz ins zammad übertragen)}i

UserInfo.current_user_id = 1
counts = Hash.new(0)
open_items = []

customer_role = Role.find_by(name: 'Customer')
User.joins(:roles).where(roles: { id: customer_role&.id }).where("phone <> '' OR mobile <> ''").find_each do |user|
  changes = {}
  %i[phone mobile].each do |field|
    next if user[field].blank?

    formatted, = ManuelContact.format(user[field])
    if formatted.nil?
      open_items << "Gast #{user.id}: Nummer im Feld #{field} nicht erkannt"
    elsif formatted != user[field]
      changes[field] = formatted
    end
  end
  next if changes.empty?

  counts['Nummern'] += changes.size
  user.update!(changes) if APPLY
end

types = Ticket::Article::Type.where(name: %w[phone web walk-in]).index_by(&:name)
sipgate_users = User.where('email ILIKE ?', '%sipgate%').pluck(:id)

Ticket.where(customer_id: sipgate_users).find_each do |ticket|
  article = ticket.articles.order(:id).first
  next if article.nil?

  if article.type_id != types['phone']&.id
    counts['Anruf'] += 1
    if APPLY
      article.update_columns(type_id: types['phone'].id) # rubocop:disable Rails/SkipsModelValidations
      ticket.update_columns(create_article_type_id: types['phone'].id) # rubocop:disable Rails/SkipsModelValidations
    end
  end
  raw = ManuelContact.text({ body: article.body, content_type: article.content_type })[ManuelContact::SIPGATE_CALLER, 1]
  digits = raw && Cti::CallerId.normalize_number(raw)
  next if digits.blank?

  ids = Cti::CallerId.where(caller_id: digits, level: 'known', object: 'User').where.not(user_id: sipgate_users).distinct.pluck(:user_id)
  case ids.size
  when 1
    counts['Gast zugeordnet'] += 1
    ticket.update_columns(customer_id: ids.first) if APPLY # rubocop:disable Rails/SkipsModelValidations
  when 0
    counts['Gast fehlt noch'] += 1
  else
    open_items << "Ticket #{ticket.number}: Nummer passt zu #{ids.size} Gästen"
  end
end

Ticket::Article.where(id: Ticket::Article.group(:ticket_id).select('MIN(id)')).find_each do |article|
  target = if article.subject.to_s.match?(ManuelContact::FORM_SUBJECT) && article.body.to_s.match?(ManuelContact::FORM_EMAIL)
             'web'
           elsif article.body.to_s.match?(WALK_IN)
             'walk-in'
           end
  next if target.nil? || types[target].nil? || article.type_id == types[target].id

  counts[target] += 1
  next if !APPLY

  article.update_columns(type_id: types[target].id) # rubocop:disable Rails/SkipsModelValidations
  Ticket.where(id: article.ticket_id).update_all(create_article_type_id: types[target].id) # rubocop:disable Rails/SkipsModelValidations
end

puts "#{APPLY ? 'Geändert' : 'Würde ändern (Probelauf, MANUEL_MIGRATE=apply zum Ausführen)'}: #{counts.map { |k, v| "#{k} #{v}" }.join(', ').presence || 'nichts'}"
puts "Offen: #{open_items.size}"
open_items.first(50).each { |line| puts "  #{line}" }
