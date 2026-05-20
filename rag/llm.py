"""
Groq LLM client.
Reads GROQ_API_KEY from the root .env file.
"""

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
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.3,
) -> str:
    """
    Send query + retrieved chunks to Groq and return the generated proposal text.

    Args:
        query:          The client request / user question
        context_chunks: Output from retriever.retrieve()
        model:          Groq model ID
        temperature:    Lower = more factual and consistent (recommended for proposals)

    Returns:
        Generated proposal as a string.
    """
    from rag.prompts import SYSTEM_PROMPT, build_user_message

    client = get_groq_client()
    user_message = build_user_message(query, context_chunks)

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return response.choices[0].message.content
