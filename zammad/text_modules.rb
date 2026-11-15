# Text modules for answers to guests, loaded by zammad/setup.rb, see
# docs/adr/0060-ablaeufe-des-bestehenden-zammad-als-code-uebernehmen.adoc. They come from
# zammad/texts/text_modules.de.tsv, typed with "::" and the name or a keyword. A module of an older Zammad
# with the name in the column legacy is renamed. New ones are active, a later run never changes active.

require 'csv'

rows = CSV.read(File.join(__dir__, 'texts', 'text_modules.de.tsv'), col_sep: "\t", headers: true, skip_lines: %r{\A#},
                                                                    liberal_parsing: true, quote_char: "\u0000")
rows.each do |row|
  record = TextModule.find_by(name: row['name']) || TextModule.find_by(name: row['legacy']) || TextModule.new(active: true)
  record.assign_attributes(name: row['name'], keywords: row['keywords'], content: row['content'],
                           groups: Group.where(name: row['groups'].split(',')))
  record.created_by_id ||= 1
  record.updated_by_id = 1
  record.save! if record.new_record? || record.changed?
end

puts "Textbausteine: #{TextModule.where(name: rows.map { |row| row['name'] }).pluck(:name).join(', ')}"
