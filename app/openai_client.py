"""
OpenAI chat completion helper for Transit Proposal AI.
Uses OPENAI_API_KEY from the environment (same key as for embeddings).
"""
from __future__ import annotations

import os
from typing import Optional

from openai import OpenAI


DEFAULT_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def _get_client(api_key: Optional[str] = None) -> OpenAI:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=key)


def call_openai(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str = DEFAULT_CHAT_MODEL,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
) -> str:
    """
    Call OpenAI chat completions (e.g. GPT-4o-mini) with system + user message.
    Single entry point for extractor, clarifier, and drafter.
    """
    client = _get_client(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    text = response.choices[0].message.content
    return (text or "").strip()
