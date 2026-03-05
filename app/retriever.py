from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import String, cast, select
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


def list_documents() -> List[Document]:
    """
    List all documents from the database (past transit projects).
    """
    with SessionLocal() as session:
        stmt = select(Document).order_by(Document.id.desc())
        results = session.execute(stmt).scalars().all()
        return list(results)


def delete_document(doc_id: int) -> bool:
    """
    Delete a document by id. Returns True if a row was deleted.
    """
    with SessionLocal() as session:
        doc = session.get(Document, doc_id)
        if doc is None:
            return False
        session.delete(doc)
        session.commit()
        return True


def similarity_search(
    query: str,
    k: int = 3,
    project_type: Optional[str] = None,
) -> List[Document]:
    """
    Perform vector similarity search over documents (cosine distance).

    If project_type is provided, filter to documents whose metadata
    project_type matches first, then rank by similarity and return top k.
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
        if project_type and project_type.strip():
            # Filter by matching project_type in JSONB metadata
            stmt = stmt.where(
                cast(Document.doc_metadata["project_type"], String) == project_type.strip()
            )
        results = session.execute(stmt).scalars().all()
        return list(results)

