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
