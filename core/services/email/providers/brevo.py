from core.services.email.providers.base import EmailProvider


class BrevoProvider(EmailProvider):
    name        = "brevo"
    api_url     = "https://api.brevo.com/v3/smtp/email"
    daily_limit = 300
    ok_status   = (200, 201, 202)

    def is_enabled(self) -> bool:
        return bool(self.env.BREVO_API_KEY)

    def headers(self) -> dict[str, str]:
        return {"api-key": self.env.BREVO_API_KEY, "Content-Type": "application/json"}

    def build_payload(self, to_email: str, subject: str, content: str) -> dict:
        return {
            "sender": {"name": self.env.MAIL_FROM_NAME, "email": self.env.MAIL_FROM_ADDRESS},
            "to":     [{"email": to_email}],
            "subject": subject,
            "htmlContent": content,
        }
