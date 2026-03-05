from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from app.settings import get_required_secret


def _load_env() -> None:
    # Load variables from a .env file if present for local development.
    load_dotenv()


def _get_database_url() -> str:
    # Use Streamlit secrets if available, otherwise fall back to environment.
    url = get_required_secret("DATABASE_URL")
    return url


def _get_openai_client() -> OpenAI:
    # Use Streamlit secrets if available, otherwise fall back to environment.
    api_key = get_required_secret("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def _load_seed_projects() -> List[Dict[str, Any]]:
    base_dir = Path(__file__).resolve().parent
    seed_path = base_dir / "seed_data" / "past_projects.json"
    if not seed_path.exists():
        raise FileNotFoundError(f"Seed data file not found at {seed_path}")

    with seed_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Seed data must be a JSON array of project objects.")

    return data


def _get_embedding(client: OpenAI, text: str) -> List[float]:
    if not text:
        return []

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return list(response.data[0].embedding)


def main() -> None:
    _load_env()
    database_url = _get_database_url()
    client = _get_openai_client()

    projects = _load_seed_projects()

    conn = psycopg2.connect(database_url)
    conn.autocommit = False

    inserted = 0

    try:
        with conn.cursor() as cur:
            for project in projects:
                title = project.get("title") or ""
                content = project.get("content") or ""
                metadata = project.get("metadata")

                if not content:
                    # Skip projects without meaningful content.
                    continue

                # Avoid duplicates by checking for existing content.
                cur.execute(
                    "SELECT id FROM documents WHERE content = %s LIMIT 1",
                    (content,),
                )
                if cur.fetchone():
                    continue

                embedding = _get_embedding(client, content)

                # Represent the embedding as a pgvector literal.
                embedding_literal = "[" + ",".join(str(x) for x in embedding) + "]"

                cur.execute(
                    """
                    INSERT INTO documents (title, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s::vector)
                    """,
                    (title, content, json.dumps(metadata) if metadata is not None else None, embedding_literal),
                )
                inserted += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Inserted {inserted} rows into documents table.")


if __name__ == "__main__":
    main()

