"""Pre-configured mock Aha! feature payloads, keyed by feature id.

Used by `app/tools/aha_tools.py` as a stand-in for the real Aha! API while
that integration is still a TODO. Each entry mimics the shape of a real
Aha! feature response: description, acceptance criteria, comments, and
attachments.
"""

from __future__ import annotations

AHA_FEATURE_MOCKS: dict[str, dict] = {
    "AHA-101": {
        "id": "AHA-101",
        "name": "User login with SSO",
        "description": "Allow users to authenticate via company SSO (SAML) instead of local passwords.",
        "acceptance_criteria": [
            "Given a valid SSO account, when the user clicks 'Login with SSO', they are redirected and logged in.",
            "Given an invalid/expired SSO session, the user sees a clear error and can retry.",
        ],
        "comments": ["QA: please cover session expiry and revoked accounts."],
        "attachments": [],
    },
    "AHA-102": {
        "id": "AHA-102",
        "name": "Bulk export to CSV",
        "description": "Users can export a filtered list of records to CSV, up to 10,000 rows.",
        "acceptance_criteria": [
            "Given a filtered list, when the user clicks Export, a CSV downloads with matching rows.",
            "Given more than 10,000 matching rows, the user is warned and export is capped.",
        ],
        "comments": [],
        "attachments": ["export-mockup.png"],
    },
    "AHA-103": {
        "id": "AHA-103",
        "name": "Password strength meter",
        "description": "Show a live strength meter (weak/medium/strong) while users set a new password.",
        "acceptance_criteria": [
            "Given a password under 8 characters, the meter shows 'weak'.",
            "Given a password with mixed case, numbers, and symbols, the meter shows 'strong'.",
        ],
        "comments": ["Design: use the standard 3-bar meter component."],
        "attachments": [],
    },
    "AHA-104": {
        "id": "AHA-104",
        "name": "Notification preferences",
        "description": "Users can opt in/out of email and in-app notifications per category.",
        "acceptance_criteria": [
            "Given a user disables a category, no further notifications of that type are sent.",
            "Given a new notification category is added, users default to opted-in.",
        ],
        "comments": [],
        "attachments": [],
    },
    "AHA-105": {
        "id": "AHA-105",
        "name": "API rate limiting",
        "description": "Public API requests are limited to 100 requests/minute per API key.",
        "acceptance_criteria": [
            "Given a client exceeds the limit, they receive HTTP 429 with a Retry-After header.",
            "Given the limit window resets, the client can make requests again.",
        ],
        "comments": ["Security: ensure limit is enforced per key, not per IP."],
        "attachments": [],
    },
    "AHA-106": {
        "id": "AHA-106",
        "name": "Dark mode",
        "description": "Add a dark mode theme toggle, persisted per user across sessions.",
        "acceptance_criteria": [
            "Given a user enables dark mode, the preference persists after logout/login.",
            "Given system preference is dark, the app defaults to dark mode on first visit.",
        ],
        "comments": [],
        "attachments": ["dark-mode-palette.pdf"],
    },
    "AHA-107": {
        "id": "AHA-107",
        "name": "Multi-currency pricing",
        "description": "Display prices in the user's local currency using daily exchange rates.",
        "acceptance_criteria": [
            "Given a supported currency, prices are converted and rounded per that currency's convention.",
            "Given an unsupported currency, the app falls back to USD.",
        ],
        "comments": ["Finance: rates must refresh at least once every 24h."],
        "attachments": [],
    },
    "AHA-108": {
        "id": "AHA-108",
        "name": "Two-factor authentication",
        "description": "Users can enable TOTP-based 2FA for their account.",
        "acceptance_criteria": [
            "Given 2FA is enabled, login requires a valid 6-digit TOTP code.",
            "Given an invalid code is entered 5 times, the account is temporarily locked.",
        ],
        "comments": [],
        "attachments": [],
    },
    "AHA-109": {
        "id": "AHA-109",
        "name": "Audit log export",
        "description": "Admins can export the account's audit log for a given date range.",
        "acceptance_criteria": [
            "Given a valid date range, the exported log contains all matching events.",
            "Given an empty date range (no events), the export succeeds with a header-only file.",
        ],
        "comments": ["Compliance: retain exported files' access log for 1 year."],
        "attachments": [],
    },
    "AHA-110": {
        "id": "AHA-110",
        "name": "Inline comment mentions",
        "description": "Users can @mention teammates in comments, triggering a notification.",
        "acceptance_criteria": [
            "Given a valid @mention, the mentioned user receives a notification.",
            "Given a mention of a user without access to the item, no notification is sent.",
        ],
        "comments": [],
        "attachments": [],
    },
    # --- Pattern-score test fixtures (AHA-2xx) -----------------------------
    # Purpose-built to exercise all three `pattern_conformance` outcomes
    # (no description/criteria -> "divergent", <2 criteria -> "partial",
    # >=2 criteria + description -> "conformant"), so the confirm_low_score
    # gate and decide_rag_usage branches can all be tested. The LLM scorer
    # may judge a fixture slightly differently than the expected tier.
    "AHA-201": {
        "id": "AHA-201",
        "name": "Untitled backlog item",
        "description": "",
        "acceptance_criteria": [],
        "comments": [],
        "attachments": [],
    },
    "AHA-202": {
        "id": "AHA-202",
        "name": "Improve performance",
        "description": "Make the reports page load faster.",
        "acceptance_criteria": [
            "Given the reports page, when it loads, it should feel faster than before.",
        ],
        "comments": ["Placeholder ticket - needs proper acceptance criteria before grooming."],
        "attachments": [],
    },
    "AHA-203": {
        "id": "AHA-203",
        "name": "Add pagination to search results",
        "description": "Search results should be paginated instead of showing everything on one page.",
        "acceptance_criteria": [
            "Given more than 25 results, the page shows pagination controls.",
        ],
        "comments": [],
        "attachments": [],
    },
    "AHA-204": {
        "id": "AHA-204",
        "name": "Allow profile picture upload",
        "description": "Users can upload a profile picture from the account settings page.",
        "acceptance_criteria": [
            "Given a valid image file under 5MB, the upload succeeds and the avatar updates.",
        ],
        "comments": ["Design: crop to a square before upload."],
        "attachments": ["avatar-upload-mock.png"],
    },
    "AHA-205": {
        "id": "AHA-205",
        "name": "Scheduled report emails",
        "description": (
            "Admins can schedule a report to be emailed to a list of recipients daily, weekly, or monthly, "
            "at a configurable time."
        ),
        "acceptance_criteria": [
            "Given a daily schedule, the report email is sent once per day at the configured time.",
            "Given a recipient list with an invalid email address, that address is skipped and logged, "
            "and valid recipients still receive the report.",
            "Given the admin disables the schedule, no further emails are sent until re-enabled.",
        ],
        "comments": ["Ops: log every send attempt (success/failure) for auditing."],
        "attachments": ["schedule-config-mockup.png"],
    },
    "AHA-206": {
        "id": "AHA-206",
        "name": "Role-based access control for reports",
        "description": (
            "Restrict report visibility based on the user's assigned role (Viewer, Editor, Admin), so "
            "users only see reports they're permitted to access."
        ),
        "acceptance_criteria": [
            "Given a user with the Viewer role, they can view but not edit or delete any report.",
            "Given a user with the Editor role, they can view and edit reports but not change permissions.",
            "Given a user with the Admin role, they have full access including managing role assignments.",
            "Given a user without any assigned role, they see an empty report list with an access-denied message.",
        ],
        "comments": [],
        "attachments": [],
    },
}

DEFAULT_AHA_FEATURE_MOCK: dict = {
    "id": "UNKNOWN",
    "name": "Untitled feature",
    "description": "No mock data configured for this feature id.",
    "acceptance_criteria": [],
    "comments": [],
    "attachments": [],
}


def get_mock_aha_feature(feature_id: str) -> dict:
    """Look up a mock Aha! feature payload, falling back to a generic default.

    Args:
        feature_id: Aha! feature identifier (e.g. "AHA-101").

    Returns:
        A mock feature payload shaped like a real Aha! API response.
    """
    mock = AHA_FEATURE_MOCKS.get(feature_id, DEFAULT_AHA_FEATURE_MOCK)
    return {**mock, "id": feature_id if mock is DEFAULT_AHA_FEATURE_MOCK else mock["id"]}
