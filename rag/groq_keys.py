"""
Groq API key pool with rotation support.

Loads up to 3 keys from .env (GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3).
Both crew.py and llm.py import the shared `key_manager` singleton so rotation
state is consistent across the full request — if crew exhausts key 1 and the
fallback pipeline runs, it automatically continues from the current key.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class GroqQuotaExhaustedError(Exception):
    """Raised when all configured Groq API keys have hit their rate or quota limit."""


def get_groq_keys() -> list[str]:
    """Return all configured non-empty Groq API keys in priority order."""
    candidates = [
        os.getenv("GROQ_API_KEY", ""),
        os.getenv("GROQ_API_KEY_2", ""),
        os.getenv("GROQ_API_KEY_3", ""),
        os.getenv("GROQ_API_KEY_4", ""),
    ]
    return [k for k in candidates if k.strip()]


def is_rotatable_error(exc: Exception) -> bool:
    """Return True for Groq errors that rotating to a different key can resolve.

    Covers:
    - 413  Token-per-minute (TPM) limit exceeded — different org key resets the counter
    - 429  Rate limit or daily quota exhausted
    """
    msg = str(exc)
    return (
        "413" in msg
        or "429" in msg
        or "rate_limit_exceeded" in msg.lower()
        or "tokens per" in msg.lower()
        or "token limit" in msg.lower()
        or "quota" in msg.lower()
    )


class GroqKeyManager:
    """Manages a pool of Groq API keys and advances through them on rate-limit errors."""

    def __init__(self) -> None:
        self._keys = get_groq_keys()
        self._index = 0
        if not self._keys:
            raise ValueError("No Groq API keys configured. Set GROQ_API_KEY in .env.")

    @property
    def current(self) -> str:
        return self._keys[self._index]

    @property
    def pool_size(self) -> int:
        return len(self._keys)

    def reset(self) -> None:
        """Call at the start of each top-level request to begin with key 1."""
        self._index = 0

    def rotate(self) -> bool:
        """Advance to the next key. Returns True if a next key exists."""
        if self._index + 1 < len(self._keys):
            self._index += 1
            print(
                f"[GroqKeyManager] Rate-limited — switching to key "
                f"{self._index + 1} of {len(self._keys)}"
            )
            return True
        print("[GroqKeyManager] All API keys exhausted.")
        return False


# Shared singleton — imported by both crew.py and llm.py
key_manager = GroqKeyManager()
