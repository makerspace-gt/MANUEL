# Runs inside the Zammad test instance right after a restore, before the scheduler starts:
#   zammad "$(cat testumgebung/disable_outbound.rb)"
# It stops every way the test instance could reach real guests or mailboxes.

Channel.find_each { |channel| channel.update!(active: false) }
Webhook.find_each { |webhook| webhook.update!(active: false) } if defined?(Webhook)

notification = Channel.find_by(area: 'Email::Notification')
if notification
  notification.update!(
    active:  true,
    options: notification.options.merge(
      outbound: { adapter: 'smtp', options: { host: 'mailpit', port: 1025, ssl: false, start_tls: false } }
    )
  )
end

puts "Kanäle aktiv: #{Channel.where(active: true).pluck(:area).join(', ')}"
puts "Webhooks aktiv: #{defined?(Webhook) ? Webhook.where(active: true).count : 0}"
