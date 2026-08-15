# Company Standard: Feature Ticket Creation

Every feature delivered to engineering must start from a well-formed ticket. This document defines the
minimum standard for ticket creation across all product teams. Any deviation requires QA lead approval.

## Required Fields

Every ticket must be filled in completely before it is ready for grooming:

| Field | Requirement |
|---|---|
| Title | Outcome-focused, specific, unique |
| Description | Purpose + user-facing behavior |
| Acceptance Criteria | ≥ 2 concrete, testable criteria |
| Priority | High / Medium / Low, per the Priority table |
| Attachments / Links | Mockups, docs, or reproduction context where available |

## Title

Titles follow the pattern `<Component>: <outcome>` (e.g. `Billing: Allow invoice download as PDF`). Titles are:

- **Outcome-focused** — state what the user can do, not the technical mechanism.
- **Specific** — no vague wording such as "improve performance" or "fix bugs".
- **Unique** — never duplicate an existing or previously shipped ticket.

## Description

A ticket's description must answer:

- **What** the feature does and who it is for.
- **Why** it exists — the user problem it solves.
- **How** a user would interact with it (happy path).
- **Edge / error behavior** — what happens on invalid input or boundary conditions, where applicable.

## Acceptance Criteria

Acceptance criteria define *done* and are the contract for QA. They must:

- Be written in **Given / When / Then** or equivalent explicit format.
- Be **testable** — verifiable without subjective judgement.
- Cover the **happy path** and at least one **boundary, error, or edge condition**.
- Avoid vague statements such as "should work correctly" or "be fast".

| ❌ Weak | ✅ Strong |
|---|---|
| The feature should work correctly. | Given a valid invoice, When the user clicks Download as PDF, Then a PDF is saved locally. |
| Improve performance. | Given 10,000 records, When the list loads, Then it renders in under 2 seconds. |

## Priority

Priority is assigned by **user impact** and **frequency of use**, not implementation complexity:

| Priority | Definition |
|---|---|
| High | Blocks users or a core workflow; affects most users frequently |
| Medium | Important but has a workaround; moderate frequency |
| Low | Nice-to-have; rarely used or cosmetic |

## Definition of Done

A ticket is ready for work only when:

- [ ] Title follows the naming pattern and is specific.
- [ ] Description states what, why, and how.
- [ ] At least two concrete, testable acceptance criteria in explicit format.
- [ ] Criteria cover the happy path and error/boundary behavior.
- [ ] Priority is set per the Priority table.
- [ ] Any relevant attachments / links are included.
