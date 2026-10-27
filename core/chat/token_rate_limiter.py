import asyncio
from datetime import datetime, timezone
from functools import cache
from core.store.redis.redis_manager import get_redis_manager

TOKEN_RESERVE_SCRIPT = """
local hourly  = tonumber(redis.call('GET', KEYS[1]) or '0')
local daily   = tonumber(redis.call('GET', KEYS[2]) or '0')
local reserve = tonumber(ARGV[1])

if hourly + reserve > tonumber(ARGV[2]) then return -1 end
if daily  + reserve > tonumber(ARGV[3]) then return -2 end

local hourly_new = redis.call('INCRBY', KEYS[1], reserve)
if hourly_new == reserve then redis.call('EXPIRE', KEYS[1], ARGV[4]) end
local daily_new = redis.call('INCRBY', KEYS[2], reserve)
if daily_new == reserve then redis.call('EXPIRE', KEYS[2], ARGV[5]) end
return 1
"""


class HourlyRateLimitExceeded(Exception):
    pass


class DailyRateLimitExceeded(Exception):
    pass


class TokenRateLimiter:
    def __init__(self, redis_manager) -> None:
        self.redis_manager = redis_manager

    async def reserve(self, user_id: str, tokens: int, max_tokens_per_hour: int, max_tokens_per_day: int) -> tuple:
        now        = datetime.now(timezone.utc)
        hourly_key = f"ratelimit:tokens:{user_id}:{now.strftime('%Y%m%d%H')}"
        daily_key  = f"ratelimit:tokens:{user_id}:{now.strftime('%Y%m%d')}"
        result     = await self.redis_manager.get_client().eval(
            TOKEN_RESERVE_SCRIPT,
            2,
            hourly_key,
            daily_key,
            tokens,
            max_tokens_per_hour,
            max_tokens_per_day,
            7200,
            172800,
        )
        if result == -1:
            raise HourlyRateLimitExceeded()
        if result == -2:
            raise DailyRateLimitExceeded()
        return hourly_key, daily_key

    async def correct(self, keys: tuple, reserved: int, actual: int) -> None:
        delta = actual - reserved
        if delta == 0:
            return

        hourly_key, daily_key = keys
        client = self.redis_manager.get_client()
        await asyncio.gather(
            client.incrby(hourly_key, delta),
            client.incrby(daily_key, delta),
        )


@cache
def get_token_rate_limiter() -> TokenRateLimiter:
    return TokenRateLimiter(redis_manager=get_redis_manager())
