"""Node: TestRail Integration.

Calls the `publish_test_cases_to_testrail` LangChain tool (`app/tools/`)
to publish approved test cases to TestRail, and records a per-test-case
created/error result for display (see `app/console.py`).
"""

from __future__ import annotations

from app.nodes.utils import safe_node
from app.state import PipelineState
from app.tools import publish_test_cases_to_testrail


@safe_node("testrail_publish")
def testrail_publish(state: PipelineState) -> dict:
    """Publish approved test cases to TestRail.

    Args:
        state: Current pipeline state. Requires `generated_test_cases` and
            `review_decision == "approved"`.

    Returns:
        Partial state update with `testrail_run_id`, `testrail_results`
        (per-test-case created/error status), and `published`.
    """
    result = publish_test_cases_to_testrail.invoke(
        {
            "feature_id": state["aha_feature_id"],
            "test_cases": state.get("generated_test_cases", []),
        }
    )

    return {
        "testrail_run_id": result["testrail_run_id"],
        "testrail_results": result.get("results", []),
        "published": True,
    }
