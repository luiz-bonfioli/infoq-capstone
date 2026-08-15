"""Static seed knowledge base used by `rag_retrieval` for RAG grounding.

Sourced from `company_patterns.md` (the same file `pattern_scoring` uses
to score ticket conformance - see `app/company_patterns.py`), split into
one `Document` per section so retrieval can surface just the relevant
part (naming, coverage, structure, etc.) instead of the whole file.

TODO: Replace this hardcoded seed list with a real ingestion pipeline that
loads company standards, previous test cases, testing guidelines, and
product documentation into a persistent vector store (e.g. pgvector,
Pinecone, Chroma) - see project.md's "Knowledge Sources".
"""

from __future__ import annotations

from langchain_core.documents import Document

COMPANY_KNOWLEDGE_SEED: list[Document] = [
    Document(
        page_content=(
            "Company Standard: Every test case must include preconditions, "
            "numbered steps, and one explicit expected result per step."
        ),
        metadata={"source": "company_patterns.md", "category": "test_case_structure"},
    ),
    Document(
        page_content=(
            "Testing Guideline: For every feature, cover at least one negative "
            "scenario (invalid input) and one edge case (boundary values, "
            "empty state, concurrency) in addition to the happy path."
        ),
        metadata={"source": "company_patterns.md", "category": "coverage"},
    ),
    Document(
        page_content=(
            "Company Standard: Test case titles follow the pattern "
            "'<Feature> - <Scenario> - <Expected outcome>' for TestRail consistency."
        ),
        metadata={"source": "company_patterns.md", "category": "naming"},
    ),
    Document(
        page_content=(
            "Testing Guideline: Assign priority (High/Medium/Low) based on user "
            "impact and frequency of use, not implementation complexity."
        ),
        metadata={"source": "company_patterns.md", "category": "prioritization"},
    ),
    Document(
        page_content=(
            "Ticket Completeness Standard: A ticket must have a non-empty description and at least two "
            "concrete, testable acceptance criteria in Given/When/Then or equivalent explicit format. "
            "Ambiguous/placeholder tickets without measurable acceptance criteria are divergent from "
            "company patterns regardless of description length."
        ),
        metadata={"source": "company_patterns.md", "category": "ticket_completeness"},
    ),
]
