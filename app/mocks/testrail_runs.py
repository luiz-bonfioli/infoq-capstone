"""Pre-configured mock TestRail responses.

Used by `app/tools/testrail_tools.py` as a stand-in for the real TestRail
API while that integration is still a TODO. Each entry mimics the shape of
a real "add_run" response.
"""

from __future__ import annotations

import hashlib

TESTRAIL_RUN_MOCKS: list[dict] = [
    {"testrail_run_id": "R-1001", "url": "https://example.testrail.io/index.php?/runs/view/1001"},
    {"testrail_run_id": "R-1002", "url": "https://example.testrail.io/index.php?/runs/view/1002"},
    {"testrail_run_id": "R-1003", "url": "https://example.testrail.io/index.php?/runs/view/1003"},
    {"testrail_run_id": "R-1004", "url": "https://example.testrail.io/index.php?/runs/view/1004"},
    {"testrail_run_id": "R-1005", "url": "https://example.testrail.io/index.php?/runs/view/1005"},
    {"testrail_run_id": "R-1006", "url": "https://example.testrail.io/index.php?/runs/view/1006"},
    {"testrail_run_id": "R-1007", "url": "https://example.testrail.io/index.php?/runs/view/1007"},
    {"testrail_run_id": "R-1008", "url": "https://example.testrail.io/index.php?/runs/view/1008"},
    {"testrail_run_id": "R-1009", "url": "https://example.testrail.io/index.php?/runs/view/1009"},
    {"testrail_run_id": "R-1010", "url": "https://example.testrail.io/index.php?/runs/view/1010"},
]


def get_mock_testrail_run(feature_id: str) -> dict:
    """Deterministically pick a mock TestRail run response for a feature id.

    Using a stable hash of `feature_id` (instead of Python's randomized
    `hash()` or a random choice) keeps repeated calls for the same feature
    id stable both within and across process runs, which is useful for
    manual testing and demos.

    Args:
        feature_id: Aha! feature identifier the test cases were generated from.

    Returns:
        A mock response shaped like a real TestRail "add_run" API response.
    """
    digest = hashlib.sha256(feature_id.encode("utf-8")).hexdigest()
    index = int(digest, 16) % len(TESTRAIL_RUN_MOCKS)
    return TESTRAIL_RUN_MOCKS[index]


def get_mock_case_result(run_id: str, index: int, test_case: dict) -> dict:
    """Deterministically mock the "add_case" outcome for one test case.

    Mimics a real per-case TestRail response: most cases are created
    successfully with a `testrail_case_id`; a case is mocked as failed
    (`status: "error"`) only if it is missing a required field (title,
    steps, or expected_result), simulating a validation error from the
    real API. This keeps the mock deterministic and realistic without
    randomly failing well-formed cases.

    Args:
        run_id: The TestRail run id the case is being added to.
        index: 0-based position of this test case in the batch (used to
            derive a stable mock case id).
        test_case: The structured test case being published.

    Returns:
        A dict shaped like `TestCaseResult` (see app/state.py).
    """
    title = test_case.get("title") or ""
    missing = [
        field
        for field in ("title", "steps", "expected_result")
        if not test_case.get(field)
    ]
    if missing:
        return {
            "title": title or f"(untitled test case #{index + 1})",
            "status": "error",
            "testrail_case_id": None,
            "error": f"Missing required field(s): {', '.join(missing)}",
        }

    case_id = f"{run_id}-C{index + 1}"
    return {
        "title": title,
        "status": "created",
        "testrail_case_id": case_id,
        "error": None,
    }

