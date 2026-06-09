"""
Gemini API key pool with rotation support.

Loads up to 3 keys from .env (GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3).
Both crew.py and llm.py import the shared `key_manager` singleton so rotation
state is consistent across the full request.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class GeminiQuotaExhaustedError(Exception):
    """Raised when all configured Gemini API keys have hit their rate or quota limit."""


def get_gemini_keys() -> list[str]:
    """Return all configured non-empty Gemini API keys in priority order."""
    candidates = [
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GEMINI_API_KEY_2", ""),
        os.getenv("GEMINI_API_KEY_3", ""),
    ]
    return [k for k in candidates if k.strip()]


def is_rotatable_error(exc: Exception) -> bool:
    """Return True for Gemini errors that rotating to a different key can resolve.

    Covers:
    - 429  Rate limit or quota exhausted
    - RESOURCE_EXHAUSTED  Google's gRPC status for quota errors
    """
    msg = str(exc).lower()
    return (
        "429" in msg
        or "rate_limit" in msg
        or "quota" in msg
        or "resource_exhausted" in msg
        or "too many requests" in msg
    )


class GeminiKeyManager:
    """Manages a pool of Gemini API keys and advances through them on rate-limit errors."""

    def __init__(self) -> None:
        self._keys = get_gemini_keys()
        self._index = 0
        if not self._keys:
            raise ValueError("No Gemini API keys configured. Set GEMINI_API_KEY in .env.")

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
                f"[GeminiKeyManager] Rate-limited — switching to key "
                f"{self._index + 1} of {len(self._keys)}"
            )
            return True
        print("[GeminiKeyManager] All Gemini API keys exhausted.")
        return False


# Shared singleton — imported by both crew.py and llm.py
key_manager = GeminiKeyManager()
