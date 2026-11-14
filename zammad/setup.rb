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

load File.join(__dir__, 'groups.rb')
load File.join(__dir__, 'objects.rb')
load File.join(__dir__, 'macros.rb')
load File.join(__dir__, 'translations.rb')

ticket = ObjectLookup.by_name('Ticket')
puts "Felder: #{ObjectManager::Attribute.where(object_lookup_id: ticket, position: 1100..1299).order(:position).pluck(:name).join(', ')}"

# Last, because Zammad restarts its processes after changing the database schema
ObjectManager::Attribute.migration_execute
