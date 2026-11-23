# Takes over contact data and the way a request came in, see
# docs/adr/0063-kontaktdaten-und-eingangswege-uebernehmen.adoc. Mounted as initializer by zammad/compose.yml,
# zammad/setup.rb registers ManuelContactFilter as postmaster pre filter 6400, before Zammad identifies the sender.
#
# Contact form: the mail comes from the web site, the guest is in the text. Name and email are read, the
# guest is found by email or created, and the first article gets the type web.
# sipgate: the mail of the voicemail comes from sipgate, the caller is the number after "Anruf von:". The
# guest is found by phone or mobile or created with the number, and the first article gets the type phone.
# Only empty fields are filled. A name or number that differs from the one stored, or a number that fits
# several guests, adds the tag contact-check, a human decides. Follow-ups to existing tickets are skipped.
#
# Numbers get the international format +49 5241 1234567, mobile numbers go to mobile, others to phone.
# Every guest saved by hand gets the same, see ManuelPhoneFormat below. A mobile number typed into phone
# moves to mobile when that is empty. Numbers the library does not recognise stay as they were typed.
# Other initiatives adapt the constants below.

module ManuelContact
  FORM_SUBJECT = %r{Kontaktformular}i
  FORM_NAME = %r{Dein Name:\s*(.+?)\s*(?:\n|Deine E-Mail-Adresse:)}m
  FORM_EMAIL = %r{Deine E-Mail-Adresse:\s*([^\s<>]+@[^\s<>]+)}
  SIPGATE_FROM = %r{sipgate}i
  SIPGATE_CALLER = %r{Anruf von:\s*\n?\s*([+\d][\d\s/()-]{4,})}
  NUMBER = %r{(?:\+49|\b0)[\d\s/()-]{6,}\d}
  CHECK_TAG = 'contact-check'.freeze
  COUNTRY = 'DE'.freeze

  module_function

  def text(mail)
    body = mail[:body].to_s
    body = body.gsub(%r{<br\s*/?>|</p>|</div>}i, "\n").gsub(%r{<[^>]+>}, '') if mail[:content_type].to_s.include?('html') || body.include?('<')
    CGI.unescapeHTML(body)
  end

  # International format and whether it is a mobile number, nil for anything that is no valid number
  def format(raw)
    digits = Cti::CallerId.normalize_number(raw.to_s)
    return if digits.blank?

    number = TelephoneNumber.parse("+#{digits}", COUNTRY)
    return if !number.valid?

    [number.international_number, number.valid_types.include?(:mobile)]
  end

  def add_tag(mail, tag)
    tags = mail[:'x-zammad-ticket-tags'].to_s.split(',').map(&:strip).compact_blank
    mail[:'x-zammad-ticket-tags'] = (tags | [tag]).join(', ')
  end

  def fill(user, attributes, mail)
    attributes.each do |key, value|
      next if value.blank?

      if user[key].blank?
        user[key] = value
      elsif user[key].to_s.casecmp(value.to_s) != 0
        add_tag(mail, CHECK_TAG)
      end
    end
    user.save! if user.changed?
  end

  def customer_role
    Role.where(name: 'Customer')
  end

  def form(mail)
    body = text(mail)
    email = body[FORM_EMAIL, 1]&.downcase
    return if email.blank?

    name = body[FORM_NAME, 1].to_s.strip
    firstname, _, lastname = name.rpartition(' ')
    firstname, lastname = lastname, '' if firstname.blank?
    user = User.find_by(email: email) || User.new(email: email, roles: customer_role, created_by_id: 1, updated_by_id: 1)
    attributes = { firstname: firstname, lastname: lastname }
    if (raw = body[NUMBER]) && (formatted, mobile = format(raw))
      attributes[mobile ? :mobile : :phone] = formatted
    end
    fill(user, attributes, mail)
    mail[:'x-zammad-ticket-customer_id'] = user.id
    mail[:'x-zammad-article-type'] = 'web'
  end

  def sipgate(mail)
    mail[:'x-zammad-article-type'] = 'phone'
    raw = text(mail)[SIPGATE_CALLER, 1]
    formatted, mobile = format(raw)
    return if formatted.nil?

    digits = Cti::CallerId.normalize_number(raw)
    ids = Cti::CallerId.where(caller_id: digits, level: 'known', object: 'User').distinct.pluck(:user_id)
    users = User.where(id: ids, active: true).to_a
    if users.size > 1
      add_tag(mail, CHECK_TAG)
      return
    end
    user = users.first || User.new(roles: customer_role, created_by_id: 1, updated_by_id: 1)
    user[mobile ? :mobile : :phone] = formatted if user.new_record?
    user.save! if user.new_record?
    mail[:'x-zammad-ticket-customer_id'] = user.id
  end

  def run(_channel, mail, _transaction_params = {})
    return if mail[:'x-zammad-ticket-id'].present?

    if mail[:from].to_s.match?(SIPGATE_FROM)
      sipgate(mail)
    elsif mail[:subject].to_s.match?(FORM_SUBJECT)
      form(mail)
    end
  rescue => e
    Rails.logger.error "ManuelContact: #{e.class} #{e.message}"
  end
end

# Formats phone and mobile of every user before saving, also for numbers typed in by hand
module ManuelPhoneFormat
  extend ActiveSupport::Concern

  included do
    before_save :manuel_format_phone
  end

  private

  def manuel_format_phone
    %w[phone mobile].each do |field|
      next if !will_save_change_to_attribute?(field) || self[field].blank?

      number, mobile = ManuelContact.format(self[field])
      next if number.nil?

      if field == 'phone' && mobile && mobile().blank?
        self.mobile = number
        self.phone = ''
      else
        self[field] = number
      end
    end
  rescue => e
    Rails.logger.error "ManuelPhoneFormat: #{e.class} #{e.message}"
  end
end

Rails.application.config.to_prepare do
  User.include(ManuelPhoneFormat) if User.ancestors.exclude?(ManuelPhoneFormat)
end

# Zammad loads pre filters by class name from the setting. A top-level class, because an initializer must
# not add constants to namespaces that Rails loads on demand.
class ManuelContactFilter
  def self.run(channel, mail, transaction_params = {})
    ManuelContact.run(channel, mail, transaction_params)
  end
end
