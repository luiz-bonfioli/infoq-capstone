# Company Test Case & Ticket Patterns

This document is the single source of truth for how feature tickets and
test cases should be structured at our company. It is loaded by two parts
of the pipeline:

- `app/nodes/pattern_scoring.py` - scores a preprocessed Aha! ticket
  against these patterns (completeness + structure), producing
  `pattern_conformance` (`divergent` / `partial` / `conformant`).
- `app/knowledge_base.py` - seeds the RAG knowledge base used by
  `rag_retrieval`/`llm_generation` to ground generated test cases in these
  same standards.

Keeping both in sync with one file avoids the scoring step and the
generation step disagreeing about what "good" looks like.

## Ticket Completeness Standards

- A ticket must have a non-empty **description** explaining the feature's
  purpose and user-facing behavior.
- A ticket must have at least **two concrete, testable acceptance
  criteria** written in a Given/When/Then or equivalent explicit format
  (not vague statements like "should work correctly").
- Acceptance criteria should cover both the primary/happy-path behavior
  and at least one boundary, error, or edge condition where applicable.
- Ambiguous or placeholder tickets (e.g. "improve performance", "fix
  bugs") without measurable acceptance criteria are considered
  **divergent** from company patterns, regardless of description length.

## Test Case Structure Standards

- Every test case must include **preconditions**, **numbered steps**, and
  exactly **one explicit expected result** per test case (or per step for
  multi-assertion cases).
- Test case titles follow the pattern
  `<Feature> - <Scenario> - <Expected outcome>` for TestRail consistency.
- Priority (`High`/`Medium`/`Low`) is assigned based on **user impact and
  frequency of use**, not implementation complexity.

## Coverage Standards

- For every feature, test cases must cover at least:
  - One **happy path** scenario.
  - One **negative** scenario (invalid input).
  - One **edge case** (boundary values, empty state, or concurrency),
    where applicable to the feature.

## How Scoring Maps to These Patterns

| Score | Meaning |
|---|---|
| `conformant` | Ticket has a clear description and multiple concrete, testable acceptance criteria that already give enough detail to derive happy-path, negative, and edge-case test cases without extra grounding. |
| `partial` | Ticket has a description and at least one acceptance criterion, but lacks enough detail/coverage to confidently derive all required test case categories (negative/edge cases) without additional context. |
| `divergent` | Ticket is missing a real description and/or has no acceptance criteria at all - not enough signal to reliably generate test cases. |
