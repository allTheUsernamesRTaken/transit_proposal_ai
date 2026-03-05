from __future__ import annotations

import os
import socket
from typing import Any, Dict
from urllib.parse import parse_qsl, urlparse, urlencode, urlunparse

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Column, Integer, String, Text, create_engine
from sqlalchemy.event import listens_for
from sqlalchemy.orm import declarative_base, sessionmaker

from app.settings import get_required_secret


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


def _force_ipv4(url: str) -> str:
    """
    Rewrite the host portion of the URL to an IPv4 address.

    Some hosting environments have trouble connecting to IPv6
    addresses returned by DNS (EADDRNOTAVAIL / "Cannot assign
    requested address"). This forces resolution to IPv4 while
    keeping the rest of the connection string intact.
    """
    parsed = urlparse(url)
    host = parsed.hostname

    # If there's no hostname or it's already an IPv4 literal, do nothing.
    if not host:
        return url
    try:
        socket.inet_aton(host)
        return url
    except OSError:
        pass

    try:
        info = socket.getaddrinfo(
            host,
            parsed.port or 5432,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return url

    if not info:
        return url

    ipv4 = info[0][4][0]

    # Rebuild netloc with username/password and port preserved.
    userinfo = ""
    if parsed.username:
        userinfo += parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    port = f":{parsed.port}" if parsed.port else ""
    new_netloc = f"{userinfo}{ipv4}{port}"

    parsed = parsed._replace(netloc=new_netloc)
    return urlunparse(parsed)


def _get_database_url() -> str:
    url = get_required_secret("DATABASE_URL")
    # Ensure SSL is required for Supabase and similar providers.
    url = _ensure_sslmode(url)
    # Force IPv4 resolution to avoid IPv6 connection issues on some hosts.
    url = _force_ipv4(url)
    return url


def _set_no_prepared_statements(dbapi_connection, _connection_record):
    """
    Disable prepared statements on the raw psycopg2 connection.
    Required for Supabase transaction pooler (port 6543), which does not
    support them.
    """
    if hasattr(dbapi_connection, "prepare_threshold"):
        dbapi_connection.prepare_threshold = 0


DATABASE_URL = _get_database_url()

# For deployed apps (e.g. Streamlit Cloud): if you see "Cannot assign requested
# address" when using Supabase, set DATABASE_URL in secrets to the Session mode
# pooler (not the direct connection). In Supabase: Connect → Session mode →
# copy the URI (host aws-0-<region>.pooler.supabase.com, port 5432). That
# endpoint supports IPv4; the direct db.*.supabase.co connection is IPv6-only.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# Transaction pooler (port 6543) does not support prepared statements.
if urlparse(DATABASE_URL).port == 6543:
    listens_for(engine, "connect")(_set_no_prepared_statements)

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

