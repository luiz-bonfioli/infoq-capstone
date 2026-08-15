"""LangChain `@tool`-decorated function for calling the Aha! API."""

from __future__ import annotations

from langchain_core.tools import tool

from app.mocks import get_mock_aha_feature


@tool
def get_aha_feature(feature_id: str) -> dict:
    """Retrieve an Aha! feature by ID, including description, acceptance
    criteria, comments, and attachments.

    Args:
        feature_id: Aha! feature identifier (e.g. "PROJ-123").

    Returns:
        Raw feature payload from the Aha! API.
    """
    # TODO: replace with a real Aha! REST API call (https://www.aha.io/api)
    # using feature_id. Until then, serve pre-configured mock data so the
    # pipeline can be exercised end-to-end (see app/mocks/aha_features.py).
    return get_mock_aha_feature(feature_id)
