# Sieve rules of the mailbox that Zammad fetches, see mail/README.md and
# docs/adr/0065-postfach-archivieren-und-aufbewahrung-begrenzen.adoc.
# Order matters. Copies of mails Zammad sent itself go to Sent only, otherwise Zammad would fetch them again.
# Every other mail is copied to Archiv, spam goes to Spam, mails from the contact form never count as spam.
require ["copy","fileinto","regex"];

# rule:[Sent] Zammad sends a BCC of every mail to this mailbox, see the setting system_bcc.
# Replace the domain by the one Zammad sends from.
if allof (header :contains "x-mailer" "Zammad Mail Service", address :domain "from" "makerspace-gt.de")
{
	fileinto "Sent";
	stop;
}
# rule:[Archiv]
if true
{
	fileinto :copy "Archiv";
}
# rule:[x-dspam-result]
if allof (header :regex "x-dspam-result" "^(Spam|Virus|Bl[ao]cklisted)$", not header :contains "subject" "Kontaktformular")
{
	fileinto "Spam";
	stop;
}
# rule:[X-Spam-Rspamd]
if allof (header :contains "x-spam-rspamd" "Yes", not header :contains "subject" "Kontaktformular")
{
	fileinto "Spam";
	stop;
}
