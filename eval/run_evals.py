"""Runs the graph headlessly over the full golden data set and scores each run
on golden-tier accuracy + structural quality.

Usage::
    python -m eval.run_evals

Exit codes: 0 = pass, 1 = a gate failed, 2 = configuration/API-key error.
"""

from __future__ import annotations

import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langgraph.types import Command

from eval.dataset import get_all_cases

load_dotenv(override=False)

_VALID_PRIORITIES = {"High", "Medium", "Low"}


@dataclass
class RunResult:
    feature_id: str
    state: dict[str, Any]
    elapsed_seconds: float


def run_single_case(graph, feature_id: str) -> RunResult:
    """Run the pipeline for one feature, auto-resuming every interrupt.

    A unique ``thread_id`` per run matters: the compiled graph uses a
    process-local ``MemorySaver`` keyed by thread_id, so reusing a thread_id
    would resume a stale interrupt from an earlier run.
    """
    thread_id = f"{feature_id}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    start = time.perf_counter()
    result = graph.invoke({"aha_feature_id": feature_id}, config=config)

    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        if payload.get("type") == "pattern_score_confirmation":
            decision = {"continue": True}
        else:  # "test_case_review"
            decision = {"decision": "approved", "feedback": ""}
        result = graph.invoke(Command(resume=decision), config=config)

    elapsed = time.perf_counter() - start

    return RunResult(
        feature_id=feature_id,
        state=result,
        elapsed_seconds=round(elapsed, 3),
    )


@dataclass
class CaseScore:
    index: int
    title: str
    checks: dict[str, bool]
    score: float


@dataclass
class EvalScore:
    feature_id: str
    observed_tier: str | None
    expected_tier: str
    tier_match: bool
    structural: float
    cases_generated: int


def _title_pattern_ok(title: str) -> bool:
    """≥3 non-empty segments when split on " - " (Feature - Scenario - Expected)."""
    return len([s for s in title.split(" - ") if s.strip()]) >= 3


def _score_case(tc: dict, index: int) -> CaseScore:
    """Score one generated test case as the mean of six structural checks."""
    title = str(tc.get("title") or "").strip()
    steps = tc.get("steps") or []
    checks = {
        "has_title": bool(title),
        "title_pattern_ok": _title_pattern_ok(title),
        "has_preconditions": bool(str(tc.get("preconditions") or "").strip()),
        "has_expected_result": bool(str(tc.get("expected_result") or "").strip()),
        "steps_nonempty": (
            isinstance(steps, list)
            and len(steps) >= 1
            and all(str(s).strip() for s in steps)
        ),
        "priority_valid": str(tc.get("priority") or "").strip() in _VALID_PRIORITIES,
    }
    score = sum(1.0 for ok in checks.values() if ok) / len(checks)
    return CaseScore(index=index, title=title, checks=checks, score=round(score, 4))


def _structural_score(state: dict) -> float:
    """Mean of the per-case structural scores; 0.0 if nothing was generated."""
    cases = state.get("generated_test_cases") or []
    if not cases:
        return 0.0
    return round(sum(_score_case(tc, i).score for i, tc in enumerate(cases)) / len(cases), 4)


def score_run(state: dict, case) -> EvalScore:
    """Score one run: golden-tier match + mean structural quality."""
    return EvalScore(
        feature_id=case.feature_id,
        observed_tier=state.get("pattern_conformance"),
        expected_tier=case.expected_tier,
        tier_match=state.get("pattern_conformance") == case.expected_tier,
        structural=_structural_score(state),
        cases_generated=len(state.get("generated_test_cases") or []),
    )


def run_full(cases: list) -> int:
    # Gate thresholds, hardcoded — see docs/EVALS.md for the rationale.
    MIN_ACCURACY = 0.50
    MIN_STRUCTURE = 0.80

    from app.graph.build_graph import build_graph
    from app.llm_config import chat_model_name, llm_configured
    from app.nodes.rag_retrieval import reset_vectorstore_cache

    if not llm_configured():
        print(
            "ERROR: OPENAI_API_KEY is not set. Full evals need a real LLM "
            "(pattern_scoring raises without one). Set OPENAI_API_KEY in .env "
            "and re-run.",
            file=sys.stderr,
        )
        return 2

    reset_vectorstore_cache()

    graph = build_graph()
    chat_model = chat_model_name()
    print(f"Running {len(cases)} golden case(s) — chat={chat_model}\n")

    scores: list[EvalScore] = []
    for case in cases:
        run = run_single_case(graph, case.feature_id)
        score = score_run(run.state, case)
        scores.append(score)
        match = "MATCH" if score.tier_match else "MISMATCH"
        print(
            f"  {case.feature_id:<9} expected={score.expected_tier:<11} "
            f"observed={str(score.observed_tier):<11} {match:<8} "
            f"structure={score.structural:.2f} gen={score.cases_generated} "
            f"({run.elapsed_seconds}s)"
        )

    accuracy = round(sum(1 for s in scores if s.tier_match) / len(scores), 4)
    mean_structure = round(sum(s.structural for s in scores) / len(scores), 4)

    gates = [
        {
            "gate": "golden accuracy",
            "threshold": MIN_ACCURACY,
            "actual": accuracy,
            "passed": accuracy >= MIN_ACCURACY,
        },
        {
            "gate": "mean structural quality",
            "threshold": MIN_STRUCTURE,
            "actual": mean_structure,
            "passed": mean_structure >= MIN_STRUCTURE,
        },
    ]
    for s in scores:
        gates.append(
            {
                "gate": f"{s.feature_id}.structure",
                "threshold": MIN_STRUCTURE,
                "actual": s.structural,
                "passed": s.structural >= MIN_STRUCTURE,
            }
        )
    passed = all(g["passed"] for g in gates)

    _print_summary(gates, accuracy, mean_structure)

    return 0 if passed else 1


def _print_summary(gates, accuracy: float, mean_structure: float) -> None:
    print()
    print(f"{'gate':<28} {'threshold':>10} {'actual':>10}  status")
    print("-" * 56)
    for g in gates:
        print(f"{g['gate']:<28} {g['threshold']:>10} {g['actual']:>10}  {'PASS' if g['passed'] else 'FAIL'}")
    print()
    print(f"golden accuracy: {accuracy:.2f}  mean structural quality: {mean_structure:.2f}")
    print("PASS" if all(g["passed"] for g in gates) else "FAIL — one or more gates below threshold")


def main() -> int:
    return run_full(get_all_cases())


if __name__ == "__main__":
    sys.exit(main())
