import httpx
from core.config.env_manager import get_env_manager


async def send(http_client: httpx.AsyncClient, to_email: str, code: str) -> bool:
    env_manager = get_env_manager()
    try:
        response = await http_client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": env_manager.BREVO_API_KEY, "Content-Type": "application/json"},
            json={
                "sender": {"name": env_manager.MAIL_FROM_NAME, "email": env_manager.MAIL_FROM_ADDRESS},
                "to":     [{"email": to_email}],
                "subject": "Your verification code",
                "htmlContent": f"Your verification code is <strong>{code}</strong>. Valid for 10 minutes.",
            }
        )
        return response.status_code in (200, 201, 202)
    except Exception:
        return False
