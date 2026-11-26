import uuid
from datetime import timedelta

import pytest
from redis.asyncio import Redis

from app.modules.auth.exceptions import InvalidLinkError
from app.modules.auth.one_time_tokens import OneTimeTokenStore, TokenPurpose

pytestmark = pytest.mark.integration

USER_ID = uuid.uuid7()


@pytest.fixture
def store(redis: Redis) -> OneTimeTokenStore:
    return OneTimeTokenStore(redis, TokenPurpose.RESET_PASSWORD, timedelta(minutes=30))


async def test_token_works_exactly_once(store: OneTimeTokenStore) -> None:
    token = await store.issue(USER_ID)

    assert await store.consume(token) == USER_ID
    with pytest.raises(InvalidLinkError):
        await store.consume(token)


async def test_a_new_link_invalidates_the_previous_one(store: OneTimeTokenStore) -> None:
    old = await store.issue(USER_ID)
    new = await store.issue(USER_ID)

    with pytest.raises(InvalidLinkError):
        await store.consume(old)
    assert await store.consume(new) == USER_ID


async def test_purposes_do_not_mix(store: OneTimeTokenStore, redis: Redis) -> None:
    verify = OneTimeTokenStore(redis, TokenPurpose.VERIFY_EMAIL, timedelta(hours=24))
    reset_token = await store.issue(USER_ID)

    with pytest.raises(InvalidLinkError):
        await verify.consume(reset_token)


async def test_tokens_expire(store: OneTimeTokenStore, redis: Redis) -> None:
    await store.issue(USER_ID)

    ttls = [await redis.ttl(key) async for key in redis.scan_iter("auth:reset:*")]

    assert ttls
    assert all(0 < ttl <= 30 * 60 for ttl in ttls)
