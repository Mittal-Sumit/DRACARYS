"""
Groq LLM client.
Reads GROQ_API_KEY from the root .env file.
Returns a structured dict (Task 8 — structured output).
"""

import json
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent.parent / ".env")

def get_groq_client():
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    return Groq(api_key=api_key)


def generate(
    query: str,
    context_chunks: list[dict],
    model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature: float = 0.5,
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
    from rag.prompts import SYSTEM_PROMPT, build_user_message

    client = get_groq_client()
    user_message = build_user_message(query, context_chunks)

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        if "sections" not in parsed:
            # LLM returned old 4-key format or unexpected shape — wrap it
            text = " ".join(str(v) for v in parsed.values() if v)
            return {"sections": [{"heading": None, "content": text or content}]}
        return parsed
    except json.JSONDecodeError:
        return {"sections": [{"heading": None, "content": content}]}
