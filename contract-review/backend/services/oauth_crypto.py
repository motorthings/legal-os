from logger_config import get_logger
logger = get_logger(__name__)

"""
OAuth Token Encryption Service

Provides symmetric encryption/decryption for OAuth tokens using Fernet (AES-128).
Tokens are encrypted before storing in the database and decrypted when retrieved.

Security:
- Uses OAUTH_ENCRYPTION_KEY from environment (32-byte hex = 64 chars)
- Fernet provides authenticated encryption (prevents tampering)
- Tokens are only decrypted in-memory, never logged
"""

import os
import base64
from cryptography.fernet import Fernet
from typing import Optional


class OAuthCryptoError(Exception):
    """Raised when encryption/decryption operations fail"""
    pass


def _get_encryption_key() -> bytes:
    """
    Get the encryption key from environment variable.

    Returns:
        bytes: Fernet-compatible encryption key

    Raises:
        OAuthCryptoError: If key is missing or invalid format
    """
    key_hex = os.getenv("OAUTH_ENCRYPTION_KEY")

    if not key_hex:
        raise OAuthCryptoError(
            "OAUTH_ENCRYPTION_KEY not set in environment. "
            "Generate one with: openssl rand -hex 32"
        )

    if len(key_hex) != 64:  # 32 bytes = 64 hex characters
        raise OAuthCryptoError(
            f"OAUTH_ENCRYPTION_KEY must be 64 hex characters (32 bytes), "
            f"got {len(key_hex)}. Generate with: openssl rand -hex 32"
        )

    try:
        # Convert hex string to bytes, then base64 encode for Fernet
        key_bytes = bytes.fromhex(key_hex)
        # Fernet requires base64-encoded 32-byte key
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return fernet_key
    except ValueError as e:
        raise OAuthCryptoError(f"Invalid OAUTH_ENCRYPTION_KEY format: {e}")


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a plaintext token for storage in the database.

    Args:
        plaintext: The token to encrypt (e.g., access_token, refresh_token)

    Returns:
        str: Base64-encoded encrypted token (safe for database storage)

    Raises:
        OAuthCryptoError: If encryption fails

    Example:
        >>> encrypted = encrypt_token("ya29.a0AfH6SMBx...")
        >>> print(encrypted)  # "gAAAAABf..."
    """
    if not plaintext:
        raise OAuthCryptoError("Cannot encrypt empty token")

    try:
        fernet_key = _get_encryption_key()
        f = Fernet(fernet_key)

        # Encrypt and return as string
        encrypted_bytes = f.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    except Exception as e:
        raise OAuthCryptoError(f"Encryption failed: {e}")


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypt a token retrieved from the database.

    Args:
        ciphertext: The encrypted token from database

    Returns:
        str: Decrypted plaintext token

    Raises:
        OAuthCryptoError: If decryption fails (wrong key, tampered data, etc.)

    Example:
        >>> decrypted = decrypt_token("gAAAAABf...")
        >>> print(decrypted)  # "ya29.a0AfH6SMBx..."
    """
    if not ciphertext:
        raise OAuthCryptoError("Cannot decrypt empty ciphertext")

    try:
        fernet_key = _get_encryption_key()
        f = Fernet(fernet_key)

        # Decrypt and return as string
        decrypted_bytes = f.decrypt(ciphertext.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')

    except Exception as e:
        raise OAuthCryptoError(
            f"Decryption failed: {e}. "
            "This usually means the encryption key changed or data was tampered with."
        )


def rotate_encryption(old_ciphertext: str, new_key_hex: str) -> str:
    """
    Helper function to re-encrypt tokens with a new key.
    Use this if you need to rotate your encryption key.

    Args:
        old_ciphertext: Token encrypted with old key
        new_key_hex: New encryption key (64 hex chars)

    Returns:
        str: Token re-encrypted with new key

    Example:
        >>> new_encrypted = rotate_encryption(old_token, new_key)
    """
    # Decrypt with current key
    plaintext = decrypt_token(old_ciphertext)

    # Temporarily swap in new key
    old_key = os.getenv("OAUTH_ENCRYPTION_KEY")
    os.environ["OAUTH_ENCRYPTION_KEY"] = new_key_hex

    try:
        # Encrypt with new key
        new_ciphertext = encrypt_token(plaintext)
        return new_ciphertext
    finally:
        # Restore old key
        if old_key:
            os.environ["OAUTH_ENCRYPTION_KEY"] = old_key


# Test helper (optional - for development only)
def _test_encryption():
    """
    Quick test to verify encryption/decryption works.
    Run with: python -c "from services.oauth_crypto import _test_encryption; _test_encryption()"
    """
    test_token = "ya29.a0AfH6SMBx_test_token_12345"

    try:
        encrypted = encrypt_token(test_token)
        logger.info(f"✓ Encrypted: {encrypted[:50]}...")

        decrypted = decrypt_token(encrypted)
        assert decrypted == test_token
        logger.info(f"✓ Decrypted: {decrypted[:30]}...")

        print("✓ Encryption test passed!")
        return True
    except Exception as e:
        logger.error(f"✗ Encryption test failed: {e}")
        return False


if __name__ == "__main__":
    _test_encryption()
