# Transcribes voicemails locally with whisper.cpp instead of the service of sipgate, see
# docs/adr/0064-voicemails-lokal-transkribieren.adoc. Mounted as initializer by zammad/compose.yml,
# zammad/scheduler.rb adds a scheduler entry for ManuelVoicemail.run every five minutes.
#
# A first article from sipgate, or one whose text names the caller, with an audio attachment and a ticket
# without the tag transcribed is sent to MANUEL_WHISPER_URL. The text comes back as internal note and the ticket gets the tag transcribed.
# An empty text means nobody spoke, the ticket gets no-info and is closed. Without MANUEL_WHISPER_URL
# nothing happens. The audio stays in the ticket and is never sent anywhere else.

require 'net/http'

module ManuelVoicemail
  SENDER = %r{sipgate}i
  # The text of sipgate names the caller, it identifies the voicemail when the sender was replaced
  MARKER = 'Anruf von:'.freeze
  TAG = 'transcribed'.freeze
  NOTE_PREFIX = 'Transkript der Voicemail, lokal mit Whisper:'.freeze
  MAX_AGE = 7.days

  module_function

  def url
    ENV['MANUEL_WHISPER_URL'].presence
  end

  def audio(article)
    article.attachments.find { |file| file.preferences['Content-Type'].to_s.start_with?('audio/') || file.filename.to_s.match?(%r{\.(mp3|wav|ogg|m4a)\z}i) }
  end

  def candidates
    Ticket.where(created_at: MAX_AGE.ago..).find_each.select do |ticket|
      next false if ticket.tag_list.include?(TAG)

      first = ticket.articles.order(:id).first
      first && (first.from.to_s.match?(SENDER) || first.body.to_s.include?(MARKER)) && audio(first)
    end
  end

  # Multipart upload as whisper-server expects it, the text comes back without timestamps
  def transcribe(file)
    uri = URI(url)
    boundary = "manuel#{SecureRandom.hex(8)}"
    parts = [
      ['file', file.filename, file.preferences['Content-Type'].presence || 'application/octet-stream', file.content],
      ['response_format', nil, nil, 'text'],
      ['temperature', nil, nil, '0'],
    ]
    body = parts.map do |name, filename, type, data|
      header = "--#{boundary}\r\nContent-Disposition: form-data; name=\"#{name}\""
      header += "; filename=\"#{filename}\"\r\nContent-Type: #{type}" if filename
      "#{header}\r\n\r\n#{data}\r\n"
    end.join + "--#{boundary}--\r\n"
    request = Net::HTTP::Post.new(uri, 'Content-Type' => "multipart/form-data; boundary=#{boundary}")
    request.body = body.b
    response = Net::HTTP.start(uri.host, uri.port, read_timeout: 600) { |http| http.request(request) }
    raise "whisper answered #{response.code}" if !response.is_a?(Net::HTTPSuccess)

    response.body.to_s.force_encoding('UTF-8').strip
  end

  def run
    return if url.nil?

    UserInfo.current_user_id = 1
    candidates.each do |ticket|
      first = ticket.articles.order(:id).first
      text = transcribe(audio(first))
      if text.blank? || text.match?(%r{\A\[?(BLANK_AUDIO|Musik|Stille)\]?\z}i)
        ticket.tag_add('no-info', 1)
        ticket.update!(state: Ticket::State.find_by!(name: 'closed'))
      else
        Ticket::Article.create!(ticket_id: ticket.id, body: "#{NOTE_PREFIX}\n\n#{text}", content_type: 'text/plain',
                                internal: true, sender: Ticket::Article::Sender.find_by!(name: 'System'),
                                type: Ticket::Article::Type.find_by!(name: 'note'))
      end
      ticket.tag_add(TAG, 1)
    rescue => e
      Rails.logger.error "ManuelVoicemail: ticket #{ticket.id} #{e.class} #{e.message}"
    end
    true
  end
end
