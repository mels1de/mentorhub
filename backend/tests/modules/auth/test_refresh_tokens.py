import asyncio
import uuid
from datetime import timedelta

import pytest
from redis.asyncio import Redis

from app.modules.auth.exceptions import InvalidTokenError, RefreshTokenReusedError
from app.modules.auth.refresh_tokens import RefreshTokenStore, RotatedToken

pytestmark = pytest.mark.integration

USER_ID = uuid.uuid7()
TTL = timedelta(days=7)


@pytest.fixture
def store(redis: Redis) -> RefreshTokenStore:
    # No grace period, so reuse is detected without waiting in the test.
    return RefreshTokenStore(redis, TTL, reuse_grace=timedelta(0))


async def test_rotation_returns_a_new_token_for_the_same_user(store: RefreshTokenStore) -> None:
    token = await store.issue(USER_ID)

    rotated = await store.rotate(token)

    assert rotated.user_id == USER_ID
    assert rotated.token != token
    assert (await store.rotate(rotated.token)).user_id == USER_ID


async def test_only_the_hash_is_stored(store: RefreshTokenStore, redis: Redis) -> None:
    token = await store.issue(USER_ID)

    keys = [key async for key in redis.scan_iter("auth:*")]

    assert keys
    assert not any(token in key for key in keys)
    ttl = await redis.ttl(next(k for k in keys if k.startswith("auth:rt:")))
    assert 0 < ttl <= TTL.total_seconds()


async def test_unknown_token_is_rejected(store: RefreshTokenStore) -> None:
    with pytest.raises(InvalidTokenError):
        await store.rotate("never-issued")


async def test_reuse_revokes_the_whole_family(store: RefreshTokenStore) -> None:
    stolen = await store.issue(USER_ID)
    current = (await store.rotate(stolen)).token

    with pytest.raises(RefreshTokenReusedError):
        await store.rotate(stolen)
    # The legitimate client's newer token died with the family.
    with pytest.raises(InvalidTokenError):
        await store.rotate(current)


async def test_reuse_does_not_touch_other_logins(store: RefreshTokenStore) -> None:
    laptop = await store.issue(USER_ID)
    phone = await store.issue(USER_ID)
    await store.rotate(laptop)

    with pytest.raises(RefreshTokenReusedError):
        await store.rotate(laptop)

    assert (await store.rotate(phone)).user_id == USER_ID


async def test_concurrent_refreshes_let_one_win_without_revoking(redis: Redis) -> None:
    store = RefreshTokenStore(redis, TTL)
    token = await store.issue(USER_ID)

    results = await asyncio.gather(*(store.rotate(token) for _ in range(5)), return_exceptions=True)

    winners = [r for r in results if isinstance(r, RotatedToken)]
    losers = [r for r in results if not isinstance(r, RotatedToken)]
    assert len(winners) == 1
    assert all(type(r) is InvalidTokenError for r in losers)
    assert (await store.rotate(winners[0].token)).user_id == USER_ID


async def test_revoke_ends_only_that_login(store: RefreshTokenStore) -> None:
    laptop = await store.issue(USER_ID)
    phone = await store.issue(USER_ID)

    await store.revoke(laptop)

    with pytest.raises(InvalidTokenError):
        await store.rotate(laptop)
    assert (await store.rotate(phone)).user_id == USER_ID


async def test_revoke_all_ends_every_login(store: RefreshTokenStore) -> None:
    tokens = [await store.issue(USER_ID) for _ in range(3)]
    other_user = await store.issue(uuid.uuid7())

    await store.revoke_all(USER_ID)

    for token in tokens:
        with pytest.raises(InvalidTokenError):
            await store.rotate(token)
    await store.rotate(other_user)


async def test_revoke_is_idempotent(store: RefreshTokenStore) -> None:
    await store.revoke("never-issued")
