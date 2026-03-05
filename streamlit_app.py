"""
Transit Proposal AI — Streamlit UI.

Public transit consulting: bus agencies, rural transit, grant-funded.
Uses Supabase Postgres (pgvector), OpenAI embeddings and chat.
"""
from __future__ import annotations

import json
import time

import streamlit as st

from app.clarifier import generate_clarification_questions
from app.drafter import generate_proposal, project_to_query
from app.estimator import estimate_effort
from app.extractor import extract_project_definition
from app.models import ProjectDefinition
from app.past_project import (
    AGENCY_TYPES,
    PROJECT_TYPES,
    build_past_project_summary,
    doc_to_display_row,
    past_project_metadata,
)
from app.retriever import add_document, delete_document, list_documents, similarity_search


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
    if "timings" not in st.session_state:
        st.session_state.timings = {}
    if "retrieved_comparable_docs" not in st.session_state:
        st.session_state.retrieved_comparable_docs = []
    if "past_projects_loaded" not in st.session_state:
        st.session_state.past_projects_loaded = False


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

with st.sidebar:
    st.subheader("Performance")
    timings = st.session_state.get("timings") or {}
    if timings:
        for k, v in timings.items():
            st.write(f"**{k}:** {v:.2f}s")
    else:
        st.caption("Run an action to see timings.")

# --- Manage Past Transit Projects (expandable at top) ---
with st.expander("Manage Past Transit Projects", expanded=False):
    st.caption("Add and manage past projects used for comparable retrieval.")

    # A. Inputs to add new past project
    st.write("**Add new past project**")
    add_title = st.text_input("Project Title", key="add_title")
    add_agency_type = st.selectbox("Agency Type", AGENCY_TYPES, key="add_agency_type")
    add_project_type = st.selectbox("Project Type", PROJECT_TYPES, key="add_project_type")
    add_state = st.text_input("State/Province", key="add_state")
    add_fleet_size = st.text_input("Fleet Size", key="add_fleet_size")
    add_fta_program = st.text_input("Funding/Grant Program (optional)", key="add_fta_program")
    add_total_hours = st.number_input("Total Hours", min_value=0, value=0, step=1, key="add_total_hours")
    add_timeline_months = st.number_input("Timeline (months)", min_value=0, value=0, step=1, key="add_timeline_months")
    add_summary = st.text_area("Project Summary", height=120, key="add_summary")

    if st.button("Save past project"):
        if not (add_title and add_state):
            st.warning("Project Title and State/Province are required.")
        else:
            try:
                content = build_past_project_summary(
                    title=add_title,
                    agency_type=add_agency_type,
                    project_type=add_project_type,
                    state=add_state,
                    fleet_size=add_fleet_size or None,
                    fta_program=add_fta_program or None,
                    total_hours=add_total_hours if add_total_hours else None,
                    timeline_months=add_timeline_months if add_timeline_months else None,
                    project_summary=add_summary or "",
                )
                meta = past_project_metadata(
                    title=add_title,
                    agency_type=add_agency_type,
                    project_type=add_project_type,
                    state=add_state,
                    fleet_size=add_fleet_size or None,
                    fta_program=add_fta_program or None,
                    total_hours=add_total_hours if add_total_hours else None,
                    timeline_months=add_timeline_months if add_timeline_months else None,
                    project_summary=add_summary or "",
                )
                add_document(title=add_title, content=content, metadata=meta)
                st.success("Past project saved.")
            except Exception as e:
                st.error(str(e))

    # B. List existing projects with delete (loaded on demand)
    st.write("**Existing past projects**")
    if st.button("Load existing projects"):
        st.session_state.past_projects_loaded = True

    docs = []
    if st.session_state.past_projects_loaded:
        with st.spinner("Loading existing past projects..."):
            try:
                docs = list_documents()
            except Exception as e:
                st.error(f"Could not load projects: {e}")
                docs = []
    if docs:
        header_cols = st.columns([3, 1, 1, 1, 1, 1])
        header_cols[0].write("**Title**")
        header_cols[1].write("**Project Type**")
        header_cols[2].write("**State/Province**")
        header_cols[3].write("**Hours**")
        header_cols[4].write("**Timeline**")
        header_cols[5].write("")
        for doc in docs:
            row = doc_to_display_row(doc)
            cols = st.columns([3, 1, 1, 1, 1, 1])
            cols[0].write(row["title"])
            cols[1].write(row["project_type"])
            cols[2].write(row["state"])
            cols[3].write(row["hours"] if row["hours"] is not None else "—")
            cols[4].write(row["timeline"] if row["timeline"] is not None else "—")
            if cols[5].button("Delete", key=f"del_{row['id']}"):
                delete_document(row["id"])
                st.rerun()
    else:
        #st.caption("No past projects yet. Add one above.")
        pass

# --- Section 1: Upload transcript ---
st.subheader("1. Transcript")
uploaded = st.file_uploader("Upload transcript", type=["txt"], label_visibility="collapsed")
if uploaded is not None:
    st.session_state.transcript_text = uploaded.read().decode("utf-8", errors="replace")
if st.session_state.transcript_text:
    st.text_area("Transcript content", height=120, key="transcript_text")

# --- Extract Project Definition ---
if st.button("Extract Project Definition"):
    if not st.session_state.transcript_text.strip():
        st.warning("Upload or paste a transcript first.")
    else:
        with st.spinner("Extracting..."):
            try:
                t0 = time.perf_counter()
                project = extract_project_definition(st.session_state.transcript_text)
                st.session_state.timings["extract_project_definition"] = time.perf_counter() - t0
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
                t0 = time.perf_counter()
                st.session_state.clarification_questions = generate_clarification_questions(project)
                st.session_state.timings["generate_clarification_questions"] = time.perf_counter() - t0
                st.rerun()
            except Exception as e:
                st.error(str(e))

if st.session_state.clarification_questions:
    st.subheader("Clarification Questions")
    for i, q in enumerate(st.session_state.clarification_questions):
        st.markdown(f"**Q{i + 1}.** {q}")
        st.text_area("Your notes", key=f"clar_notes_{i}", height=60, label_visibility="collapsed")

# --- Run Estimation ---
if st.button("Run Estimation"):
    project = _parse_project_from_json()
    if project is None:
        st.warning("Extract and fix project definition first.")
    else:
        with st.spinner("Running estimation..."):
            try:
                t0 = time.perf_counter()
                st.session_state.estimate = estimate_effort(project)
                st.session_state.timings["estimate_effort"] = time.perf_counter() - t0
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

# --- Retrieved Comparable Transit Projects (persisted in session_state) ---
retrieved = st.session_state.get("retrieved_comparable_docs") or []
if retrieved:
    st.subheader("Retrieved Comparable Transit Projects")
    for doc in retrieved:
        row = doc_to_display_row(doc)
        st.write(f"**{row['title']}** — {row['project_type']} | {row['state']} | Hours: {row['hours'] or '—'} | Timeline: {row['timeline'] or '—'} months")

# --- Generate Proposal ---
project_type_filter = st.selectbox(
    "Filter comparables by project type (optional)",
    options=[None] + PROJECT_TYPES,
    format_func=lambda x: "(no filter)" if x is None else x,
    key="proposal_project_type_filter",
)
if st.button("Generate Proposal"):
    project = _parse_project_from_json()
    if project is None:
        st.warning("Extract and fix project definition first.")
    elif st.session_state.estimate is None:
        st.warning("Run estimation first.")
    else:
        with st.spinner("Retrieving comparables and generating proposal..."):
            try:
                t0 = time.perf_counter()
                query = project_to_query(project)
                filter_val = project_type_filter if project_type_filter else None
                docs = similarity_search(query, k=3, project_type=filter_val)
                st.session_state.retrieved_comparable_docs = docs
                st.session_state.proposal_text = generate_proposal(
                    project,
                    st.session_state.estimate,
                    comparable_docs=docs,
                    project_type_filter=filter_val,
                )
                st.session_state.timings["generate_proposal"] = time.perf_counter() - t0
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
