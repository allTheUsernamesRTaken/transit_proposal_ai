from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectMode(str, Enum):
    PLANNING = "planning"
    FEASIBILITY = "feasibility"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    EVALUATION = "evaluation"


class TransitMode(str, Enum):
    BUS_NETWORK = "bus_network"
    BUS_RAPID_TRANSIT = "bus_rapid_transit"
    LIGHT_RAIL = "light_rail"
    METRO = "metro"
    COMMUTER_RAIL = "commuter_rail"
    REGIONAL_RAIL = "regional_rail"
    STREETCAR = "streetcar"
    MICROTRANSIT = "microtransit"
    ON_DEMAND = "on_demand"
    ACTIVE_TRANSPORT = "active_transport"
    MULTIMODAL_CORRIDOR = "multimodal_corridor"


class Geography(BaseModel):
    city: Optional[str] = Field(default=None, description="Primary city for the project.")
    region: Optional[str] = Field(default=None, description="Region or metropolitan area.")
    country: Optional[str] = Field(default=None, description="Country of the project.")
    description: Optional[str] = Field(
        default=None,
        description="Free-text description of the study area (corridors, neighborhoods, etc.).",
    )


class Stakeholder(BaseModel):
    name: str = Field(..., description="Stakeholder name (agency, community group, etc.).")
    role: Optional[str] = Field(default=None, description="Role in the project.")
    primary_contact: Optional[str] = Field(default=None, description="Optional primary contact person.")


class Risk(BaseModel):
    description: str = Field(..., description="Description of a key project risk or uncertainty.")
    likelihood: Optional[str] = Field(
        default=None, description="Qualitative likelihood (e.g., low, medium, high)."
    )
    impact: Optional[str] = Field(
        default=None, description="Qualitative impact on scope, cost, schedule, or outcomes."
    )


class KPI(BaseModel):
    name: str = Field(..., description="Name of the performance indicator.")
    description: Optional[str] = Field(default=None, description="What the indicator measures.")
    unit: Optional[str] = Field(default=None, description="Unit or direction of improvement (e.g., minutes, %).")


class ProjectDefinition(BaseModel):
    """
    Structured definition of a transit consulting project used throughout Transit Proposal AI.
    """

    project_name: str = Field(..., description="Short name of the proposed project.")
    client_name: str = Field(..., description="Name of the client agency or organization.")

    geography: Geography = Field(..., description="Geographic context and study area for the project.")
    primary_transit_modes: List[TransitMode] = Field(
        default_factory=list,
        description="Transit modes that are central to this project.",
    )

    @field_validator("primary_transit_modes", mode="before")
    @classmethod
    def _coerce_primary_transit_modes(cls, v: object) -> object:
        """
        GPT outputs sometimes use non-enum labels like "demand_response".
        Coerce common variants to the closest allowed TransitMode value.
        """
        if v is None:
            return []

        def _coerce_one(item: object) -> object:
            if isinstance(item, TransitMode):
                return item
            if not isinstance(item, str):
                return item
            s = item.strip().lower()
            if not s:
                return item

            # Exact/substring matches of defined enum values
            for mode in TransitMode:
                if s == mode.value or mode.value in s:
                    return mode

            # Common synonyms / variants
            if any(k in s for k in ("demand_response", "demand response", "paratransit", "dial-a-ride", "dial a ride", "demand-responsive")):
                return TransitMode.ON_DEMAND
            if any(k in s for k in ("on demand", "on-demand")):
                return TransitMode.ON_DEMAND
            if any(k in s for k in ("micro transit", "micro-transit")):
                return TransitMode.MICROTRANSIT

            # Fall back to original value; Pydantic will raise if truly invalid.
            return item

        if isinstance(v, list):
            return [_coerce_one(item) for item in v]

        # Allow a single value instead of a list
        return [_coerce_one(v)]

    project_mode: ProjectMode = Field(
        default=ProjectMode.PLANNING,
        description="Overall lifecycle phase of the project.",
    )
    
    @field_validator("project_mode", mode="before")
    @classmethod
    def _coerce_project_mode(cls, v: object) -> object:
        """
        GPT outputs sometimes put a descriptive phrase in project_mode.
        Coerce common variants to the closest allowed enum value.
        """
        if v is None:
            return ProjectMode.PLANNING
        if isinstance(v, ProjectMode):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if not s:
                return ProjectMode.PLANNING

            # Exact/substring matches of allowed values.
            for mode in ProjectMode:
                if s == mode.value or mode.value in s:
                    return mode

            # Heuristic mapping for common lifecycle language.
            if any(k in s for k in ("feasibility", "alternatives analysis", "aa", "screening", "viability")):
                return ProjectMode.FEASIBILITY
            if any(k in s for k in ("design", "preliminary engineering", "30%", "60%", "90%", "engineering")):
                return ProjectMode.DESIGN
            if any(k in s for k in ("implement", "implementation", "rollout", "deployment", "procurement", "deliver", "execute")):
                return ProjectMode.IMPLEMENTATION
            if any(k in s for k in ("evaluate", "evaluation", "monitor", "kpi", "performance", "optimization", "after-action")):
                return ProjectMode.EVALUATION
            if any(k in s for k in ("plan", "planning", "strategy", "study", "tdp", "coa", "concept")):
                return ProjectMode.PLANNING

            # Safe default to avoid hard failures.
            return ProjectMode.PLANNING

        return v

    objectives: List[str] = Field(
        default_factory=list,
        description="High-level objectives or questions the project must address.",
    )

    scope_summary: str = Field(
        ...,
        description="Narrative summary of scope (corridors, services, analyses, etc.).",
    )

    key_tasks: List[str] = Field(
        default_factory=list,
        description="Major tasks or workstreams (e.g., data collection, modeling, engagement).",
    )

    deliverables: List[str] = Field(
        default_factory=list,
        description="Expected deliverables (e.g., technical memo, operations plan, final report).",
    )

    assumptions: List[str] = Field(
        default_factory=list,
        description="Key planning assumptions and constraints known at proposal time.",
    )

    constraints: List[str] = Field(
        default_factory=list,
        description="Key constraints (e.g., budget, schedule, political, right-of-way).",
    )

    timeline_months: Optional[int] = Field(
        default=None,
        description="Approximate project duration in months.",
        ge=1,
    )

    budget_usd: Optional[float] = Field(
        default=None,
        description="Rough order-of-magnitude budget for the consulting engagement (USD).",
        ge=0,
    )

    stakeholders: List[Stakeholder] = Field(
        default_factory=list,
        description="Key agencies and partners involved in the project.",
    )

    risks: List[Risk] = Field(
        default_factory=list,
        description="Known project risks and uncertainties.",
    )

    kpis: List[KPI] = Field(
        default_factory=list,
        description="Key performance indicators to track project success.",
    )

