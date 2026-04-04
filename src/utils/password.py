import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a plaintext password for storage using bcrypt.

    Encodes the password as UTF-8 bytes, generates a new random salt with
    ``bcrypt.gensalt()`` (default cost factor), and computes the bcrypt hash. The
    result is decoded back to a Unicode string suitable for persistence in a
    VARCHAR/TEXT column. This is a one-way function: verification must use
    ``bcrypt.checkpw`` with the stored hash and a candidate password, not string
    comparison of hashes across different salts.

    Args:
        password: Raw user password as provided at registration or change-password time.

    Returns:
        The bcrypt hash string (includes salt and algorithm metadata) to store in
        ``password_hash``.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash in constant time.

    Delegates to ``bcrypt.checkpw``, which compares the candidate password to the hash
    using a timing-safe implementation appropriate for authentication checks.

    Args:
        plain_password: Password supplied at login or similar.
        password_hash: Value previously stored from ``hash_password``.

    Returns:
        ``True`` if the password matches; ``False`` otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )
