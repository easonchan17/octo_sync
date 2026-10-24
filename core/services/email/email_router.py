import httpx
from datetime import datetime
from functools import cache

from core.logger.logger_manager import get_logger_manager
from core.store.redis.redis_manager import get_redis_manager
from core.services.email.providers.base import EmailProvider
from core.services.email.providers.brevo import BrevoProvider
from core.services.email.providers.mailjet import MailjetProvider
from core.services.email.providers.resend import ResendProvider

class EmailRouter:
    def __init__(self, active_providers: list[EmailProvider]) -> None:
        self.logger            = get_logger_manager().get_logger(self.__class__.__name__)
        self.redis_manager     = get_redis_manager()
        self._active_providers = active_providers
        self._http_client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._http_client = httpx.AsyncClient(timeout=10.0)
        if not self._active_providers:
            self.logger.warning("EmailRouter: no email providers configured, send-code will be unavailable")
        else:
            self.logger.info(f"EmailRouter initialized with providers: {[p.name for p in self._active_providers]}")

    async def shutdown(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
            self.logger.info("EmailRouter resources cleaned up")

    async def send(self, to_email: str, subject: str, content: str) -> None:
        if not self._active_providers:
            raise ValueError("邮件服务暂未配置，请联系管理员")

        redis = self.redis_manager.get_client()
        if redis is None or self._http_client is None:
            raise RuntimeError("EmailRouter.send() called before startup()")

        today = datetime.now().strftime("%Y%m%d")

        for provider in self._active_providers:
            quota_key = f"quota:email:{provider.name}:{today}"
            count     = await redis.incr(quota_key)
            if count == 1:
                await redis.expire(quota_key, 86400)
            if count > provider.daily_limit:
                self.logger.warning(
                    f"Provider {provider.name} quota exhausted, skipping: "
                    f"quota_key={quota_key} count={count} limit={provider.daily_limit}"
                )
                continue

            success = await provider.send(self._http_client, to_email, subject, content)
            if success:
                return

            self.logger.warning(f"Provider {provider.name} failed, trying next, quota_key={quota_key}")

        raise ValueError("今日发信额度已耗尽，请明天再试")


@cache
def get_email_router() -> EmailRouter:
    providers: list[EmailProvider] = [BrevoProvider(), MailjetProvider(), ResendProvider()]
    return EmailRouter(active_providers=[p for p in providers if p.is_enabled()])
