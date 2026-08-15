"""LangChain `@tool`-decorated function for calling the TestRail API."""

from __future__ import annotations

from langchain_core.tools import tool

from app.mocks import get_mock_case_result, get_mock_testrail_run


@tool
def publish_test_cases_to_testrail(feature_id: str, test_cases: list[dict]) -> dict:
    """Publish approved test cases to TestRail as a new test run.

    Args:
        feature_id: Aha! feature identifier the test cases were generated from.
        test_cases: List of structured test cases to publish.

    Returns:
        Dict with the created TestRail run id/url and a per-test-case
        `results` list (each shaped like `{"title", "status", "testrail_case_id", "error"}`,
        status being "created" or "error"), e.g.:
        {"testrail_run_id": "R123", "url": "...", "results": [...]}
    """
    # TODO: replace with a real TestRail API call (add_run, then add_case per
    # test case) using feature_id and test_cases. Until then, serve
    # pre-configured mock responses so the pipeline can be exercised
    # end-to-end (see app/mocks/testrail_runs.py), including per-case
    # created/error outcomes.
    run = get_mock_testrail_run(feature_id)
    results = [
        get_mock_case_result(run["testrail_run_id"], index, test_case)
        for index, test_case in enumerate(test_cases)
    ]
    return {**run, "results": results}
