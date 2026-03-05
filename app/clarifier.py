from __future__ import annotations

import json
import logging
from json import JSONDecodeError
from typing import List

from .chatgpt_client import call_chatgpt
from .models import ProjectDefinition


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a senior transit consulting project manager.

You are given a structured definition of a proposed public transit consulting project.
Your job is to identify remaining ambiguities that would materially affect:
- project scope,
- level of effort and cost,
- schedule and delivery timeline.

From this structure, you must generate a small set of clarifying questions to ask the client.

CRITICAL CONSTRAINTS:
- Stay strictly within the information provided in the project definition.
- Do NOT invent or propose new scope items that are not already implied by the project.
- Focus only on clarifications that would change cost, scope boundaries, or schedule expectations.
- Avoid generic boilerplate; make questions specific to the provided project details.
- Do NOT repeat essentially the same question in different words.

OUTPUT FORMAT:
- Output a single JSON array of 2 to 4 strings.
- Each element is one short, clear, consultant-ready question.
- No additional text, no numbering, no Markdown, no explanations.
Example:
[
  "First question here?",
  "Second question here?"
]
"""


def _build_user_prompt(project: ProjectDefinition) -> str:
    project_json = project.model_dump_json(indent=2)
    return (
        "Based on the following structured transit consulting project definition, "
        "generate 2 to 4 clarification questions as described in the system prompt.\n\n"
        "Project definition (JSON):\n"
        f"{project_json}\n"
    )


def _parse_questions(raw: str) -> List[str]:
    """
    Parse a JSON array of strings from the model output, with light trimming in
    case the model accidentally adds text around the array.
    """
    text = raw.strip()

    if not text.startswith("[") or not text.endswith("]"):
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and start < end:
            text = text[start : end + 1]

    data = json.loads(text)
    if not isinstance(data, list):
        raise JSONDecodeError("Top-level JSON must be an array", text, 0)

    questions: List[str] = []
    for item in data:
        if isinstance(item, str):
            q = item.strip()
            if q:
                questions.append(q)

    return questions


def generate_clarification_questions(project: ProjectDefinition) -> List[str]:
    """
    Use OpenAI GPT-5.2 (via call_chatgpt wrapper) to generate 2–4 short
    clarification questions for a project.

    - Uses a transit-focused system prompt.
    - Temperature fixed at 0.2.
    - Expects JSON array output and parses it into a list of strings.
    - Retries once on JSON parsing failure.
    """
    user_prompt = _build_user_prompt(project)
    last_error: Exception | None = None

    for attempt in range(2):
        raw = call_chatgpt(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        try:
            questions = _parse_questions(raw)
            # De-duplicate while preserving order, to avoid repetition.
            seen = set()
            unique_questions: List[str] = []
            for q in questions:
                if q not in seen:
                    seen.add(q)
                    unique_questions.append(q)
            return unique_questions
        except JSONDecodeError as exc:
            last_error = exc
            logger.warning(
                "Failed to parse clarification questions JSON from model on attempt %d: %s",
                attempt + 1,
                exc,
            )
            if attempt == 0:
                continue
        except Exception as exc:
            last_error = exc
            break

    if last_error is not None:
        raise last_error
    raise RuntimeError("Unknown error while generating clarification questions.")

