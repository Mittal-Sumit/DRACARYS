"""
Helpers for using multiple Groq API keys.

Configuration options:
  - GROQ_API_KEY: primary key
  - GROQ_API_KEY2, GROQ_API_KEY3, ...: ordered fallback keys
  - GROQ_API_KEYS: optional comma-separated list, appended after numbered keys
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv(Path(__file__).parent.parent / ".env")


def get_groq_api_keys() -> list[str]:
    """Return configured Groq keys in fallback order, without blanks or duplicates."""
    candidates: list[str] = []

    primary = os.getenv("GROQ_API_KEY")
    if primary:
        candidates.append(primary)

    index = 2
    while True:
        key = os.getenv(f"GROQ_API_KEY{index}")
        if not key:
            break
        candidates.append(key)
        index += 1

    bulk_keys = os.getenv("GROQ_API_KEYS", "")
    candidates.extend(key.strip() for key in bulk_keys.split(",") if key.strip())

    keys: list[str] = []
    seen: set[str] = set()
    for key in candidates:
        key = key.strip()
        if key and key not in seen:
            keys.append(key)
            seen.add(key)

    return keys


def is_groq_limit_error(exc: Exception) -> bool:
    """Return True for quota, token, or rate-limit errors that should try next key."""
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True

    body = getattr(exc, "body", None)
    message = f"{exc} {body or ''}".lower()
    limit_markers = (
        "rate limit",
        "rate_limit",
        "rate_limit_exceeded",
        "quota",
        "insufficient_quota",
        "token limit",
        "tokens per minute",
        "requests per minute",
    )
    return any(marker in message for marker in limit_markers)
