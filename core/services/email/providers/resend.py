import httpx
from core.config.env_manager import get_env_manager


async def send(http_client: httpx.AsyncClient, to_email: str, code: str) -> bool:
    env = get_env_manager()
    try:
        response = await http_client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {env.RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from":    f"{env.MAIL_FROM_NAME} <{env.MAIL_FROM_ADDRESS}>",
                "to":      [to_email],
                "subject": "Your verification code",
                "html":    f"Your verification code is <strong>{code}</strong>. Valid for 10 minutes.",
            }
        )
        return response.status_code in (200, 201)
    except Exception:
        return False
