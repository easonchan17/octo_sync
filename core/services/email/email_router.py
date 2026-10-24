import httpx
from datetime import datetime
from functools import cache

from core.logger.logger_manager import get_logger_manager
from core.config.env_manager import get_env_manager
from core.store.redis.redis_manager import get_redis_manager
from core.services.email.providers import brevo, mailjet, resend

class EmailRouter:
    def __init__(self, active_providers: list) -> None:
        self.logger            = get_logger_manager().get_logger(self.__class__.__name__)
        self.redis_manager     = get_redis_manager()
        self._active_providers = active_providers
        self._http_client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._http_client = httpx.AsyncClient(timeout=10.0)
        if not self._active_providers:
            self.logger.warning("EmailRouter: no email providers configured, send-code will be unavailable")
        else:
            self.logger.info(f"EmailRouter initialized with providers: {[p['name'] for p in self._active_providers]}")

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self.logger.info("EmailRouter resources cleaned up")

    async def send(self, to_email: str, code: str) -> None:
        if not self._active_providers:
            raise ValueError("邮件服务暂未配置，请联系管理员")

        redis = self.redis_manager.get_client()
        today = datetime.now().strftime("%Y%m%d")

        for provider in self._active_providers:
            quota_key = f"quota:email:{provider['name']}:{today}"
            count     = await redis.incr(quota_key)
            if count == 1:
                await redis.expire(quota_key, 86400)
            if count > provider["limit"]:
                continue

            success = await provider["send"](self._http_client, to_email, code)
            if success:
                return

            self.logger.warning(f"Provider {provider['name']} failed, trying next, quota_key={quota_key}")

        raise ValueError("今日发信额度已耗尽，请明天再试")


@cache
def get_email_router() -> EmailRouter:
    active_providers = []
    env_manager = get_env_manager()
    if env_manager.BREVO_API_KEY:
        active_providers.append({"name": "brevo",   "limit": 300, "send": brevo.send})
    if env_manager.MAILJET_API_KEY and env_manager.MAILJET_API_SECRET:
        active_providers.append({"name": "mailjet", "limit": 200, "send": mailjet.send})
    if env_manager.RESEND_API_KEY:
        active_providers.append({"name": "resend",  "limit": 100, "send": resend.send})
    return EmailRouter(active_providers=active_providers)
