"""Authentication and pairing management for Flash Agent.

Provides secure device pairing over local Wi-Fi, short-lived pairing codes,
revocable bearer tokens, and WebSocket connection authorization.
"""

import secrets
import time
from typing import Optional
from pydantic import BaseModel, Field

from app.logging_config import get_logger

logger = get_logger("flash.auth")


class PairingCode(BaseModel):
    """Model representing an active pairing code."""
    code: str
    expires_at: float
    created_at: float = Field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class ClientToken(BaseModel):
    """Authorized client authentication token."""
    token: str
    client_name: str
    created_at: float = Field(default_factory=time.time)
    last_used_at: float = Field(default_factory=time.time)
    revoked: bool = False


class PairingManager:
    """Manages short-lived, one-time pairing codes for phone connection."""

    def __init__(self, code_ttl_seconds: int = 300) -> None:
        self.code_ttl_seconds = code_ttl_seconds
        self._active_codes: dict[str, PairingCode] = {}

    def generate_code(self) -> str:
        """Generate a cryptographically random 6-digit pairing code."""
        # 6-digit random code formatted as "123-456" for readability
        raw_code = f"{secrets.randbelow(900000) + 100000}"
        formatted_code = f"{raw_code[:3]}-{raw_code[3:]}"
        expires_at = time.time() + self.code_ttl_seconds

        # Clean expired codes
        self._purge_expired()

        self._active_codes[raw_code] = PairingCode(code=formatted_code, expires_at=expires_at)
        logger.info(
            "Generated new pairing code: %s (expires in %ds)",
            formatted_code,
            self.code_ttl_seconds,
        )
        return formatted_code

    def verify_and_consume(self, code_input: str) -> bool:
        """Verify code and consume it if valid. Handles formatted or raw input."""
        clean_code = code_input.replace("-", "").strip()
        self._purge_expired()

        if clean_code in self._active_codes:
            pairing = self._active_codes[clean_code]
            if not pairing.is_expired:
                del self._active_codes[clean_code]
                logger.info("Pairing code verified and consumed successfully.")
                return True
            del self._active_codes[clean_code]

        logger.warning("Pairing attempt failed for code: %s", code_input)
        return False

    def get_latest_code(self) -> Optional[str]:
        """Return currently valid pairing code if one exists."""
        self._purge_expired()
        for p in self._active_codes.values():
            if not p.is_expired:
                return p.code
        return None

    def get_or_create_code_info(self) -> tuple[str, int, float]:
        """Return (code, remaining_seconds, expires_at) for current active code, creating one if needed."""
        self._purge_expired()
        now = time.time()
        for p in self._active_codes.values():
            if not p.is_expired:
                return p.code, max(0, int(p.expires_at - now)), p.expires_at
        code = self.generate_code()
        for p in self._active_codes.values():
            if not p.is_expired:
                return p.code, max(0, int(p.expires_at - now)), p.expires_at
        return code, self.code_ttl_seconds, now + self.code_ttl_seconds


    def _purge_expired(self) -> None:
        """Remove expired pairing codes."""
        now = time.time()
        expired = [k for k, v in self._active_codes.items() if now > v.expires_at]
        for k in expired:
            del self._active_codes[k]


class TokenManager:
    """Manages revocable bearer tokens for paired phone companion clients."""

    def __init__(self, persist_to_disk: bool = True) -> None:
        self.persist_to_disk = persist_to_disk
        self._tokens: dict[str, ClientToken] = {}
        if self.persist_to_disk:
            self._load_tokens()

    def clear(self) -> None:
        """Clear all active tokens."""
        self._tokens.clear()

    def _get_storage_path(self) -> Optional[str]:
        if not self.persist_to_disk:
            return None
        try:
            import os
            from app.config import settings
            root = settings.storage_base_dir if settings.storage_base_dir else str(settings.workspace_dir)
            base_dir = os.path.join(root, "data")
            os.makedirs(base_dir, exist_ok=True)
            return os.path.join(base_dir, "auth_tokens.json")
        except Exception:
            return None

    def _save_tokens(self) -> None:
        path = self._get_storage_path()
        if not path:
            return
        try:
            import json
            data = {t: obj.model_dump() for t, obj in self._tokens.items()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug("Could not save tokens to disk: %s", e)

    def _load_tokens(self) -> None:
        path = self._get_storage_path()
        if not path:
            return
        try:
            import os, json
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for t, obj in data.items():
                    if t not in self._tokens:
                        self._tokens[t] = ClientToken(**obj)
        except Exception as e:
            logger.debug("Could not load tokens from disk: %s", e)

    def issue_token(self, client_name: str = "Android Companion") -> str:
        """Generate and store a new 256-bit cryptographically secure token."""
        raw_token = secrets.token_hex(32)
        self._tokens[raw_token] = ClientToken(
            token=raw_token,
            client_name=client_name,
        )
        self._save_tokens()
        logger.info("Issued new auth token for client: '%s'", client_name)
        return raw_token

    def validate_token(self, token: Optional[str]) -> bool:
        """Check if token is valid, active, and not revoked."""
        if not token:
            return False
        if token not in self._tokens:
            self._load_tokens()
        client_token = self._tokens.get(token)
        if client_token and not client_token.revoked:
            client_token.last_used_at = time.time()
            return True
        return False

    def revoke_token(self, token: str) -> bool:
        """Revoke an active token immediately."""
        client_token = self._tokens.get(token)
        if client_token and not client_token.revoked:
            client_token.revoked = True
            self._save_tokens()
            logger.info("Revoked auth token for client: '%s'", client_token.client_name)
            return True
        return False

    def list_tokens(self) -> list[dict]:
        """Return catalog of issued tokens (with secret masked)."""
        return [
            {
                "client_name": t.client_name,
                "token_prefix": t.token[:8] + "...",
                "created_at": t.created_at,
                "last_used_at": t.last_used_at,
                "revoked": t.revoked,
            }
            for t in self._tokens.values()
        ]


# Global singletons
pairing_manager = PairingManager()
token_manager = TokenManager()
