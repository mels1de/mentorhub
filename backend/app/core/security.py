import hashlib
import secrets

from pwdlib import PasswordHash

# Argon2id with pwdlib's recommended parameters.
_password_hash = PasswordHash.recommended()

# Verified against when the user does not exist, so a login for an unknown email takes as long
# as one for a known email (no user enumeration by timing).
_DUMMY_HASH = _password_hash.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> tuple[bool, str | None]:
    """Return (valid, new_hash); new_hash is set when the stored hash uses outdated parameters."""
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False, None
    return _password_hash.verify_and_update(password, password_hash)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # Tokens are 256-bit random values, so a fast unsalted hash is enough (unlike passwords).
    return hashlib.sha256(token.encode()).hexdigest()
