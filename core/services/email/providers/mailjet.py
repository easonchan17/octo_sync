from core.services.email.providers.base import EmailProvider


class MailjetProvider(EmailProvider):
    name        = "mailjet"
    api_url     = "https://api.mailjet.com/v3.1/send"
    daily_limit = 200
    ok_status   = (200,)

    def is_enabled(self) -> bool:
        return bool(self.env.MAILJET_API_KEY and self.env.MAILJET_API_SECRET)

    def auth(self) -> tuple:
        return (self.env.MAILJET_API_KEY, self.env.MAILJET_API_SECRET)

    def build_payload(self, to_email: str, subject: str, content: str) -> dict:
        return {
            "Messages": [{
                "From": {"Email": self.env.MAIL_FROM_ADDRESS, "Name": self.env.MAIL_FROM_NAME},
                "To":   [{"Email": to_email}],
                "Subject":  subject,
                "HTMLPart": content,
            }]
        }

