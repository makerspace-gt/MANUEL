# Creates the ticket fields MANUEL needs in Zammad, see PLAN.md, section "Stammdaten für die Felder im Ticket".
# Runs with rails runner and can run again, existing fields are updated instead of added twice:
#   zammad "$(cat zammad/objekte.rb)" < katalog/kategorien.tsv
# Without the catalog on stdin the field for the kind of device is left out.
#
# The values follow the form on reparatur-initiativen.org and the result tree of our Zammad as
# exported on 13.11.2026. The names of the fields are our proposal. If an existing Zammad uses other
# names, change them in FIELDS before running, otherwise the script adds a second field.

require 'csv'

FIELDS = {
  geraeteart:      'Art des Geräts',
  marke:           'Marke',
  bezeichnung:     'Bezeichnung',
  baujahr:         'Baujahr',
  alter:           'Alter in Jahren',
  alter_angabe:    'Angabe zum Alter',
  stromversorgung: 'Stromversorgung',
  defekt:          'Defekt laut Anmeldung',
  defekt_festgestellt: 'Festgestellter Defekt',
  loesung:         'Lösung',
  ergebnis:        'Ergebnis',
  repariert_von:   'Repariert von',
  vde_pruefung:    'VDE 0701/0702 geprüft',
  termin:          'Termin',
  spenden:         'Spenden in Euro',
  bedarf:          'Bedarf im Repair Café',
}.freeze

AGENT_SCREENS = {
  create_middle: { 'ticket.agent' => { shown: true, required: false, item_class: 'column' } },
  edit:          { 'ticket.agent' => { shown: true, required: false } },
}.freeze

RESULT_TREE = {
  'No-Show'            => [],
  'gelungen'           => [],
  'teilweise gelungen' => [],
  'vertagt'            => ['Ersatzteilbesorgung durch Gast', 'Ersatzteilbesorgung durch Repair Café',
                           'Gerät nicht komplett', 'Hilfsmittel oder Zubehör fehlt', 'zu lange Wartezeit'],
  'nicht erfolgt'      => ['Abnutzung zu groß', 'Ersatzteil nicht erhältlich', 'Ersatzteil zu teuer',
                           'Fehler nicht gefunden', 'Gerät nicht komplett', 'Gesamtaufwand zu hoch',
                           'Hilfsmittel oder Zubehör fehlt', 'Reparaturinformationen nicht verfügbar',
                           'Teilnutzung möglich', 'hat noch Garantie', 'zu lange Wartezeit',
                           'Öffnung des Gerätes nicht möglich'],
  'abgebrochen'        => ['Gerät darf nicht mehr genutzt werden'],
}.freeze

def field(name, data_type, data_option, position)
  ObjectManager::Attribute.add(
    object:        'Ticket',
    name:          name.to_s,
    display:       FIELDS.fetch(name),
    data_type:     data_type,
    data_option:   { null: true, **data_option },
    active:        true,
    screens:       AGENT_SCREENS,
    position:      position,
    created_by_id: 1,
    updated_by_id: 1,
  )
end

def select(options, **extra)
  { options: options, default: '', nulloption: true, multiple: false, translate: false, maxlength: 255, **extra }
end

# Catalog key as value and name as label, so the key stays in the ticket when a name changes, see ADR 13
catalog = $stdin.tty? ? '' : $stdin.read
if catalog.strip.empty?
  puts 'Ohne Katalog auf stdin, Feld geraeteart ausgelassen'
else
  rows = CSV.parse(catalog, col_sep: "\t", headers: true, liberal_parsing: true, quote_char: "\x00")
  field(:geraeteart, 'select', select(rows.to_h { |row| [row['key'], row['name']] }), 1100)
end

# Generic for items without a brand, as the Open Repair Data Standard calls them, see docs/adr/0052
field(:marke, 'input', { type: 'text', maxlength: 120, default: '' }, 1110)
field(:bezeichnung, 'input', { type: 'text', maxlength: 120, default: '' }, 1120)
field(:baujahr, 'integer', { min: 1900, max: 2100, default: nil }, 1130)
# The uncertainty goes into alter_angabe, for example mindestens for "at least 12 years", see docs/adr/0052
field(:alter, 'integer', { min: 0, max: 200, default: nil }, 1132)
field(:alter_angabe, 'select', select(%w[genau etwa mindestens].to_h { |v| [v, v] }), 1134)
field(:stromversorgung, 'select',
      select(['mit Netzteil', '230 V', 'Batterie', 'Akku', 'ohne Kabel (Mechanik)'].to_h { |v| [v, v] }), 1140)
# Reported or suspected before the event, the defect found during the repair and the solution follow, see docs/adr/0052
field(:defekt, 'textarea', { type: 'textarea', maxlength: 1000, rows: 3, default: '' }, 1150)
field(:defekt_festgestellt, 'textarea', { type: 'textarea', maxlength: 1000, rows: 3, default: '' }, 1155)
field(:loesung, 'textarea', { type: 'textarea', maxlength: 1000, rows: 3, default: '' }, 1160)
field(:ergebnis, 'tree_select', {
        options:    RESULT_TREE.map do |name, children|
                      node = { 'name' => name, 'value' => name }
                      node['children'] = children.map { |c| { 'name' => c, 'value' => "#{name}::#{c}" } } if children.any?
                      node
                    end,
        default:    '', nulloption: true, multiple: false, translate: false, maxlength: 255,
      }, 1170)
field(:repariert_von, 'select', select(['Gast selbst', 'Gast mit Hilfe', 'Engagierte'].to_h { |v| [v, v] }), 1180)
# Empty means not decided yet, empfohlen means a check is due, see case-study chapter 7
field(:vde_pruefung, 'select', select({ 'empfohlen' => 'empfohlen', 'ja' => 'ja', 'nein' => 'nein' }), 1190)
field(:termin, 'date', { future: true, past: true, diff: 0, default: nil }, 1200)
# Only filled in the statistics ticket of each date, see PLAN.md, phase 0
field(:spenden, 'integer', { min: 0, max: 100_000, default: nil }, 1210)
field(:bedarf, 'textarea', { type: 'textarea', maxlength: 2000, rows: 3, default: '' }, 1220)

ObjectManager::Attribute.migration_execute
names = FIELDS.keys.map(&:to_s)
puts "Felder in Zammad: #{ObjectManager::Attribute.where(name: names).order(:position).pluck(:name).join(', ')}"
