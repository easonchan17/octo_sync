import jwt
import secrets as sec
from datetime import datetime, timedelta, timezone
from functools import cache
from core.logger.logger_manager import get_logger_manager
from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager
from core.store.redis.redis_manager import get_redis_manager
from core.store.postgres.daos.common.user_dao import UserDao
from core.services.auth.otp_service import get_otp_service


class AuthService:
    def __init__(self, algorithm: str, token_expire_days: int, allowed_origins: list) -> None:
        self.logger            = get_logger_manager().get_logger(self.__class__.__name__)
        self.env_manager       = get_env_manager()
        self.redis_manager     = get_redis_manager()
        self.otp_service       = get_otp_service()
        self.user_dao          = UserDao()
        self.algorithm         = algorithm
        self.token_expire_days = token_expire_days
        self.allowed_origins   = set(allowed_origins)

    def is_origin_allowed(self, origin: str) -> bool:
        return not self.allowed_origins or origin in self.allowed_origins

    async def login(self, email: str, code: str) -> str:
        await self.otp_service.verify_code(email, code)
        uid = self.user_dao.get_or_create(email)
        payload = {
            "sub": uid,
            "jti": sec.token_hex(16),
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=self.token_expire_days),
        }
        return jwt.encode(payload, self.env_manager.JWT_SECRET, algorithm=self.algorithm)

    async def get_user_id(self, token: str) -> str:
        payload = await self._decode_token(token)
        uid = payload.get("sub")
        if not uid:
            raise ValueError("missing sub claim")
        return uid

    async def _decode_token(self, token: str) -> dict:
        payload = jwt.decode(token, self.env_manager.JWT_SECRET, algorithms=[self.algorithm])
        if await self.redis_manager.get_client().exists(f"jwt:blacklist:{payload['jti']}"):
            raise ValueError("token revoked")
        return payload

    async def logout(self, token: str) -> None:
        payload = await self._decode_token(token)
        ttl     = max(payload["exp"] - int(datetime.now(timezone.utc).timestamp()), 1)
        await self.redis_manager.get_client().set(f"jwt:blacklist:{payload['jti']}", "1", ex=ttl)


@cache
def get_auth_service() -> AuthService:
    config = get_config_manager().get_config("auth", {})
    return AuthService(
        algorithm         = config["jwt"]["algorithm"],
        token_expire_days = config["token_expire_days"],
        allowed_origins   = config.get("allowed_origins", []),
    )
