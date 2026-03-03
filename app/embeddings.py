from __future__ import annotations

import os
from typing import List

from openai import OpenAI


_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text using OpenAI.
    """
    if not text:
        return []

    response = _client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )

    return list(response.data[0].embedding)

