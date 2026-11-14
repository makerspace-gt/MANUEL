# Keeps the pending time of a ticket when the ticket leaves a pending state, for example when a guest
# replies. Repair groups use the pending time as date and time of the appointment, see
# docs/adr/0053-termin-in-der-wartezeit-behalten.adoc. Zammad clears it in Ticket#reset_pending_time
# in app/models/ticket.rb. This file overrides only that method instead of replacing the whole model.
#
# zammad/compose.yml mounts it into config/initializers of zammad-railsserver and zammad-scheduler.
# The scheduler matters as well, because it fetches the emails of guests.
# After an update of Zammad check that the method still exists. Without it this file has no effect,
# which is logged when Zammad starts.

module KeepPendingTime
  private

  def reset_pending_time
    true
  end
end

Rails.application.config.to_prepare do
  if Ticket.private_method_defined?(:reset_pending_time)
    Ticket.prepend(KeepPendingTime) if Ticket.ancestors.exclude?(KeepPendingTime)
  else
    message = 'keep_pending_time.rb: Ticket#reset_pending_time is missing, the pending time is not kept'
    warn message
    Rails.logger.error message
  end
end
