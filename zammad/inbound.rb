# Article type walk-in and the pre filter for contact data, loaded by zammad/setup.rb, see
# docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc. The filter is only registered when its
# class is loaded, see zammad/compose.yml.

Ticket::Article::Type.find_or_create_by!(name: 'walk-in') do |type|
  type.communication = true
  type.created_by_id = 1
  type.updated_by_id = 1
end

if Object.const_defined?(:ManuelContactFilter)
  Setting.create_if_not_exists(
    title:       'Defines postmaster filter.',
    name:        '6400_postmaster_filter_manuel_contact',
    area:        'Postmaster::PreFilter',
    description: 'Takes over contact data from the contact form and from sipgate, see MANUEL.',
    options:     {},
    state:       'ManuelContactFilter',
    frontend:    false,
  )
end

puts "Eingangswege: Typ walk-in, Filter #{Setting.find_by(name: '6400_postmaster_filter_manuel_contact') ? 'registriert' : 'nicht geladen'}"

# Copies of sent mails: Zammad adds MANUEL_SENT_BCC as BCC to every mail it sends, the sieve rules in
# mail/sieve/ file them to Sent, see docs/adr/0065-postfach-archivieren-und-aufbewahrung-begrenzen.adoc.
Setting.set('system_bcc', ENV['MANUEL_SENT_BCC']) if ENV['MANUEL_SENT_BCC'].present? && Setting.get('system_bcc') != ENV['MANUEL_SENT_BCC']

# Spam folder: a second email channel fetches MANUEL_SPAM_FOLDER of the first IMAP account, keeps the
# mails on the server and puts them into the group Spam check. The access data stay in Zammad.
spam_folder = ENV['MANUEL_SPAM_FOLDER'].presence
spam_group = Group.find_by(name: 'Spam check')
if spam_folder && spam_group
  imap = ->(channel) { channel.options.dig(:inbound, :adapter) == 'imap' }
  source = Channel.where(area: 'Email::Account').find { |c| imap.(c) && c.options.dig(:inbound, :options, :folder).to_s.in?(['', 'INBOX']) }
  if source
    clone = Channel.where(area: 'Email::Account').find do |c|
      imap.(c) && c.options.dig(:inbound, :options, :folder) == spam_folder &&
        c.options.dig(:inbound, :options, :user) == source.options.dig(:inbound, :options, :user)
    end
    options = source.options.deep_dup
    options[:inbound][:options][:folder] = spam_folder
    options[:inbound][:options][:keep_on_server] = true
    if clone.nil?
      Channel.create!(area: 'Email::Account', options: options, group_id: spam_group.id, active: source.active,
                      created_by_id: 1, updated_by_id: 1)
    elsif clone.options != options || clone.group_id != spam_group.id
      clone.update!(options: options, group_id: spam_group.id, updated_by_id: 1)
    end
  end
  puts "Spam-Ordner #{spam_folder}: #{source ? 'Kanal angelegt oder aktuell' : 'kein IMAP-Konto gefunden'}"
end
