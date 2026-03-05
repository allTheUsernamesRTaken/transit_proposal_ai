from __future__ import annotations

from typing import Optional

from .openai_client import DEFAULT_CHAT_MODEL, call_openai


DEFAULT_CHATGPT_MODEL = DEFAULT_CHAT_MODEL


def call_chatgpt(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    model: str = DEFAULT_CHATGPT_MODEL,
    max_completion_tokens: int = 2048,
    api_key: Optional[str] = None,
) -> str:
    """
    ChatGPT (OpenAI) chat completion helper.

    Defaults to GPT-5.2 via OPENAI_CHAT_MODEL, and uses OPENAI_API_KEY.
    """
    return call_openai(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        model=model,
        max_completion_tokens=max_completion_tokens,
        api_key=api_key,
    )

