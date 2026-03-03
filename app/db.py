from __future__ import annotations

import os
from typing import Any, Dict
from urllib.parse import parse_qsl, urlparse, urlencode, urlunparse

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


def _ensure_sslmode(url: str) -> str:
    """
    Ensure sslmode=require is present in the database URL for hosted
    Postgres providers like Supabase.
    """
    parsed = urlparse(url)
    query_params: Dict[str, Any] = dict(parse_qsl(parsed.query))

    if "sslmode" not in query_params:
        query_params["sslmode"] = "require"
        parsed = parsed._replace(query=urlencode(query_params))
        return urlunparse(parsed)

    return url


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return _ensure_sslmode(url)


DATABASE_URL = _get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(length=512), nullable=False)
    content = Column(Text, nullable=False)
    doc_metadata = Column("metadata", JSON, nullable=True)
    # text-embedding-3-small currently produces 1536-dimensional vectors
    embedding = Column(Vector(dim=1536), nullable=False)


def create_tables() -> None:
    """
    Create mapped tables in the target database.

    Assumes that the pgvector extension is already installed and that the
    'documents' table (or its equivalent) is safe to manage via SQLAlchemy.
    """
    Base.metadata.create_all(bind=engine)

