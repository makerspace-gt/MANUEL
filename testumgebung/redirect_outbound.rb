# Keeps fetching from real mailboxes but sends every outgoing mail of the Zammad test instance to Mailpit:
#   zammad "$(cat /usr/share/manuel/testumgebung/redirect_outbound.rb)"
# Use it to test with a real test mailbox. Never with the mailbox of the Repair Café and never after
# restoring a backup, there disable_outbound.rb switches fetching off as well.

mailpit = { adapter: 'smtp', options: { host: 'mailpit', port: 465, ssl: true, ssl_verify: false } }

Channel.where(area: ['Email::Account', 'Email::Notification']).find_each do |channel|
  channel.update!(options: channel.options.merge(outbound: mailpit))
end
Channel.where.not(area: ['Email::Account', 'Email::Notification']).find_each { |c| c.update!(active: false) }
Webhook.find_each { |webhook| webhook.update!(active: false) } if defined?(Webhook)

Channel.where(active: true).find_each do |channel|
  puts "#{channel.area} #{channel.id}: Abruf #{channel.options.dig(:inbound, :adapter) || 'keiner'}, " \
       "Versand an #{channel.options.dig(:outbound, :options, :host)}"
end
