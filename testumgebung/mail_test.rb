# Sends a test mail through the notification channel of the Zammad test instance:
#   zammad "$(cat /usr/share/manuel/testumgebung/mail_test.rb)"
# It must show up in Mailpit and nowhere else. Run disable_outbound.rb before.

channel = Channel.find_by(area: 'Email::Notification', active: true)
abort 'Kein aktiver Benachrichtigungskanal, erst disable_outbound.rb ausführen.' if !channel
host = channel.options.dig(:outbound, :options, :host)
abort "Ausgehende Mail geht an #{host.inspect}, nicht an mailpit. Abbruch." if host != 'mailpit'

others = Channel.where(active: true).where.not(id: channel.id).pluck(:area)
abort "Weitere aktive Kanäle: #{others.join(', ')}. Abbruch." if others.any?

channel.deliver(
  {
    from:    'Zammad Testumgebung <zammad@example.org>',
    to:      'test@example.org',
    subject: "Testmail #{Time.zone.now.iso8601}",
    body:    'Wenn diese Mail in Mailpit erscheint, ist der Weg nach außen sicher abgefangen.',
  },
  true
)
puts 'Testmail an Mailpit übergeben.'
