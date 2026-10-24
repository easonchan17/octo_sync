import secrets
import httpx
from datetime import datetime
from functools import cache
from core.logger.logger_manager import get_logger_manager
from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager
from core.store.redis.redis_manager import get_redis_manager, RedisManager
from core.services.email.email_router import get_email_router

TURNSTILE_VERIFY_URL   = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
EMAIL_SUBJECT          = "Your verification code"
EMAIL_CONTENT_TEMPLATE = "Your verification code is <strong>{code}</strong>. Valid for {minutes} minutes."


class CodeStore:
    def __init__(
        self,
        redis_manager: RedisManager,
        code_ttl: int,
        cooldown_ttl: int,
        ip_daily_limit: int,
        email_daily_limit: int,
        max_wrong_attempts: int,
    ) -> None:
        self.redis_manager      = redis_manager
        self.code_ttl           = code_ttl
        self.cooldown_ttl       = cooldown_ttl
        self.ip_daily_limit     = ip_daily_limit
        self.email_daily_limit  = email_daily_limit
        self.max_wrong_attempts = max_wrong_attempts

    def _code_key(self, email: str) -> str:
        return f"auth:code:{email}"

    def _lock_key(self, email: str) -> str:
        return f"lock:email:send:{email}"

    def _ip_count_key(self, user_ip: str) -> str:
        return f"limit:email:ip:{user_ip}:{datetime.now().strftime('%Y%m%d')}"

    def _email_count_key(self, email: str) -> str:
        return f"limit:email:addr:{email}:{datetime.now().strftime('%Y%m%d')}"

    async def is_cooldown_locked(self, email: str) -> bool:
        return bool(await self.redis_manager.get_client().exists(self._lock_key(email)))

    async def is_ip_limit_exceeded(self, user_ip: str) -> bool:
        count = int(await self.redis_manager.get_client().get(self._ip_count_key(user_ip)) or 0)
        return count >= self.ip_daily_limit

    async def is_email_limit_exceeded(self, email: str) -> bool:
        count = int(await self.redis_manager.get_client().get(self._email_count_key(email)) or 0)
        return count >= self.email_daily_limit

    def is_attempts_exceeded(self, wrong_attempts: int) -> bool:
        return wrong_attempts >= self.max_wrong_attempts

    def remaining_attempts(self, wrong_attempts: int) -> int:
        return self.max_wrong_attempts - wrong_attempts - 1

    async def save_code(self, email: str, code: str, user_ip: str) -> None:
        redis     = self.redis_manager.get_client()
        ip_key    = self._ip_count_key(user_ip)
        email_key = self._email_count_key(email)

        ip_count    = int(await redis.get(ip_key) or 0)
        email_count = int(await redis.get(email_key) or 0)

        async with redis.pipeline(transaction=True) as pipe:
            pipe.hset(self._code_key(email), mapping={"code": code, "wrong_attempts": "0"})
            pipe.expire(self._code_key(email), self.code_ttl)
            pipe.set(self._lock_key(email), "1", ex=self.cooldown_ttl)
            pipe.incr(ip_key)
            pipe.incr(email_key)
            await pipe.execute()

        if ip_count == 0:
            await redis.expire(ip_key, 86400)
        if email_count == 0:
            await redis.expire(email_key, 86400)

    async def load_code(self, email: str) -> dict | None:
        data = await self.redis_manager.get_client().hgetall(self._code_key(email))
        return data or None

    async def increment_wrong_attempts(self, email: str) -> None:
        await self.redis_manager.get_client().hincrby(self._code_key(email), "wrong_attempts", 1)

    async def delete_code(self, email: str) -> None:
        await self.redis_manager.get_client().delete(self._code_key(email))


class OtpService:
    def __init__(self, code_store: CodeStore, email_whitelist: set) -> None:
        self.logger          = get_logger_manager().get_logger(self.__class__.__name__)
        self.env_manager     = get_env_manager()
        self.email_router    = get_email_router()
        self.code_store      = code_store
        self.email_whitelist = email_whitelist

    async def send_code(self, email: str, turnstile_token: str, user_ip: str) -> None:
        if await self.code_store.is_cooldown_locked(email):
            raise ValueError(f"请等待 {self.code_store.cooldown_ttl} 秒后再试")

        await self._verify_turnstile(turnstile_token)

        if email not in self.email_whitelist:
            if await self.code_store.is_ip_limit_exceeded(user_ip):
                raise ValueError("该网络今日发送次数已达上限，请明天再试")
            if await self.code_store.is_email_limit_exceeded(email):
                raise ValueError("该邮箱今日发送次数已达上限，请明天再试")

        code = f"{secrets.randbelow(1000000):06d}"
        await self.code_store.save_code(email, code, user_ip)
        await self.email_router.send(email, EMAIL_SUBJECT, self._build_email_content(code))

    def _build_email_content(self, code: str) -> str:
        minutes = max(1, self.code_store.code_ttl // 60)
        return EMAIL_CONTENT_TEMPLATE.format(code=code, minutes=minutes)

    async def verify_code(self, email: str, code: str) -> None:
        data = await self.code_store.load_code(email)
        if not data:
            raise ValueError("验证码已过期或未获取")

        wrong_attempts = int(data.get("wrong_attempts", 0))

        if self.code_store.is_attempts_exceeded(wrong_attempts):
            await self.code_store.delete_code(email)
            raise ValueError("错误次数过多，验证码已作废")

        if data.get("code") != code:
            await self.code_store.increment_wrong_attempts(email)
            raise ValueError(f"验证码错误，还剩 {self.code_store.remaining_attempts(wrong_attempts)} 次机会")

        await self.code_store.delete_code(email)

    async def _verify_turnstile(self, token: str) -> None:
        secret = self.env_manager.TURNSTILE_SECRET
        if not secret:
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    TURNSTILE_VERIFY_URL,
                    data={"secret": secret, "response": token}
                )
                result = response.json()
        except Exception:
            raise ValueError("人机验证请求失败")

        if not result.get("success"):
            raise ValueError("人机验证失败")


@cache
def get_otp_service() -> OtpService:
    config = get_config_manager().get_config("auth.otp", {})
    return OtpService(
        code_store = CodeStore(
            redis_manager      = get_redis_manager(),
            code_ttl           = config["code_ttl"],
            cooldown_ttl       = config["cooldown_ttl"],
            ip_daily_limit     = config["ip_daily_limit"],
            email_daily_limit  = config["email_daily_limit"],
            max_wrong_attempts = config["max_wrong_attempts"],
        ),
        email_whitelist = get_env_manager().email_whitelist,
    )
