"""
Groq LLM client — simple fallback pipeline.
Uses the shared GroqKeyManager so key rotation is consistent with the crew pipeline.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _make_client(api_key: str):
    from groq import Groq
    return Groq(api_key=api_key)


def generate(
    query: str,
    context_chunks: list[dict],
    model: str = _GROQ_MODEL,
    temperature: float = 0.5,
) -> dict:
    """
    Send query + retrieved chunks to Groq and return a structured proposal dict.
    Rotates through available API keys on rate-limit or quota errors.
    """
    from rag.prompts import SYSTEM_PROMPT, build_user_message
    from rag.groq_keys import GroqQuotaExhaustedError, is_rotatable_error, key_manager

    user_message = build_user_message(query, context_chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    # key_manager index is already set by run_crew (rotated to the first working key).
    # Try remaining keys in sequence if this one is also rate-limited.
    while True:
        try:
            client = _make_client(key_manager.current)
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=messages,
            )
            break
        except Exception as exc:
            if is_rotatable_error(exc):
                if key_manager.rotate():
                    continue
                raise GroqQuotaExhaustedError(
                    f"All {key_manager.pool_size} Groq API key(s) have hit their rate or quota limit. "
                    "Please try again in a few minutes."
                ) from exc
            raise

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        if "sections" not in parsed:
            text = " ".join(str(v) for v in parsed.values() if v)
            return {"sections": [{"heading": None, "content": text or content}]}
        return parsed
    except json.JSONDecodeError:
        return {"sections": [{"heading": None, "content": content}]}
