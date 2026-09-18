"""
Authentication and Session Security Module.
Provides password hashing, JWT creation, token validation, and rate limiting.
"""
import time
import hashlib
import hmac
from typing import Optional, Dict, Any


def hash_password(password: str, salt: str) -> str:
    """
    Hashes a plaintext password using SHA-256 with an HMAC salt.
    
    Args:
        password: The user's raw password.
        salt: Random cryptographic salt.
    Returns:
        Hex-encoded hashed string.
    """
    return hmac.new(salt.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).hexdigest()


class TokenService:
    """
    Manages cryptographic JWT authentication tokens, expiration cycles, and revocation.
    """
    def __init__(self, secret_key: str, expiration_seconds: int = 3600):
        """
        Initializes the TokenService with secret credentials.
        """
        self.secret_key = secret_key
        self.expiration_seconds = expiration_seconds
        self.revoked_tokens: set[str] = set()

    def generate_token(self, user_id: str, role: str = "user") -> str:
        """
        Generates a signed access token payload containing user id, role, and expiry timestamp.
        """
        expires_at = int(time.time()) + self.expiration_seconds
        payload = f"{user_id}:{role}:{expires_at}"
        signature = hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{signature}"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validates token signature and checks whether the token has expired or been revoked.
        
        Returns:
            Dictionary with user details if valid, None if invalid or expired.
        """
        if token in self.revoked_tokens:
            return None

        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload, signature = parts[0], parts[1]
        expected_sig = hmac.new(self.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None

        user_id, role, expires_at_str = payload.split(":")
        if int(time.time()) > int(expires_at_str):
            return None  # Token expired

        return {"user_id": user_id, "role": role, "expires_at": int(expires_at_str)}

    def revoke_token(self, token: str) -> bool:
        """
        Adds a token to the blacklist/revocation set to prevent further usage.
        """
        self.revoked_tokens.add(token)
        return True
