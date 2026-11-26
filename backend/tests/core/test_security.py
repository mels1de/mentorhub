from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.security import generate_token, hash_password, hash_token, verify_password


def test_password_roundtrip() -> None:
    password_hash = hash_password("s3cret-password")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("s3cret-password", password_hash) == (True, None)
    assert verify_password("wrong", password_hash) == (False, None)


def test_missing_user_still_runs_a_hash_and_fails() -> None:
    assert verify_password("anything", None) == (False, None)


def test_outdated_hash_parameters_trigger_a_rehash() -> None:
    weak = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=8 * 1024),)).hash("pw-12345678")

    valid, new_hash = verify_password("pw-12345678", weak)

    assert valid
    assert new_hash is not None
    assert new_hash != weak


def test_tokens_are_random_and_hash_deterministically() -> None:
    first, second = generate_token(), generate_token()

    assert first != second
    assert len(first) >= 43
    assert hash_token(first) == hash_token(first)
    assert hash_token(first) != hash_token(second)
