from __future__ import annotations

from typing import List

from openai import OpenAI

from app.settings import get_required_secret


EMBEDDING_MODEL = "text-embedding-3-small"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = get_required_secret("OPENAI_API_KEY")
        _client = OpenAI(api_key=api_key)
    return _client


def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text using OpenAI.
    """
    if not text:
        return []

    client = _get_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return list(response.data[0].embedding)

