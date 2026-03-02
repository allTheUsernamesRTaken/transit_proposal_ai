from __future__ import annotations

import json
import logging
from json import JSONDecodeError

from .claude_client import call_claude
from .models import ProjectDefinition


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are an expert transit consulting proposal analyst.

Your task is to read transcripts of client conversations, RFP text, or internal notes
and extract a structured definition of a transit consulting project.

CRITICAL RULES:
- This is specifically about public transit and multimodal transport planning and operations.
- Do NOT treat this as generic software, marketing, or construction work unless explicitly stated.
- Never invent or guess detailed scope, budget, or timeline values that are not supported by the text.
- When information is missing, unclear, or cannot be reasonably inferred, you MUST use the literal string "unknown".
- You must stay within the facts available in the transcript.

OUTPUT FORMAT:
- You MUST output a single JSON object that can be parsed directly by a strict JSON parser.
- Do NOT include Markdown, comments, backticks, or any explanatory prose.
- The JSON must be compatible with this schema (field names and basic types):
  {
    "project_name": string,
    "client_name": string,
    "geography": {
      "city": string or "unknown",
      "region": string or "unknown",
      "country": string or "unknown",
      "description": string or "unknown"
    },
    "primary_transit_modes": [string, ...],
    "project_mode": string,
    "objectives": [string, ...],
    "scope_summary": string,
    "key_tasks": [string, ...],
    "deliverables": [string, ...],
    "assumptions": [string, ...],
    "constraints": [string, ...],
    "timeline_months": integer or null,
    "budget_usd": number or null,
    "stakeholders": [
      {
        "name": string,
        "role": string or "unknown",
        "primary_contact": string or "unknown"
      },
      ...
    ],
    "risks": [
      {
        "description": string,
        "likelihood": string or "unknown",
        "impact": string or "unknown"
      },
      ...
    ],
    "kpis": [
      {
        "name": string,
        "description": string or "unknown",
        "unit": string or "unknown"
      },
      ...
    ]
  }

ADDITIONAL GUIDANCE:
- If you are not certain about project_name or client_name, set them to "unknown".
- For numeric fields like timeline_months and budget_usd, use null when not supported by the transcript.
- For list fields, use an empty list [] when there is no reliable information.
- For every string field where you cannot extract a reliable value, use "unknown" exactly.
- primary_transit_modes should use simple lowercase snake_case strings such as
  "bus_network", "bus_rapid_transit", "light_rail", "metro", "commuter_rail",
  "regional_rail", "streetcar", "microtransit", "on_demand", "active_transport",
  or "multimodal_corridor". If modes are unclear, use an empty list.

REMEMBER:
- Output ONLY the JSON object.
- The JSON must be syntactically valid and self-contained.
"""


def _build_user_prompt(transcript: str) -> str:
    return (
        "Extract a structured transit consulting project definition from the following transcript.\n\n"
        "Transcript:\n"
        f"{transcript}\n"
    )


def _parse_json_strict(raw: str) -> dict:
    """
    Parse JSON, attempting to be tolerant of accidental leading/trailing text
    while still enforcing that we end up with a single JSON object.
    """
    text = raw.strip()

    # Best-effort extraction if the model accidentally adds text around JSON.
    if not text.startswith("{") or not text.endswith("}"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            text = text[start : end + 1]

    data = json.loads(text)
    if not isinstance(data, dict):
        raise JSONDecodeError("Top-level JSON must be an object", text, 0)
    return data


def extract_project_definition(transcript: str) -> ProjectDefinition:
    """
    Use Claude to extract a ProjectDefinition from free-text transcript input.

    - Uses a transit-specific system prompt and call_claude().
    - Temperature fixed at 0.1 for determinism.
    - Expects strict JSON-only output and parses it.
    - Retries once if JSON parsing fails.
    - Validates the result with the ProjectDefinition Pydantic model.
    """
    user_prompt = _build_user_prompt(transcript)

    last_error: Exception | None = None

    for attempt in range(2):
        raw = call_claude(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        try:
            payload = _parse_json_strict(raw)
            # Let Pydantic enforce schema correctness.
            return ProjectDefinition.model_validate(payload)
        except JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "Failed to parse JSON from Claude on attempt %d: %s",
                attempt + 1,
                exc,
            )
            # Only retry once on JSON parsing issues.
            if attempt == 0:
                continue
        except Exception as exc:
            # Do not retry on validation or other unexpected errors.
            last_error = exc
            break

    if last_error is not None:
        raise last_error
    raise RuntimeError("Unknown error while extracting project definition.")

