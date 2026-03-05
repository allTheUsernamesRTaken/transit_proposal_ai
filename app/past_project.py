"""
Past transit project schema and summary builder for storage and retrieval.

Used by the "Manage Past Transit Projects" UI and by the retriever.
Public transit consulting context: bus agencies, rural transit, grant-funded.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# Agency types for past project form
AGENCY_TYPES = ["Urban", "Rural", "Regional", "Tribal"]

# Project types for past project form
PROJECT_TYPES = [
    "Service Planning",
    "Capital & Infrastructure",
    "Technology & ITS",
    "Operations & Performance",
    "Grants & Funding",
    "Policy & Strategic Planning",
    "Misc / Other",
]


def build_past_project_summary(
    title: str,
    agency_type: str,
    project_type: str,
    state: str,
    fleet_size: Optional[str],
    fta_program: Optional[str],
    total_hours: Optional[int],
    timeline_months: Optional[int],
    project_summary: str,
) -> str:
    """
    Concatenate structured metadata into a clean summary string for embedding.

    This string is stored as document content and used for vector search.
    """
    parts = [
        title,
        f"Agency type: {agency_type}.",
        f"Project type: {project_type}.",
        f"State/Province: {state}.",
    ]
    if fleet_size:
        parts.append(f"Fleet size: {fleet_size}.")
    if fta_program:
        parts.append(f"Funding program: {fta_program}.")
    if total_hours is not None:
        parts.append(f"Total hours: {total_hours}.")
    if timeline_months is not None:
        parts.append(f"Timeline: {timeline_months} months.")
    if project_summary.strip():
        parts.append(project_summary.strip())
    return " ".join(parts)


def past_project_metadata(
    title: str,
    agency_type: str,
    project_type: str,
    state: str,
    fleet_size: Optional[str],
    fta_program: Optional[str],
    total_hours: Optional[int],
    timeline_months: Optional[int],
    project_summary: str,
) -> Dict[str, Any]:
    """
    Build the JSONB metadata dict for a past project document.
    """
    return {
        "title": title,
        "agency_type": agency_type,
        "project_type": project_type,
        "state": state,
        "fleet_size": fleet_size or None,
        "fta_program": fta_program or None,
        "total_hours": total_hours,
        "timeline_months": timeline_months,
        "project_summary": project_summary.strip() or None,
    }


def doc_to_display_row(doc: Any) -> Dict[str, Any]:
    """
    Extract display fields (title, project_type, state, hours, timeline) from a Document.
    """
    meta = doc.doc_metadata or {}
    return {
        "id": doc.id,
        "title": doc.title or meta.get("title", "—"),
        "project_type": meta.get("project_type") or "—",
        "state": meta.get("state") or "—",
        "hours": meta.get("total_hours"),
        "timeline": meta.get("timeline_months"),
    }
