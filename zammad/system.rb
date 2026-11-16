# Does what the getting started wizard of Zammad does, loaded by zammad/setup.rb before everything else:
# base settings, the first admin and system_init_done, as Service::User::AddFirstAdmin and
# Service::System::SetSystemInformation do. It runs only on a fresh Zammad and only when address and
# password of the admin are given. Without them setup.rb waits for the wizard in the browser.
#
# The password never goes into a repository or an image. On MANUEL it comes from /etc/manuel/zammad.env,
# which zammad-compose reads when it exists, see docs/inbetriebnahme.md:
#   MANUEL_ADMIN_EMAIL=admin@example.org
#   MANUEL_ADMIN_PASSWORD=...
#   MANUEL_ADMIN_NAME=Vorname Nachname     optional
# URL and organization come from MANUEL_URL and MANUEL_ORGANIZATION, language and time zone from
# MANUEL_LOCALE (default de-de) and TZ. Calendar and text modules of the wizard are left out, the wizard
# guesses the calendar from the IP address with an outside service.

email = ENV['MANUEL_ADMIN_EMAIL'].to_s.strip.downcase.presence
password = ENV['MANUEL_ADMIN_PASSWORD'].presence

if Setting.get('system_init_done')
  # set up before, by the wizard or an earlier run
elsif email.nil? || password.nil?
  puts 'Kein MANUEL_ADMIN_EMAIL und MANUEL_ADMIN_PASSWORD, die Einrichtung läuft über den Assistenten im Browser'
elsif User.count > 2
  puts 'Es gibt schon Nutzer, die Einrichtung läuft über den Assistenten im Browser'
else
  UserInfo.ensure_current_user_id do
    Service::System::SetSystemInformation.new(data: {
      url:              ENV.fetch('MANUEL_URL'),
      organization:     ENV.fetch('MANUEL_ORGANIZATION'),
      locale_default:   ENV['MANUEL_LOCALE'].presence || 'de-de',
      timezone_default: ENV['TZ'].presence || 'Europe/Berlin',
    }).execute

    PasswordPolicy.new(password).valid!
    firstname, _, lastname = ENV['MANUEL_ADMIN_NAME'].to_s.strip.rpartition(' ')
    firstname, lastname = lastname, '' if firstname.blank?
    User.create!(login: email, email: email, password: password, active: true,
                 firstname: firstname.presence || 'Admin', lastname: lastname,
                 role_ids: Role.where(name: %w[Admin Agent]).pluck(:id), group_ids: Group.pluck(:id))
    Setting.set('system_init_done', true)
  end
  puts "System eingerichtet für #{Setting.get('fqdn')}, Admin #{email}"
end
