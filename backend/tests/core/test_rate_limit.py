from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.dependencies import get_app_settings
from app.core.exceptions import TooManyRequestsError
from app.core.rate_limit import RateLimiter, anonymized

pytestmark = pytest.mark.integration


async def test_allows_up_to_the_limit_then_rejects(redis: Redis) -> None:
    limiter = RateLimiter(redis)
    for _ in range(3):
        await limiter.hit("k", limit=3, window=timedelta(minutes=1))

    with pytest.raises(TooManyRequestsError) as error:
        await limiter.hit("k", limit=3, window=timedelta(minutes=1))

    assert 0 < int(error.value.headers["Retry-After"]) <= 60


async def test_later_hits_do_not_extend_the_window(redis: Redis) -> None:
    limiter = RateLimiter(redis)
    await limiter.hit("k", limit=10, window=timedelta(seconds=30))
    await redis.expire("rl:k", 5)

    await limiter.hit("k", limit=10, window=timedelta(seconds=30))

    assert await redis.ttl("rl:k") <= 5


async def test_keys_are_independent(redis: Redis) -> None:
    limiter = RateLimiter(redis)
    await limiter.hit("a", limit=1, window=timedelta(minutes=1))

    await limiter.hit("b", limit=1, window=timedelta(minutes=1))


def test_anonymized_keys_ignore_case_and_hide_the_value() -> None:
    assert anonymized("User@Example.com ") == anonymized("user@example.com")
    assert "example" not in anonymized("user@example.com")


async def test_login_is_limited_per_ip(api: AsyncClient) -> None:
    payload = {"email": "nobody@example.com", "password": "whatever-password"}
    statuses = [(await api.post("/api/v1/auth/login", json=payload)).status_code for _ in range(11)]

    assert statuses == [401] * 10 + [429]
    last = await api.post("/api/v1/auth/login", json=payload)
    assert last.json()["code"] == "rate_limited"
    assert last.headers["content-type"] == "application/problem+json"
    assert int(last.headers["retry-after"]) > 0


async def test_login_is_limited_per_account_across_ips(api: AsyncClient, redis: Redis) -> None:
    payload = {"email": "victim@example.com", "password": "guess"}
    statuses = []
    for _ in range(21):
        # Reset the per-IP counter: as if every guess came from a different address.
        await redis.delete("rl:login:ip:127.0.0.1")
        statuses.append((await api.post("/api/v1/auth/login", json=payload)).status_code)

    assert statuses == [401] * 20 + [429]


async def test_limits_can_be_switched_off(
    api: AsyncClient, app: FastAPI, settings: Settings
) -> None:
    disabled = settings.model_copy(update={"rate_limit_enabled": False})
    app.dependency_overrides[get_app_settings] = lambda: disabled
    payload = {"email": "nobody@example.com", "password": "whatever-password"}

    statuses = [(await api.post("/api/v1/auth/login", json=payload)).status_code for _ in range(12)]

    assert set(statuses) == {401}
