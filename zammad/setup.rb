# Sets up a fresh or existing Zammad for a repair group as MANUEL expects it, see zammad/README.md.
# Runs with rails runner and can run again, existing records are updated instead of added twice.
# With docker compose it runs as the service manuel-setup from zammad/compose.yml:
#   docker compose --project-directory . -f quellen/zammad-docker-compose/docker-compose.yml \
#     -f zammad/compose.yml up -d
#
# Names, values and labels are English. German comes as custom translations, so Zammad shows the
# fields in the language each user has chosen and other initiatives can add their own language.

# Translations of the English strings used below, filled by tr() and written at the end
TRANSLATIONS = Hash.new { |hash, locale| hash[locale] = {} }

def tr(english, german)
  return english if german == english

  known = TRANSLATIONS['de-de'][english]
  warn "#{english} wird #{german}, vorher #{known}" if known && known != german
  TRANSLATIONS['de-de'][english] = german
  english
end

# Wait for the getting started wizard. Zammad offers it only while there are at most two users
# (setup_done? in app/controllers/getting_started_controller.rb), and groups.rb adds the guest agent.
until Setting.get('system_init_done')
  puts 'Warte auf den Einrichtungsassistenten von Zammad'
  sleep 30
  Setting.reload
end

# Records created on the way, like the items of a checklist, take their author from here
UserInfo.current_user_id = 1

load File.join(__dir__, 'groups.rb')
load File.join(__dir__, 'objects.rb')
# Create the columns right away, Zammad checks conditions of triggers and core workflows against the
# database. It reloads the columns here and only asks the other processes to restart.
ObjectManager::Attribute.migration_execute if ObjectManager::Attribute.migrations.any?
load File.join(__dir__, 'core_workflows.rb')
load File.join(__dir__, 'macros.rb')
load File.join(__dir__, 'knowledge_base.rb')
load File.join(__dir__, 'overviews.rb')
load File.join(__dir__, 'scheduler.rb')
load File.join(__dir__, 'inbound.rb')
load File.join(__dir__, 'press.rb')
load File.join(__dir__, 'workflows.rb')
load File.join(__dir__, 'agents.rb')
load File.join(__dir__, 'checklists.rb')
load File.join(__dir__, 'text_modules.rb')
load File.join(__dir__, 'templates.rb')
load File.join(__dir__, 'translations.rb')

ticket = ObjectLookup.by_name('Ticket')
puts "Felder: #{ObjectManager::Attribute.where(object_lookup_id: ticket, position: 1100..1299).order(:position).pluck(:name).join(', ')}"

# Again at the end for fields changed by the files above. Zammad restarts its other processes after a
# change of the database schema.
ObjectManager::Attribute.migration_execute
