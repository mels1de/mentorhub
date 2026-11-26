import uuid
from datetime import timedelta

import pytest
from redis.asyncio import Redis

from app.modules.auth.exceptions import InvalidOtpError, OtpLockedError
from app.modules.auth.otp import MAX_SENDS, OtpPolicy, OtpStore

pytestmark = pytest.mark.integration

USER_ID = uuid.uuid7()
POLICY = OtpPolicy(ttl=timedelta(minutes=10), max_attempts=3, lockout=timedelta(minutes=15))


@pytest.fixture
def store(redis: Redis) -> OtpStore:
    return OtpStore(redis, "test-secret", POLICY)


async def issue(store: OtpStore) -> tuple[str, str]:
    challenge_id = await store.create_challenge(USER_ID)
    issued = await store.issue_code(challenge_id)
    assert issued is not None
    assert issued[0] == USER_ID
    return challenge_id, issued[1]


def wrong(code: str) -> str:
    return f"{(int(code) + 1) % 10**6:06d}"


async def test_correct_code_passes_once(store: OtpStore) -> None:
    challenge_id, code = await issue(store)

    assert len(code) == 6
    assert code.isdigit()
    assert await store.verify(challenge_id, code) == USER_ID
    with pytest.raises(InvalidOtpError):
        await store.verify(challenge_id, code)


async def test_code_is_not_stored_in_plain_text(store: OtpStore, redis: Redis) -> None:
    challenge_id, code = await issue(store)

    stored = await redis.hgetall(f"auth:otp:{challenge_id}")

    assert code not in stored.values()
    assert 0 < await redis.ttl(f"auth:otp:{challenge_id}") <= 600


async def test_wrong_code_reports_attempts_left(store: OtpStore) -> None:
    challenge_id, code = await issue(store)

    with pytest.raises(InvalidOtpError) as error:
        await store.verify(challenge_id, wrong(code))

    assert error.value.extensions == {"attempts_left": 2}


async def test_too_many_wrong_codes_lock_the_user_out(store: OtpStore) -> None:
    challenge_id, code = await issue(store)
    for _ in range(POLICY.max_attempts - 1):
        with pytest.raises(InvalidOtpError):
            await store.verify(challenge_id, wrong(code))

    with pytest.raises(OtpLockedError) as error:
        await store.verify(challenge_id, wrong(code))

    assert error.value.headers["Retry-After"] == "900"
    # The challenge is gone and a new login can't start a new one during the lockout.
    with pytest.raises(InvalidOtpError):
        await store.verify(challenge_id, code)
    with pytest.raises(OtpLockedError):
        await store.create_challenge(USER_ID)


async def test_resend_replaces_the_code_but_keeps_attempts(store: OtpStore) -> None:
    challenge_id, first = await issue(store)
    with pytest.raises(InvalidOtpError):
        await store.verify(challenge_id, wrong(first))

    issued = await store.issue_code(challenge_id)
    assert issued is not None
    second = issued[1]

    if first != second:
        with pytest.raises(InvalidOtpError) as error:
            await store.verify(challenge_id, first)
        assert error.value.extensions == {"attempts_left": 1}
    assert await store.verify(challenge_id, second) == USER_ID


async def test_resends_are_capped(store: OtpStore) -> None:
    challenge_id = await store.create_challenge(USER_ID)

    results = [await store.issue_code(challenge_id) for _ in range(MAX_SENDS + 1)]

    assert all(r is not None for r in results[:MAX_SENDS])
    assert results[MAX_SENDS] is None


async def test_unknown_challenge(store: OtpStore) -> None:
    assert await store.issue_code("missing") is None
    with pytest.raises(InvalidOtpError):
        await store.verify("missing", "123456")


async def test_codes_from_another_secret_do_not_match(store: OtpStore, redis: Redis) -> None:
    challenge_id, code = await issue(store)
    other = OtpStore(redis, "another-secret", POLICY)

    with pytest.raises(InvalidOtpError):
        await other.verify(challenge_id, code)
