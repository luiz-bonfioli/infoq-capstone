"""Loader for `company_patterns.md`, the single source of truth for ticket
and test case standards.

Used by both `app/nodes/pattern_scoring.py` (to score ticket conformance)
and `app/knowledge_base.py` (to ground RAG-based test case generation), so
scoring and generation are judged against the exact same documented
patterns instead of drifting apart.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

COMPANY_PATTERNS_PATH = Path(__file__).resolve().parent.parent / "company_patterns.md"


@lru_cache(maxsize=1)
def load_company_patterns() -> str:
    """Read `company_patterns.md` from the project root.

    Returns:
        The full Markdown contents, or a short fallback notice if the file
        is missing (so the pipeline degrades gracefully rather than
        crashing if the file is ever deleted/renamed).
    """
    try:
        return COMPANY_PATTERNS_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "_(company_patterns.md not found - no company patterns loaded)_"
