"""Node: Document Preprocessing.

Converts the raw Aha! feature payload (`feature_raw`) into structured
Markdown plus lightweight metadata, so downstream nodes (`pattern_scoring`,
`rag_retrieval`, `llm_generation`) have consistent, readable content to
work with regardless of the raw payload's shape.

TODO: Extract and parse attachments (images, PDFs, etc.) once the real
Aha! extractor returns attachment content/URLs, and derive richer metadata
(product area, tags) as those fields become available upstream.
"""

from __future__ import annotations

from app.nodes.utils import safe_node
from app.state import PipelineState


def _to_markdown(feature_raw: dict) -> str:
    """Render a raw Aha! feature payload as structured Markdown."""
    if not feature_raw:
        return ""

    name = feature_raw.get("name", "Untitled feature")
    description = feature_raw.get("description", "").strip()
    acceptance_criteria = feature_raw.get("acceptance_criteria", [])
    comments = feature_raw.get("comments", [])
    attachments = feature_raw.get("attachments", [])

    lines = [f"# {name}", ""]

    lines.append("## Description")
    lines.append(description or "_(no description provided)_")
    lines.append("")

    lines.append("## Acceptance Criteria")
    if acceptance_criteria:
        lines.extend(f"- {criterion}" for criterion in acceptance_criteria)
    else:
        lines.append("_(no acceptance criteria provided)_")
    lines.append("")

    lines.append("## Comments")
    if comments:
        lines.extend(f"- {comment}" for comment in comments)
    else:
        lines.append("_(no comments)_")
    lines.append("")

    lines.append("## Attachments")
    if attachments:
        lines.extend(f"- {attachment}" for attachment in attachments)
    else:
        lines.append("_(no attachments)_")

    return "\n".join(lines)


@safe_node("preprocessing")
def preprocessing(state: PipelineState) -> dict:
    """Normalize raw Aha! content into Markdown + metadata.

    Args:
        state: Current pipeline state. Requires `feature_raw`.

    Returns:
        Partial state update with `feature_markdown` and `feature_metadata`.
    """
    feature_raw = state.get("feature_raw", {})

    feature_markdown = _to_markdown(feature_raw)
    feature_metadata = {
        "has_description": bool(feature_raw.get("description", "").strip()),
        "acceptance_criteria_count": len(feature_raw.get("acceptance_criteria", [])),
        "comment_count": len(feature_raw.get("comments", [])),
        "attachment_count": len(feature_raw.get("attachments", [])),
    }

    return {
        "feature_markdown": feature_markdown,
        "feature_metadata": feature_metadata,
    }
