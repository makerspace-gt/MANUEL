# Ticket fields MANUEL needs, loaded by zammad/setup.rb, see PLAN.md, section "Stammdaten für die
# Felder im Ticket", and docs/adr/0052-erfasste-daten-festlegen.adoc.
#
# Names follow the Open Repair Data Standard where it has a field, for example brand and
# year_of_manufacture. Values are English and stay in the ticket, the labels are translated by Zammad.
# The values follow the form on reparatur-initiativen.org and the result tree of our Zammad as exported
# on 13.11.2026, see eval/ora/result_mapping.tsv for the old German values.
# The catalog is read from MANUEL_CATALOG or katalog/kategorien.tsv next to this folder. Without it the
# field for the kind of device is left out.

require 'csv'

AGENT_SCREENS = {
  create_middle: { 'ticket.agent' => { shown: true, required: false, item_class: 'column' } },
  edit:          { 'ticket.agent' => { shown: true, required: false } },
}.freeze

def field(name, display, data_type, data_option, position)
  ObjectManager::Attribute.add(
    object:        'Ticket',
    name:          name,
    display:       display,
    data_type:     data_type,
    data_option:   { null: true, **data_option },
    active:        true,
    screens:       AGENT_SCREENS,
    position:      position,
    created_by_id: 1,
    updated_by_id: 1,
  )
end

# Options as { value => [English label, German label] }
def choice(options, **extra)
  labels = options.to_h { |value, (english, german)| [value, tr(english, german)] }
  { options: labels, default: '', nulloption: true, multiple: false, translate: true, maxlength: 255, **extra }
end

def text(rows: 3, maxlength: 1000)
  { type: 'textarea', maxlength: maxlength, rows: rows, default: '' }
end

RESULT_TREE = {
  ['No-show', 'No-Show']                    => [],
  %w[Fixed gelungen]                        => [],
  ['Partly fixed', 'teilweise gelungen']    => [],
  %w[Postponed vertagt]                     => [
    ['Spare part ordered by the visitor', 'Ersatzteilbesorgung durch Gast'],
    ['Spare part ordered by the repair group', 'Ersatzteilbesorgung durch die Initiative'],
    ['Item incomplete', 'Gerät nicht komplett'],
    ['Tool or accessory missing', 'Hilfsmittel oder Zubehör fehlt'],
    ['Waiting time too long', 'zu lange Wartezeit'],
  ],
  ['Not repaired', 'nicht erfolgt']         => [
    ['Too worn out', 'Abnutzung zu groß'],
    ['Spare part not available', 'Ersatzteil nicht erhältlich'],
    ['Spare part too expensive', 'Ersatzteil zu teuer'],
    ['Fault not found', 'Fehler nicht gefunden'],
    ['Item incomplete', 'Gerät nicht komplett'],
    ['Total effort too high', 'Gesamtaufwand zu hoch'],
    ['Tool or accessory missing', 'Hilfsmittel oder Zubehör fehlt'],
    ['Repair information not available', 'Reparaturinformationen nicht verfügbar'],
    ['Partly usable', 'Teilnutzung möglich'],
    ['Still under warranty', 'hat noch Garantie'],
    ['Waiting time too long', 'zu lange Wartezeit'],
    ['Item cannot be opened', 'Öffnung des Gerätes nicht möglich'],
  ],
  %w[Aborted abgebrochen]                   => [
    ['Item must not be used any more', 'Gerät darf nicht mehr genutzt werden'],
  ],
}.freeze

def result_tree
  RESULT_TREE.map do |(english, german), children|
    node = { 'name' => tr(english, german), 'value' => english }
    if children.any?
      node['children'] = children.map do |child, child_german|
        { 'name' => tr(child, child_german), 'value' => "#{english}::#{child}" }
      end
    end
    node
  end
end

# Catalog key as value and English name as label, so the key stays in the ticket when a name changes,
# see ADR 13. Entries without an English name show the German one.
catalog_path = ENV.fetch('MANUEL_CATALOG', File.expand_path('../katalog/kategorien.tsv', __dir__))
if File.exist?(catalog_path)
  rows = CSV.read(catalog_path, col_sep: "\t", headers: true, liberal_parsing: true, quote_char: "\x00")
  options = rows.to_h { |row| [row['key'], [row['name_en'].presence || row['name'], row['name']]] }
  field('device_type', tr('Device type', 'Art des Geräts'), 'select', choice(options), 1100)
else
  puts "Kein Katalog unter #{catalog_path}, Feld device_type ausgelassen"
end

# Generic for items without a brand, as the Open Repair Data Standard calls them, see docs/adr/0052
field('brand', tr('Brand', 'Marke'), 'input', { type: 'text', maxlength: 120, default: '' }, 1110)
field('device_model', tr('Model or type', 'Bezeichnung'), 'input', { type: 'text', maxlength: 120, default: '' }, 1120)
field('year_of_manufacture', tr('Year of manufacture', 'Baujahr'), 'integer',
      { min: 1900, max: 2100, default: nil }, 1130)
# The uncertainty goes into product_age_qualifier, for example at_least for "at least 12 years"
field('product_age', tr('Age in years', 'Alter in Jahren'), 'integer', { min: 0, max: 200, default: nil }, 1132)
field('product_age_qualifier', tr('Age given as', 'Angabe zum Alter'), 'select',
      choice({ 'exact' => %w[Exact genau], 'about' => %w[About etwa], 'at_least' => ['At least', 'mindestens'] }),
      1134)
field('power_supply', tr('Power source', 'Stromversorgung'), 'select',
      choice({ 'adapter'      => ['Power adapter', 'mit Netzteil'],
               'mains'        => ['230 V', '230 V'],
               'battery'      => ['Disposable battery', 'Batterie'],
               'rechargeable' => ['Rechargeable battery', 'Akku'],
               'none'         => ['No cable (mechanical)', 'ohne Kabel (Mechanik)'] }), 1140)
# The defect reported or suspected before the event, the defect found during the repair and the solution
field('problem_reported', tr('Problem as reported', 'Defekt laut Anmeldung'), 'textarea', text, 1150)
field('problem_found', tr('Problem found', 'Festgestellter Defekt'), 'textarea', text, 1155)
field('solution', tr('Solution', 'Lösung'), 'textarea', text, 1160)
field('repair_result', tr('Result', 'Ergebnis'), 'tree_select',
      { options: result_tree, default: '', nulloption: true, multiple: false, translate: true, maxlength: 255 }, 1170)
field('repaired_by', tr('Repaired by', 'Repariert von'), 'select',
      choice({ 'visitor'      => ['Visitor alone', 'Gast selbst'],
               'visitor_help' => ['Visitor with help', 'Gast mit Hilfe'],
               'volunteers'   => %w[Volunteers Engagierte] }), 1180)
# Empty means not decided yet, recommended means a check is due, see case-study chapter 7
field('safety_test', tr('Safety test VDE 0701/0702', 'VDE 0701/0702 geprüft'), 'select',
      choice({ 'recommended' => %w[Recommended empfohlen], 'yes' => %w[Yes Ja], 'no' => %w[No Nein] }), 1190)
field('event_date', tr('Event date', 'Termin'), 'date', { future: true, past: true, diff: 0, default: nil }, 1200)
# Only filled in the statistics ticket of each date, see PLAN.md, phase 0
field('donations', tr('Donations in euros', 'Spenden in Euro'), 'integer', { min: 0, max: 100_000, default: nil }, 1210)
field('needs', tr('Needs of the repair group', 'Bedarf der Initiative'), 'textarea', text(maxlength: 2000), 1220)
