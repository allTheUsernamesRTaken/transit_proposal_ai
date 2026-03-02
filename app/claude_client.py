from __future__ import annotations

import os
from typing import Optional

import anthropic


DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20241022"


def _get_client(api_key: Optional[str] = None) -> anthropic.Anthropic:
    """
    Lazily construct an Anthropic client.
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=key)


def call_claude(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str = DEFAULT_CLAUDE_MODEL,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
) -> str:
    """
    Simple, reusable helper for calling Claude.

    This function is intentionally minimal so that higher-level modules
    (extractor, clarifier, estimator, etc.) can depend on a single entry point
    without worrying about client configuration.
    """
    client = _get_client(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
    )

    parts: list[str] = []
    for item in response.content:
        if getattr(item, "type", None) == "text":
            parts.append(item.text)

    return "".join(parts).strip()

