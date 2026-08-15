"""Shared state definition for the LangGraph pipeline.

This TypedDict flows through every node in the graph. Nodes read fields
they need and return a partial dict of updates (LangGraph merges these
into the running state).
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class TestCase(TypedDict, total=False):
    title: str
    preconditions: str
    steps: list[str]
    expected_result: str
    priority: str
    tags: list[str]


# How closely the preprocessed ticket already follows established company
# patterns/standards (naming, structure, level of detail, etc.):
#   - "divergent":  ticket deviates significantly from company patterns;
#                   RAG retrieval is required to ground generation.
#   - "partial":    ticket partially follows company patterns; RAG is
#                   optional and currently skipped for speed/cost.
#   - "conformant": ticket already closely matches company patterns; RAG
#                   retrieval is skipped as unnecessary.
PatternConformance = Literal["divergent", "partial", "conformant"]


class TestCaseResult(TypedDict, total=False):
    """Per-test-case outcome of publishing to TestRail."""

    title: str
    status: Literal["created", "error"]
    testrail_case_id: str | None
    error: str | None


class PipelineState(TypedDict, total=False):
    # --- Input ---
    aha_feature_id: str

    # --- Aha! Extractor ---
    feature_raw: dict[str, Any]  # raw Aha! API payload (description, acceptance criteria, comments, attachments)

    # --- Preprocessing ---
    feature_markdown: str
    feature_metadata: dict[str, Any]

    # --- Pattern Scoring ---
    pattern_conformance: PatternConformance
    pattern_score_rationale: str
    # "continue" | "abort" - human decision when pattern_conformance is not "conformant"
    score_review_decision: Literal["continue", "abort"]

    # --- RAG Retrieval (optional, gated by pattern_conformance) ---
    retrieved_context: list[dict[str, Any]]  # chunks from vector DB (standards, past test cases, guidelines, docs)

    # --- LLM Generation ---
    generated_test_cases: list[TestCase]

    # --- Human Review ---
    review_decision: Literal["approved", "rejected", "pending"]
    review_feedback: str

    # --- TestRail Publish ---
    testrail_run_id: str
    testrail_results: list[TestCaseResult]  # per-test-case created/error status
    published: bool

    # --- Control / bookkeeping ---
    error: str | None
    retry_count: int
