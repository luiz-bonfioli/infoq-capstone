"""LangChain `@tool`-decorated functions for calling external systems
(Aha!, TestRail).

These are invoked directly by their corresponding LangGraph nodes
(`aha_extractor`, `testrail_publish`) - the graph's control flow decides
*when* to call them, not an LLM. Wrapping them as LangChain tools still
pays off: standardized `.invoke()` interface, automatic input-schema
validation from type hints/docstrings, and the option to later expose the
same tools to an LLM (e.g. `.bind_tools(...)`) if an agentic sub-flow is
ever added, without rewriting the integration logic.

Each tool lives in its own module (one external system per file); this
package re-exports them for convenient importing.
"""

from __future__ import annotations

from app.tools.aha_tools import get_aha_feature
from app.tools.testrail_tools import publish_test_cases_to_testrail

__all__ = ["get_aha_feature", "publish_test_cases_to_testrail"]
