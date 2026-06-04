import httpx
from core.config.env_manager import get_env_manager


async def send(http_client: httpx.AsyncClient, to_email: str, code: str) -> bool:
    env = get_env_manager()
    try:
        response = await http_client.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(env.MAILJET_API_KEY, env.MAILJET_API_SECRET),
            json={
                "Messages": [{
                    "From": {"Email": env.MAIL_FROM_ADDRESS, "Name": env.MAIL_FROM_NAME},
                    "To":   [{"Email": to_email}],
                    "Subject":  "Your verification code",
                    "HTMLPart": f"Your verification code is <strong>{code}</strong>. Valid for 10 minutes.",
                }]
            }
        )
        return response.status_code == 200
    except Exception:
        return False
