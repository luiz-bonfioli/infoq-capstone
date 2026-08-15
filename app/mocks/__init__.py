"""Mock response fixtures for external-system tools (Aha!, TestRail).

These stand in for the real APIs while `app/tools/aha_tools.py` and
`app/tools/testrail_tools.py` are still TODOs, so the pipeline can be
exercised end-to-end with realistic-looking data.
"""

from __future__ import annotations

from app.mocks.aha_features import get_mock_aha_feature
from app.mocks.testrail_runs import get_mock_case_result, get_mock_testrail_run

__all__ = ["get_mock_aha_feature", "get_mock_testrail_run", "get_mock_case_result"]
