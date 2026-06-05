"""
Groq LLM client.
Reads Groq API keys from the root .env file.
Returns a structured dict (Task 8 — structured output).
"""

import json
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent / ".env")

from rag.groq_keys import get_groq_api_keys, is_groq_limit_error


def get_groq_client(api_key: str | None = None):
    from groq import Groq

    if api_key is None:
        keys = get_groq_api_keys()
        api_key = keys[0] if keys else None
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    return Groq(api_key=api_key)


def generate(
    query: str,
    context_chunks: list[dict],
    model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature: float = 0.5,
    tone: str = "balanced",
    use_web_search: bool = False,
    output_format: str = "proposal",
    conversation_context: str = "",
) -> dict:
    """
    Send query + retrieved chunks to Groq and return a structured proposal dict.

    Returns:
        {
            "executive_summary": "...",
            "proposed_solution": "...",
            "relevant_experience": "...",
            "why_us": "..."
        }
    """
    from rag.prompts import build_system_prompt, build_user_message

    system_prompt = build_system_prompt(tone, use_web_search, output_format)
    user_message = build_user_message(query, context_chunks)
    if conversation_context:
        user_message = f"CONVERSATION HISTORY:\n{conversation_context}\n\n{user_message}"

    keys = get_groq_api_keys()
    if not keys:
        raise ValueError("GROQ_API_KEY not found in .env file")

    last_limit_error: Exception | None = None
    for api_key in keys:
        client = get_groq_client(api_key)
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            break
        except Exception as exc:
            if not is_groq_limit_error(exc):
                raise
            last_limit_error = exc
    else:
        raise RuntimeError("All configured Groq API keys are exhausted or rate-limited.") from last_limit_error

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        if output_format == "email":
            if "subject" in parsed or "body" in parsed:
                return parsed
            text = " ".join(str(v) for v in parsed.values() if v)
            return {"subject": "Outreach Email", "body": text or content}

        if "sections" not in parsed:
            # LLM returned old 4-key format or unexpected shape — wrap it
            text = " ".join(str(v) for v in parsed.values() if v)
            return {"sections": [{"heading": None, "content": text or content}]}
        return parsed
    except json.JSONDecodeError:
        if output_format == "email":
            return {"subject": "Outreach Email", "body": content}
        return {"sections": [{"heading": None, "content": content}]}
