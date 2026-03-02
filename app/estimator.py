from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

from .models import ProjectDefinition


# Base hour estimates by project type
BASE_HOURS_BY_TYPE: Dict[str, int] = {
    "coa": 500,  # Comprehensive Operational Analysis
    "tdp": 600,  # Transit Development Plan
    "its": 450,  # Intelligent Transportation Systems planning
    "microtransit": 400,
    "grant_support": 200,
    "operational_review": 350,
    "unknown": 300,
}


def _normalize_text(project: ProjectDefinition) -> str:
    """Concatenate key text fields into a single lowercase blob for simple heuristics."""
    parts: List[str] = [
        project.project_name,
        project.scope_summary,
        " ".join(project.objectives or []),
        " ".join(project.assumptions or []),
        " ".join(project.constraints or []),
        " ".join(project.deliverables or []),
    ]
    return " ".join(p for p in parts if p).lower()


def _infer_project_type(text: str) -> Tuple[str, List[str]]:
    """Infer a coarse project type label from free text."""
    assumptions: List[str] = []

    if "comprehensive operational analysis" in text or "coa" in text:
        project_type = "coa"
    elif "transit development plan" in text or "tdp" in text:
        project_type = "tdp"
    elif "intelligent transportation system" in text or "its " in text or "its-" in text:
        project_type = "its"
    elif "microtransit" in text or "on-demand" in text or "on demand" in text:
        project_type = "microtransit"
    elif "grant" in text and ("application" in text or "support" in text or "fta" in text):
        project_type = "grant_support"
    elif "operational review" in text or "operations review" in text:
        project_type = "operational_review"
    else:
        project_type = "unknown"

    assumptions.append(f"Base project type inferred as '{project_type}'.")
    return project_type, assumptions


def _estimate_vehicle_count(text: str) -> Tuple[int, List[str]]:
    """
    Estimate vehicle count from text if explicitly mentioned.

    Looks for simple patterns like '25 buses' or '30 vehicles'.
    """
    assumptions: List[str] = []
    pattern = re.compile(r"\b(\d+)\s+(buses|bus|vehicles|fleet)\b", re.IGNORECASE)
    match = pattern.search(text)
    if match:
        count = int(match.group(1))
        assumptions.append(f"Vehicle count inferred as {count} from transcript text.")
        return count, assumptions

    assumptions.append("Vehicle count not specified; assuming 0 additional hours for vehicles.")
    return 0, assumptions


def _count_public_workshops(project: ProjectDefinition) -> Tuple[int, List[str]]:
    """Count public workshop-style deliverables from the deliverables list."""
    assumptions: List[str] = []
    keywords = ("workshop", "open house", "public meeting", "community meeting", "listening session")

    count = 0
    for d in project.deliverables or []:
        text = d.lower()
        if any(k in text for k in keywords):
            count += 1

    assumptions.append(f"Identified {count} public workshop-style deliverables.")
    return count, assumptions


def _detect_fta_funding(text: str) -> Tuple[bool, List[str]]:
    """Detect whether FTA funding is mentioned."""
    assumptions: List[str] = []
    fta_keywords = (
        "fta",
        "federal transit administration",
        "section 5307",
        "section 5309",
        "section 5339",
        "cig program",
        "capital investment grant",
        "raise grant",
    )

    has_fta = any(k in text for k in fta_keywords)
    if has_fta:
        assumptions.append("FTA-related funding or programs mentioned.")
    else:
        assumptions.append("FTA funding not explicitly mentioned.")
    return has_fta, assumptions


def _detect_board_approval(text: str) -> Tuple[bool, List[str]]:
    """Detect whether board approval is required."""
    assumptions: List[str] = []
    board_keywords = (
        "board approval",
        "approved by the board",
        "board adoption",
        "adoption by the board",
        "governing board approval",
    )

    requires_board = any(k in text for k in board_keywords)
    if requires_board:
        assumptions.append("Board approval requirement detected.")
    else:
        assumptions.append("Board approval requirement not explicitly mentioned.")
    return requires_board, assumptions


def estimate_effort(project: ProjectDefinition) -> Dict[str, object]:
    """
    Estimate effort (hours and timeline) for a transit consulting project.

    This is a simple, deterministic heuristic that does not call Claude.
    """
    assumptions: List[str] = []
    text = _normalize_text(project)

    # Base hours by inferred project type
    project_type, type_assumptions = _infer_project_type(text)
    assumptions.extend(type_assumptions)
    base_hours = BASE_HOURS_BY_TYPE.get(project_type, BASE_HOURS_BY_TYPE["unknown"])

    total_hours = base_hours

    # Vehicle-based adjustment
    vehicle_count, vehicle_assumptions = _estimate_vehicle_count(text)
    assumptions.extend(vehicle_assumptions)
    total_hours += 5 * vehicle_count

    # Public workshops / meetings
    workshop_count, workshop_assumptions = _count_public_workshops(project)
    assumptions.extend(workshop_assumptions)
    total_hours += 40 * workshop_count

    # FTA funding
    has_fta, fta_assumptions = _detect_fta_funding(text)
    assumptions.extend(fta_assumptions)
    if has_fta:
        total_hours += 60

    # Board approval
    requires_board, board_assumptions = _detect_board_approval(text)
    assumptions.extend(board_assumptions)
    if requires_board:
        total_hours += 80

    # Ensure non-negative and convert to int
    total_hours = max(int(total_hours), 0)

    # Simple rule-of-thumb timeline: 120 hours per month, rounded up
    timeline_months = max(1, int(math.ceil(total_hours / 120.0)))

    return {
        "estimated_hours": total_hours,
        "timeline_months": timeline_months,
        "assumptions": assumptions,
    }

