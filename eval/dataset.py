"""Golden evaluation data set.

A curated set of mock Aha! feature tickets annotated with the tier the system
*should* assign, guided by the "Ticket Completeness Standard":

- empty description AND no criteria  -> 'divergent'
- >= 2 concrete acceptance criteria  -> 'conformant'
- otherwise                          -> 'partial'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConformanceTier = Literal["divergent", "partial", "conformant"]


@dataclass(frozen=True)
class EvalCase:
    feature_id: str
    expected_tier: ConformanceTier
    description: str


def get_all_cases() -> list[EvalCase]:
    """The full golden data set."""
    return [
        EvalCase(
            "AHA-201", "divergent",
            "Empty ticket — the hard routing path (RAG + human gate)",
        ),
        EvalCase(
            "AHA-202", "partial",
            "Thin ticket (1 concrete criterion)",
        ),
        EvalCase(
            "AHA-203", "partial",
            "Thin ticket (1 criterion)",
        ),
        EvalCase(
            "AHA-204", "partial",
            "Thin ticket (1 criterion + attachment)",
        ),
        EvalCase(
            "AHA-205", "conformant",
            "Rich ticket (3 criteria)",
        ),
        EvalCase(
            "AHA-206", "conformant",
            "Rich ticket (4 criteria)",
        ),
    ]


__all__ = [
    "ConformanceTier",
    "EvalCase",
    "get_all_cases",
]
