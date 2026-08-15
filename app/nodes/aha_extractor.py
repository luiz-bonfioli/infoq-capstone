"""Node: Aha! Extractor.

Calls the `get_aha_feature` LangChain tool (`app/tools.py`) to fetch the
raw feature payload for `state["aha_feature_id"]`.
"""

from __future__ import annotations

from app.nodes.utils import safe_node
from app.state import PipelineState
from app.tools import get_aha_feature


@safe_node("aha_extractor")
def aha_extractor(state: PipelineState) -> dict:
    """Retrieve raw feature content from Aha!.

    Args:
        state: Current pipeline state. Requires `aha_feature_id`.

    Returns:
        Partial state update with `feature_raw`.
    """
    feature_raw = get_aha_feature.invoke({"feature_id": state["aha_feature_id"]})

    return {"feature_raw": feature_raw}
