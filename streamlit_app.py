"""
Transit Proposal AI — Streamlit UI.
"""
from __future__ import annotations

import json

import streamlit as st

from app.clarifier import generate_clarification_questions
from app.drafter import generate_proposal
from app.estimator import estimate_effort
from app.extractor import extract_project_definition
from app.models import ProjectDefinition


def _init_session_state() -> None:
    if "transcript_text" not in st.session_state:
        st.session_state.transcript_text = ""
    if "project_json" not in st.session_state:
        st.session_state.project_json = ""
    if "clarification_questions" not in st.session_state:
        st.session_state.clarification_questions = []
    if "estimate" not in st.session_state:
        st.session_state.estimate = None
    if "proposal_text" not in st.session_state:
        st.session_state.proposal_text = ""


def _parse_project_from_json() -> ProjectDefinition | None:
    raw = st.session_state.get("project_json", "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return ProjectDefinition.model_validate(data)
    except (json.JSONDecodeError, Exception) as e:
        st.error(f"Invalid project JSON: {e}")
        return None


st.set_page_config(page_title="Transit Proposal AI", layout="centered")
_init_session_state()

st.title("Transit Proposal AI")

# --- Section 1: Upload transcript ---
st.subheader("1. Transcript")
uploaded = st.file_uploader("Upload transcript", type=["txt"], label_visibility="collapsed")
if uploaded is not None:
    st.session_state.transcript_text = uploaded.read().decode("utf-8", errors="replace")
if st.session_state.transcript_text:
    st.text_area("Transcript content", value=st.session_state.transcript_text, height=120, key="transcript_text")

# --- Extract Project Definition ---
if st.button("Extract Project Definition"):
    if not st.session_state.transcript_text.strip():
        st.warning("Upload or paste a transcript first.")
    else:
        with st.spinner("Extracting..."):
            try:
                project = extract_project_definition(st.session_state.transcript_text)
                st.session_state.project_json = project.model_dump_json(indent=2)
                st.rerun()
            except Exception as e:
                st.error(str(e))

if st.session_state.project_json:
    st.subheader("Project Definition (editable)")
    st.text_area(
        "Edit JSON",
        value=st.session_state.project_json,
        height=280,
        key="project_json",
        label_visibility="collapsed",
    )

# --- Clarification Questions ---
if st.button("Generate Clarification Questions"):
    project = _parse_project_from_json()
    if project is None:
        st.warning("Extract and fix project definition first.")
    else:
        with st.spinner("Generating questions..."):
            try:
                st.session_state.clarification_questions = generate_clarification_questions(project)
                st.rerun()
            except Exception as e:
                st.error(str(e))

if st.session_state.clarification_questions:
    st.subheader("Clarification Questions")
    for i, q in enumerate(st.session_state.clarification_questions):
        st.text_input(f"Q{i + 1}", value=q, key=f"clar_q_{i}", disabled=True)
        st.text_area("Your notes", key=f"clar_notes_{i}", height=60, label_visibility="collapsed")

# --- Run Estimation ---
if st.button("Run Estimation"):
    project = _parse_project_from_json()
    if project is None:
        st.warning("Extract and fix project definition first.")
    else:
        with st.spinner("Running estimation..."):
            try:
                st.session_state.estimate = estimate_effort(project)
                st.rerun()
            except Exception as e:
                st.error(str(e))

if st.session_state.estimate is not None:
    st.subheader("Estimate")
    est = st.session_state.estimate
    st.write(f"**Estimated hours:** {est.get('estimated_hours', '—')}")
    st.write(f"**Timeline:** {est.get('timeline_months', '—')} months")
    if est.get("assumptions"):
        with st.expander("Assumptions"):
            for a in est["assumptions"]:
                st.write(f"- {a}")

# --- Generate Proposal ---
if st.button("Generate Proposal"):
    project = _parse_project_from_json()
    if project is None:
        st.warning("Extract and fix project definition first.")
    elif st.session_state.estimate is None:
        st.warning("Run estimation first.")
    else:
        with st.spinner("Generating proposal..."):
            try:
                st.session_state.proposal_text = generate_proposal(project, st.session_state.estimate)
                st.rerun()
            except Exception as e:
                st.error(str(e))

if st.session_state.proposal_text:
    st.subheader("Proposal")
    st.text_area(
        "Proposal text",
        value=st.session_state.proposal_text,
        height=400,
        key="proposal_display",
        label_visibility="collapsed",
    )
    st.download_button(
        "Download proposal as .txt",
        data=st.session_state.proposal_text,
        file_name="proposal.txt",
        mime="text/plain",
    )
