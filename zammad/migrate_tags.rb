# Replaces older tags that name only a month or a special event by the date tag YYYY-MM-DD, see
# docs/adr/0062-datums-tags-und-monatsuebersichten-automatisch-pflegen.adoc. Runs with rails runner:
#   rails runner zammad/migrate_tags.rb           shows what would change
#   MANUEL_MIGRATE=apply rails runner zammad/migrate_tags.rb
#
# A month tag like 2024-03 with exactly one event in the list of events becomes that date. In a month with
# two events a ticket gets the date its pending time matches, otherwise it is listed. Special tags come
# from legacy_tags.tsv, a row without a date stays open and is listed.

require 'csv'

APPLY = ENV['MANUEL_MIGRATE'] == 'apply'
EVENTS = ENV.fetch('MANUEL_EVENTS', File.expand_path('../docs/ora/anstiftung/events.tsv', __dir__))
LEGACY = File.expand_path('legacy_tags.tsv', __dir__)
MONTH_TAG = %r{\A(\d{4})-(\d{2})\z}

dates = CSV.read(EVENTS, col_sep: "\t", headers: true).map { |row| row['event_date'] }.grep(%r{\A\d{4}-\d{2}-\d{2}\z})
legacy = CSV.read(LEGACY, col_sep: "\t", headers: true, skip_lines: %r{\A#}).to_h { |row| [row['tag'], row] }
UserInfo.current_user_id = 1
open_items = []
changes = []

Tag::Item.find_each do |item|
  if (match = MONTH_TAG.match(item.name))
    in_month = dates.select { |date| date.start_with?("#{match[1]}-#{match[2]}-") }
    if in_month.size == 1
      changes << "#{item.name} -> #{in_month.first}"
      Tag::Item.rename(id: item.id, name: in_month.first) if APPLY
    elsif in_month.size > 1
      Tag.tag_references(tag: item.name, object: 'Ticket').each do |_object, o_id|
        ticket = Ticket.find_by(id: o_id)
        day = ticket&.pending_time&.in_time_zone('Europe/Berlin')&.to_date&.iso8601
        if day && in_month.include?(day)
          changes << "#{item.name} -> #{day} (Ticket #{ticket.number})"
          next if !APPLY

          ticket.tag_add(day, 1)
          ticket.tag_remove(item.name, 1)
        else
          open_items << "#{item.name}: Ticket #{ticket&.number} passt zu keinem der Termine #{in_month.join(', ')}"
        end
      end
    else
      open_items << "#{item.name}: kein Termin in #{EVENTS}"
    end
  elsif (row = legacy[item.name])
    if row['date'].blank?
      open_items << "#{item.name}: Datum in legacy_tags.tsv offen, #{row['note']}"
      next
    end
    changes << "#{item.name} -> #{row['date']} und #{row['extra_tag']}"
    next if !APPLY

    Tag.tag_references(tag: item.name, object: 'Ticket').each do |_object, o_id|
      ticket = Ticket.find_by(id: o_id)
      ticket&.tag_add(row['extra_tag'], 1) if row['extra_tag'].present?
    end
    Tag::Item.rename(id: item.id, name: row['date'])
  end
end

puts "#{APPLY ? 'Geändert' : 'Würde ändern (Probelauf, MANUEL_MIGRATE=apply zum Ausführen)'}: #{changes.size}"
changes.each { |line| puts "  #{line}" }
puts "Offen: #{open_items.size}"
open_items.each { |line| puts "  #{line}" }
