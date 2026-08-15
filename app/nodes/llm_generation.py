"""Node: LLM Test Case Generation.

Prompts a LangChain chat model with the feature Markdown + retrieved RAG
context (when available) to produce structured, TestRail-ready test cases,
using `.with_structured_output(...)` so the model's response is parsed
directly into `TestCase` objects (no manual JSON parsing/repair needed).

TODO: Tune the prompt/model choice, add few-shot examples from previous
TestRail test cases, and expand schema validation (e.g. minimum step
count) once real usage data is available.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from app.llm_config import build_http_client, llm_configured
from app.nodes.utils import safe_node
from app.state import PipelineState, TestCase

logger = logging.getLogger(__name__)


class GeneratedTestCase(BaseModel):
    title: str = Field(description="Format: '<Feature> - <Scenario> - <Expected outcome>'")
    preconditions: str = Field(description="State required before executing the test steps")
    steps: list[str] = Field(description="Ordered, numbered test steps")
    expected_result: str = Field(description="Overall expected outcome of the test case")
    priority: str = Field(description="High, Medium, or Low")
    tags: list[str] = Field(default_factory=list, description="e.g. 'positive', 'negative', 'edge-case'")


class TestCaseBatch(BaseModel):
    test_cases: list[GeneratedTestCase]


_PROMPT_TEMPLATE = """You are a senior QA engineer generating TestRail test cases from a feature ticket.

Feature (Markdown):
{feature_markdown}

Relevant company standards / guidelines / prior test cases (RAG context):
{retrieved_context}

{feedback_section}

Generate a comprehensive set of test cases covering the happy path, negative scenarios (invalid input,
error handling), and edge cases (boundary values, empty state, concurrency where applicable). Follow the
company standards above for structure, naming, and prioritization.
"""


def _build_prompt(state: PipelineState) -> str:
    context_text = "\n".join(
        f"- {c['content']}" for c in state.get("retrieved_context", [])
    ) or "(no additional context retrieved)"

    feedback_section = ""
    if state.get("review_feedback"):
        feedback_section = (
            f"A previous attempt was rejected by a human reviewer with this feedback, "
            f"address it in this revision:\n{state['review_feedback']}\n"
        )

    return _PROMPT_TEMPLATE.format(
        feature_markdown=state.get("feature_markdown") or "(empty)",
        retrieved_context=context_text,
        feedback_section=feedback_section,
    )


@safe_node("llm_generation")
def llm_generation(state: PipelineState) -> dict:
    """Generate structured test cases grounded in retrieved context.

    Args:
        state: Current pipeline state. Requires `feature_markdown` and
            `retrieved_context`.

    Returns:
        Partial state update with `generated_test_cases` and an incremented
        `retry_count` (used by `route_after_review` to cap the
        reject-and-regenerate loop).
    """
    generated_test_cases: list[TestCase]

    if not llm_configured():
        logger.warning("OPENAI_API_KEY not set - skipping real generation, returning empty test cases.")
        generated_test_cases = []
    else:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model="gpt-4o-mini", temperature=0, http_client=build_http_client()
        ).with_structured_output(TestCaseBatch)
        prompt = _build_prompt(state)
        batch: TestCaseBatch = llm.invoke(prompt)
        generated_test_cases = [tc.model_dump() for tc in batch.test_cases]

    return {
        "generated_test_cases": generated_test_cases,
        "retry_count": state.get("retry_count", 0) + 1,
    }
