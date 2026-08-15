"""Node: Pattern Conformance Scoring.

Scores the preprocessed ticket (`feature_markdown`/`feature_metadata`)
against established company patterns/standards (naming conventions,
structure, level of acceptance-criteria detail, completeness, etc.). The
score is logged before the pipeline proceeds, and - when the ticket is not
"conformant" - the graph pauses (`confirm_low_score`) to ask a human
whether to proceed anyway with a possibly incomplete feature ticket.

The resulting `pattern_conformance` is also used by `decide_rag_usage` to
make `rag_retrieval` optional: well-formed tickets that already conform to
company patterns can skip the extra retrieval hop, saving latency/cost,
while divergent/partial tickets are routed through RAG to ground
generation with company standards.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.company_patterns import load_company_patterns
from app.llm_config import build_http_client, llm_configured
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

Using the "How Scoring Maps to These Patterns" section above as your rubric, score the ticket as one of: \
"divergent", "partial", or "conformant".
"""


def _heuristic_score(state: PipelineState) -> PatternScoreResult:
    """Deterministic fallback scorer used when no LLM is configured.

    Mirrors the "How Scoring Maps to These Patterns" rubric in
    `company_patterns.md` (loaded via `load_company_patterns()` for the
    LLM scorer) using the lightweight completeness signals already
    computed by `preprocessing` (`feature_metadata`), since a full text
    read isn't needed to check description/acceptance-criteria presence.
    """
    metadata = state.get("feature_metadata", {})
    has_description = metadata.get("has_description", False)
    criteria_count = metadata.get("acceptance_criteria_count", 0)

    if not has_description or criteria_count == 0:
        return PatternScoreResult(
            conformance="divergent",
            rationale="Heuristic scorer: missing description and/or acceptance criteria.",
        )
    if criteria_count < 2:
        return PatternScoreResult(
            conformance="partial",
            rationale=f"Heuristic scorer: only {criteria_count} acceptance criterion found.",
        )
    return PatternScoreResult(
        conformance="conformant",
        rationale=f"Heuristic scorer: description present with {criteria_count} acceptance criteria.",
    )


def _llm_score(state: PipelineState) -> PatternScoreResult:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="gpt-4o-mini", temperature=0, http_client=build_http_client()
    ).with_structured_output(PatternScoreResult, include_raw=True)
    prompt = _SCORING_PROMPT.format(
        company_patterns=load_company_patterns(),
        feature_markdown=state.get("feature_markdown") or "(empty)",
    )
    response = llm.invoke(prompt)
    # `include_raw=True` returns {"raw": AIMessage, "parsed": PatternScoreResult, "parsing_error": ...}
    # so we can log the model's raw/unparsed response alongside the parsed result.
    raw_message = response["raw"]
    logger.info(
        "pattern_scoring: raw LLM response for feature '%s':\n%s",
        state.get("aha_feature_id"),
        raw_message.pretty_repr() if hasattr(raw_message, "pretty_repr") else raw_message,
    )
    return response["parsed"]


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
    if llm_configured():
        logger.info("pattern_scoring: using LLM scorer (gpt-4o-mini)")
        result = _llm_score(state)
    else:
        logger.info("pattern_scoring: using heuristic scorer (no OPENAI_API_KEY configured)")
        result = _heuristic_score(state)

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

    Rule: RAG retrieval only runs when the ticket is "divergent" from
    company patterns. "partial" and "conformant" tickets skip straight to
    `llm_generation`, since they already carry enough structure/detail.
    """
    if state.get("error"):
        log_edge("confirm_low_score", "error", "error_handler")
        return "error_handler"

    conformance = state.get("pattern_conformance", "divergent")
    if conformance == "divergent":
        log_edge("confirm_low_score", "continue+divergent", "rag_retrieval")
        return "rag_retrieval"
    log_edge("confirm_low_score", "continue+partial", "llm_generation")
    return "llm_generation"
