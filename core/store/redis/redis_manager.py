import redis.asyncio as aioredis
from functools import cache
from core.config.env_manager import get_env_manager
from core.logger.logger_manager import get_logger_manager


class RedisManager:
    def __init__(self, url: str) -> None:
        self.logger  = get_logger_manager().get_logger(self.__class__.__name__)
        self.url     = url
        self._client: aioredis.Redis | None = None

    async def startup(self) -> None:
        self._client = aioredis.from_url(
            self.url,
            decode_responses=True,
            health_check_interval=10,
            socket_timeout=None,
            socket_connect_timeout=5,
        )
        await self._client.ping()
        self.logger.info("RedisManager initialized")

    async def cleanup(self) -> None:
        if self._client:
            await self._client.aclose()
            self.logger.info("RedisManager resources cleaned up")

    def get_client(self) -> aioredis.Redis:
        return self._client


@cache
def get_redis_manager() -> RedisManager:
    return RedisManager(url=get_env_manager().REDIS_URL)
