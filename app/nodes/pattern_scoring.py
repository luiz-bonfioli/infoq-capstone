"""Node: Pattern Conformance Scoring.

Scores the preprocessed ticket (`feature_markdown`/`feature_metadata`)
against established company patterns/standards (naming conventions,
structure, level of acceptance-criteria detail, completeness, etc.). The
score is logged before the pipeline proceeds, and - when the ticket is not
"conformant" - the graph pauses (`confirm_low_score`) to ask a human
whether to proceed anyway with a possibly incomplete feature ticket.

The resulting `pattern_conformance` is also used by `decide_rag_usage` to
decide whether `rag_retrieval` runs: only fully "conformant" tickets can
skip the retrieval hop (saving latency/cost), while any weak ticket -
"partial" or "divergent" - is routed through RAG so the extra retrieval
grounds generation with company knowledge about the ticket's problem,
filling in what the weak ticket itself is missing.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.company_patterns import load_company_patterns
from app.llm_config import build_http_client, chat_model_name, llm_configured
from app.nodes.utils import log_edge, safe_node
from app.state import PatternConformance, PipelineState

logger = logging.getLogger(__name__)


class PatternScoreResult(BaseModel):
    conformance: PatternConformance = Field(
        description=(
            "'divergent' if the ticket is missing acceptance criteria or a real "
            "description (i.e. the feature is not complete enough to generate reliable "
            "test cases from); 'partial' if it has some but thin detail; 'conformant' if "
            "it has a clear description and multiple concrete acceptance criteria."
        )
    )
    rationale: str = Field(description="One or two sentences explaining the score.")


_SCORING_PROMPT = """You are a QA lead assessing whether a feature ticket is complete and detailed \
enough to reliably generate test cases from, and whether it conforms to the company's documented ticket \
and test case patterns below.

--- Company Patterns ---
{company_patterns}
--- End Company Patterns ---

Feature ticket (Markdown):
{feature_markdown}

Using the company patterns above as your rubric, score the ticket as one of: \
"divergent", "partial", or "conformant".
"""


def _llm_score(state: PipelineState) -> PatternScoreResult:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=chat_model_name(), temperature=0, http_client=build_http_client()
    ).with_structured_output(PatternScoreResult)
    prompt = _SCORING_PROMPT.format(
        company_patterns=load_company_patterns(),
        feature_markdown=state.get("feature_markdown") or "(empty)",
    )
    return llm.invoke(prompt)


@safe_node("pattern_scoring")
def pattern_scoring(state: PipelineState) -> dict:
    """Score how closely the preprocessed ticket follows company patterns.

    Args:
        state: Current pipeline state. Requires `feature_markdown` and
            `feature_metadata`.

    Returns:
        Partial state update with `pattern_conformance` and
        `pattern_score_rationale`.
    """
    if not llm_configured():
        raise RuntimeError(
            "pattern_scoring requires an LLM: set OPENAI_API_KEY "
            "(the heuristic fallback scorer has been removed)."
        )
    logger.info("pattern_scoring: using LLM scorer (%s)", chat_model_name())
    result = _llm_score(state)

    # Always log the score before the pipeline moves on to RAG/generation,
    # so it's visible in output/logs regardless of what happens next.
    logger.info(
        "Pattern conformance score for feature '%s': %s - %s",
        state.get("aha_feature_id"),
        result.conformance,
        result.rationale,
    )

    return {
        "pattern_conformance": result.conformance,
        "pattern_score_rationale": result.rationale,
    }


def route_after_scoring(state: PipelineState) -> str:
    """Conditional edge after `pattern_scoring`.

    "conformant" tickets proceed straight to `llm_generation` (no RAG
    needed, no confirmation needed). Anything less than fully conformant
    pauses at `confirm_low_score` to let a human decide whether to proceed
    with a possibly incomplete/divergent feature ticket.
    """
    if state.get("error"):
        log_edge("pattern_scoring", "error", "error_handler")
        return "error_handler"

    if state.get("pattern_conformance") == "conformant":
        log_edge("pattern_scoring", "conformant", "llm_generation")
        return "llm_generation"
    log_edge("pattern_scoring", "partial/divergent", "confirm_low_score")
    return "confirm_low_score"


def decide_rag_usage(state: PipelineState) -> str:
    """Routing tool: decide whether `rag_retrieval` is needed.

    Rule: RAG retrieval runs for any weak (non-conformant) ticket -
    "divergent" or "partial" - because a weak ticket is missing detail
    about the problem it addresses, and RAG supplies the company knowledge
    that fills that gap. Only a "conformant" ticket (which never reaches
    this router) would skip straight to `llm_generation`.
    """
    if state.get("error"):
        log_edge("confirm_low_score", "error", "error_handler")
        return "error_handler"

    conformance = state.get("pattern_conformance", "divergent")
    if conformance in ("divergent", "partial"):
        log_edge("confirm_low_score", f"continue+{conformance}", "rag_retrieval")
        return "rag_retrieval"
    log_edge("confirm_low_score", "continue+conformant", "llm_generation")
    return "llm_generation"
