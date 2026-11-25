"""Hashowanie PIN-u nauczyciela (argon2, z awaryjnym PBKDF2)."""

from __future__ import annotations

import hashlib
import hmac
import os

try:  # pragma: no cover - zależy od środowiska
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    _hasher: PasswordHasher | None = PasswordHasher()
except Exception:  # noqa: BLE001  # pragma: no cover
    _hasher = None
    VerifyMismatchError = Exception  # type: ignore[assignment, misc]

PBKDF2_ROUNDS = 240_000


def hash_pin(pin: str) -> str:
    if _hasher is not None:
        return _hasher.hash(pin)
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, PBKDF2_ROUNDS)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_pin(pin: str, stored: str) -> bool:
    if not stored:
        return False
    if stored.startswith("pbkdf2$"):
        _, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt_hex), PBKDF2_ROUNDS)
        return hmac.compare_digest(digest.hex(), digest_hex)
    if _hasher is None:  # pragma: no cover
        return False
    try:
        return _hasher.verify(stored, pin)
    except Exception:  # noqa: BLE001
        return False
