import hashlib


def hash_plaintext(plaintext: str) -> str:
    """
    Hashes a plaintext string using SHA-256.
    """
    return hashlib.sha256(plaintext.encode()).hexdigest()


def verify_password(plaintext: str, hashed: str) -> bool:
    """
    Verifies a plaintext password against a hashed password.
    """
    return hash_plaintext(plaintext) == hashed
