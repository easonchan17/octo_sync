from core.services.email.providers.base import EmailProvider


class ResendProvider(EmailProvider):
    name        = "resend"
    api_url     = "https://api.resend.com/emails"
    daily_limit = 100
    ok_status   = (200, 201)

    def is_enabled(self) -> bool:
        return bool(self.env.RESEND_API_KEY)

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.env.RESEND_API_KEY}", "Content-Type": "application/json"}

    def build_payload(self, to_email: str, subject: str, content: str) -> dict:
        return {
            "from":    f"{self.env.MAIL_FROM_NAME} <{self.env.MAIL_FROM_ADDRESS}>",
            "to":      [to_email],
            "subject": subject,
            "html":    content,
        }

