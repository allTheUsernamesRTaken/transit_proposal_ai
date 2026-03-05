"""
OpenAI chat completion helper for Transit Proposal AI.

Uses configuration from Streamlit secrets (secrets.toml / Secrets UI)
or, as a fallback, from standard environment variables.
"""
from __future__ import annotations

from typing import Optional

from openai import OpenAI

from app.settings import get_required_secret, get_setting


DEFAULT_CHAT_MODEL = get_setting("OPENAI_CHAT_MODEL", "gpt-5.2")


def _get_client(api_key: Optional[str] = None) -> OpenAI:
    key = api_key or get_required_secret("OPENAI_API_KEY")
    return OpenAI(api_key=key)


def call_openai(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str = DEFAULT_CHAT_MODEL,
    max_completion_tokens: int = 2048,
    api_key: Optional[str] = None,
) -> str:
    """
    Call OpenAI chat completions (GPT-5.2 or another specified model)
    with system + user message.

    This is the single entry point for extractor, clarifier, and drafter.
    """
    client = _get_client(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content
    return (text or "").strip()
