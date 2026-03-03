from __future__ import annotations

from typing import Any, Dict, List

from .claude_client import call_claude
from .db import Document
from .models import ProjectDefinition
from .retriever import similarity_search

# Max characters of document content to include per comparable project (avoid token overflow).
_MAX_SUMMARY_CHARS = 600


def _project_to_query(project: ProjectDefinition) -> str:
    """Build a short query string from the structured project for vector search."""
    parts: List[str] = []

    parts.append(project.project_name)
    parts.append(project.client_name)
    if project.geography:
        g = project.geography
        if g.city:
            parts.append(g.city)
        if g.region:
            parts.append(g.region)
        if g.description:
            parts.append(g.description)
    parts.append(project.scope_summary)
    for m in project.primary_transit_modes:
        parts.append(m.value)
    for obj in project.objectives[:5]:
        parts.append(obj)
    for d in project.deliverables[:5]:
        parts.append(d)

    return " ".join(p for p in parts if p).strip() or project.project_name


def _format_comparable_projects(docs: List[Document]) -> str:
    """Format retrieved documents as a 'Comparable Past Projects' block."""
    if not docs:
        return "Comparable Past Projects:\nNone provided."

    lines = ["Comparable Past Projects:"]
    for i, doc in enumerate(docs, 1):
        title = doc.title or f"Project {i}"
        content = doc.content or ""
        summary = content[:_MAX_SUMMARY_CHARS] + ("..." if len(content) > _MAX_SUMMARY_CHARS else "")
        lines.append(f"\n{i}. {title}\n{summary}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a senior transit consultant writing a professional proposal for a public transit agency or authority.

Your tone is professional, precise, and transit-specific. Avoid marketing fluff and vague promises. Focus on implementable scope and clear deliverables.

STRICT RULES:
- Do NOT invent or fabricate case studies, past projects, or references. Use only the "Comparable Past Projects" material provided; if none is provided, do not reference specific past work.
- Do NOT alter, round, or reinterpret any numeric estimates (hours, budget, timeline) that are provided to you. Use the given numbers exactly in the Budget & Assumptions and Timeline sections.
- Base the proposal strictly on the project definition and the estimate provided. Do not add scope that is not already implied or stated.

STRUCTURE:
Write a proposal with exactly these sections, in order, as plain text (no markdown headers required if you prefer, but section titles must be clear):

1. Background & Understanding
2. Objectives
3. Scope of Work
4. Methodology
5. Timeline
6. Deliverables
7. Budget & Assumptions
8. Risk Mitigation

LENGTH: 1500–2500 words total. Plain text only."""


def _build_user_prompt(
    project: ProjectDefinition,
    estimate: Dict[str, Any],
    comparable_block: str,
) -> str:
    """Build the user prompt with project summary, estimate, and comparable projects."""
    project_summary = project.model_dump_json(indent=2)
    estimate_str = (
        f"Estimated hours: {estimate.get('estimated_hours', 'N/A')}\n"
        f"Timeline (months): {estimate.get('timeline_months', 'N/A')}\n"
        f"Estimator assumptions: {estimate.get('assumptions', [])}"
    )

    return f"""Use the following inputs to write the proposal.

--- Project Definition (structured) ---
{project_summary}

--- Estimate (use these numbers exactly) ---
{estimate_str}

--- {comparable_block}

---

Generate the full proposal (1500–2500 words) with the eight sections listed in the system prompt. Output plain text only."""


def generate_proposal(project: ProjectDefinition, estimate: Dict[str, Any]) -> str:
    """
    Generate a transit consulting proposal using the project definition, estimate,
    and up to three comparable past projects retrieved by vector search.
    """
    query = _project_to_query(project)
    docs = similarity_search(query, k=3)
    comparable_block = _format_comparable_projects(docs)

    user_prompt = _build_user_prompt(project, estimate, comparable_block)

    return call_claude(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=4096,
    )
