"""Static seed knowledge base used by `rag_retrieval` for RAG grounding.

Two kinds of company knowledge live here:

1. **Test-case / ticket standards** (`source: company_patterns.md`) - the
   rubric `pattern_scoring` uses to score ticket conformance (see
   `app/company_patterns.py`), split into one `Document` per section so
   retrieval can surface just the relevant part (naming, coverage,
   structure, etc.) instead of the whole file.
2. **Problem-domain knowledge** (`source: company_knowledge.md`) - how the
   company addresses each problem area its features touch (performance,
   authentication, file uploads, exports, notifications, RBAC, search,
   billing, rate limiting, audit logging, theming, ...). This is the
   "additional info about the problem" a weak ticket is missing: when a
   ticket is thin on detail, retrieval grounds generation with the company
   knowledge that addresses the ticket's problem domain.

TODO: Replace this hardcoded seed list with a real ingestion pipeline that
loads company standards, previous test cases, testing guidelines, and
product documentation into a persistent vector store (e.g. pgvector,
Pinecone, Chroma) - see project.md's "Knowledge Sources".
"""

from __future__ import annotations

from langchain_core.documents import Document

COMPANY_KNOWLEDGE_SEED: list[Document] = [
    # --- Test-case / ticket standards (scoring rubric + generation grounding) ---
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
    # --- Problem-domain knowledge (addresses the problem a ticket describes) ---
    Document(
        page_content=(
            "Company knowledge - Performance: UI pages must render their first meaningful "
            "content within 2 seconds on the reference hardware and network profile. "
            "Large result sets are paginated or virtualized server-side; load time must be "
            "tested with the maximum supported data volume, and empty/loading/error states "
            "are part of the acceptance criteria."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:performance"},
    ),
    Document(
        page_content=(
            "Company knowledge - Authentication & SSO: Enterprise customers authenticate via "
            "company SSO (SAML/OIDC). SSO sessions expire per the identity provider's policy; "
            "the app must surface a clear retry path on expired/invalid sessions and never "
            "silently fall back to weaker credentials. Account security (2FA/TOTP) is a "
            "supported feature and follows the same session-expiry rules."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:authentication"},
    ),
    Document(
        page_content=(
            "Company knowledge - File uploads: Uploaded files are validated for type, size, and "
            "content before storage. Company limits: images up to 5MB, other files up to 25MB. "
            "Files are processed asynchronously (e.g. thumbnail/avatar cropping) and the UI "
            "must handle in-progress, success, and failure states."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:file_uploads"},
    ),
    Document(
        page_content=(
            "Company knowledge - Bulk export: Exports (CSV/PDF/audit logs) are capped at "
            "10,000 rows per request; larger requests must warn the user and cap the result. "
            "Exports respect the current view filters and are generated server-side with "
            "consistent column ordering. Empty result sets export a header-only file without error."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:bulk_export"},
    ),
    Document(
        page_content=(
            "Company knowledge - Notifications & email: Notification delivery is per-user "
            "and per-category, opt-in by default for new categories. Scheduled emails honor "
            "the configured time and timezone, skip invalid recipients with a logged warning, "
            "and every send attempt is logged for audit. Mentions (@user) notify the target "
            "only when they have access to the item."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:notifications"},
    ),
    Document(
        page_content=(
            "Company knowledge - Roles & permissions (RBAC): Access is enforced per user role "
            "(Viewer, Editor, Admin). Viewers read-only, Editors edit content but not "
            "permissions, Admins full access including role assignment. A user with no role "
            "sees an empty list with an access-denied message - never a partial view."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:rbac"},
    ),
    Document(
        page_content=(
            "Company knowledge - Search: Search results are paginated (25 per page by default) "
            "and respect the active filters. Empty queries show the full default list; queries "
            "with no matches show an explicit 'no results' state. Pagination controls are hidden "
            "when the result set fits on one page."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:search"},
    ),
    Document(
        page_content=(
            "Company knowledge - Billing & multi-currency: Prices display in the user's local "
            "currency converted with daily exchange rates and rounded per the currency's "
            "convention. Unsupported currencies fall back to USD. Exchange rates must refresh "
            "at least once every 24 hours."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:billing"},
    ),
    Document(
        page_content=(
            "Company knowledge - API rate limiting: Public API requests are limited to "
            "100 requests/minute per API key. Exceeding the limit returns HTTP 429 with a "
            "Retry-After header; the limit is enforced per key, not per IP. Tests must verify "
            "the reset window restores access."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:api_rate_limiting"},
    ),
    Document(
        page_content=(
            "Company knowledge - Audit logging: Audit logs capture who did what and when for "
            "admin operations (exports, permission changes, scheduled emails). Audit log exports "
            "retain an access log for at least 1 year, and an empty date range exports a "
            "header-only file."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:audit_logging"},
    ),
    Document(
        page_content=(
            "Company knowledge - Theming/dark mode: The app supports a light/dark theme toggle "
            "persisted per user across sessions. On first visit the app follows the system "
            "preference. All surfaces must be legible in both themes with no hardcoded colors."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:theming"},
    ),
    Document(
        page_content=(
            "Company knowledge - Password security: Password strength is evaluated live while "
            "the user types (weak/medium/strong) using the standard 3-bar meter. Weak is under "
            "8 characters or single character class; strong requires mixed case, numbers, and "
            "symbols. Invalid codes or passwords are limited to 5 attempts before a temporary lock."
        ),
        metadata={"source": "company_knowledge.md", "category": "domain:password_security"},
    ),
]
