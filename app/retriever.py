from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Document, SessionLocal
from .embeddings import get_embedding


def add_document(
    title: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Document:
    """
    Insert a new document and its embedding into the database.
    """
    embedding = get_embedding(content)

    with SessionLocal() as session:
        doc = Document(
            title=title,
            content=content,
            doc_metadata=metadata,
            embedding=embedding,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)
        return doc


def similarity_search(query: str, k: int = 3) -> List[Document]:
    """
    Perform a vector similarity search over documents using cosine distance.

    Uses the pgvector cosine distance operator (<=>) under the hood via
    the SQLAlchemy integration.
    """
    if k <= 0:
        return []

    query_embedding = get_embedding(query)
    if not query_embedding:
        return []

    with SessionLocal() as session:
        stmt = (
            select(Document)
            .order_by(Document.embedding.cosine_distance(query_embedding))
            .limit(k)
        )
        results = session.execute(stmt).scalars().all()
        return list(results)

