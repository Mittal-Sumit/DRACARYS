"""
Gemini LLM client — simple fallback pipeline.
Uses the shared GeminiKeyManager so rotation is consistent with the crew pipeline.
"""

import json
import os
from pathlib import Path

import litellm
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-2.5-flash")


def generate(
    query: str,
    context_chunks: list[dict],
    model: str = None,
    temperature: float = 0.5,
) -> dict:
    """
    Send query + retrieved chunks to Gemini and return a structured proposal dict.
    Rotates through available API keys on rate-limit or quota errors.
    """
    from rag.prompts import SYSTEM_PROMPT, build_user_message
    from rag.gemini_keys import GeminiQuotaExhaustedError, is_rotatable_error, key_manager

    model = model or _GEMINI_MODEL
    user_message = build_user_message(query, context_chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    while True:
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                api_key=key_manager.current,
                response_format={"type": "json_object"},
            )
            break
        except Exception as exc:
            if is_rotatable_error(exc):
                if key_manager.rotate():
                    continue
                raise GeminiQuotaExhaustedError(
                    f"All {key_manager.pool_size} Gemini API key(s) have hit their rate or quota limit. "
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
