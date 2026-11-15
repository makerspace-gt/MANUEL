# Lets AI agents write internal notes, see docs/adr/0061-loesungsansatz-eine-woche-vor-dem-termin-schreiben.adoc.
# Mounted as initializer by zammad/compose.yml.
#
# The action of an agent reaches perform changes as JSON with string keys. The action for notes reads the
# subject with a symbol (app/models/ticket/perform_changes/action/article_note.rb), gets nil and Zammad
# then looks for a mail template file and fails. Triggers are not affected, their data allows both keys.
# The patch gives the action data that answers to both, it changes nothing else.

module ManuelAgentNote
  def initialize(record, execution_data, perform_changes_data)
    super(record, execution_data.respond_to?(:with_indifferent_access) ? execution_data.with_indifferent_access : execution_data,
          perform_changes_data)
  end
end

Rails.application.config.to_prepare do
  action = Ticket::PerformChanges::Action::ArticleNote
  action.prepend(ManuelAgentNote) if action.ancestors.exclude?(ManuelAgentNote)
end
