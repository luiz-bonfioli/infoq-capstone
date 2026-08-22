"""Step-by-step console visualization of the graph as it runs.

A LangChain callback handler (`GraphProgressLogger`) that renders one styled
line per graph event, so the operator can see exactly where the run is in the
pipeline - which node is executing, when it pauses for a human decision, what
was decided, and how the run ended:

    → START
    → aha_extractor
    ✓ preprocessing
    → pattern_scoring
    ⏸ confirm_low_score        waiting for human decision…
    ▸ confirm_low_score        resumed…
    ✓ confirm_low_score        decision=continue
    → rag_retrieval
    → llm_generation
    ⏸ human_review             waiting for test case approval…
    ✓ human_review             decision=approved
    → testrail_publish
    ✓ PUBLISHED                run=1234

The handler is attached via `config={"callbacks": [handler]}` and the same
instance is reused across `graph.invoke` / `Command(resume=...)` calls so the
timeline is continuous across interrupt pauses (see `app/main.py`).

Node identity comes from the `langgraph_node` metadata that LangGraph attaches
to each node's chain run. Pauses are detected in `on_chain_error` when the
raised exception is a `GraphInterrupt` - it carries the `Interrupt` payload,
so the wait reason is available right there - and resumes are detected in
`on_chain_start` when the starting node is the one currently paused.

Because a node's `on_chain_end` can be immediately followed by an interrupt,
completion lines are deferred: the `✓` is only emitted when the *next* node
starts (or the graph ends), so a pause correctly renders as `⏸` instead.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.errors import GraphInterrupt

from app.console import console
from app.nodes.utils import MAX_RETRIES

# interrupt payload `type` -> human-readable "waiting for …" reason
_WAIT_REASONS = {
    "pattern_score_confirmation": "human decision",
    "test_case_review": "test case approval",
}


def _interrupt_value(error: GraphInterrupt) -> dict:
    """Extract the interrupt payload dict from a `GraphInterrupt`.

    A node's `interrupt(value)` surfaces in `on_chain_error` as a
    `GraphInterrupt` whose `.args` is a nested tuple of `Interrupt` objects
    (each carrying the payload as `.value`), e.g.
    `error.args == ((Interrupt(value={'type': ...}, id=...),),)`. Flatten it
    and return the first payload dict (or `{}` if none is present).
    """
    for arg in error.args or ():
        items = arg if isinstance(arg, tuple) else (arg,)
        for item in items:
            value = getattr(item, "value", None)
            if isinstance(value, dict):
                return value
    return {}


class GraphProgressLogger(BaseCallbackHandler):
    """Render one console line per graph event (start / complete / pause / resume / end)."""

    def __init__(self) -> None:
        super().__init__()
        self._node_by_run: dict[UUID, str] = {}     # run_id -> node name
        self._current: str | None = None            # node currently executing
        self._paused: str | None = None             # node awaiting resume
        self._resumed: str | None = None            # node we printed "▸ resumed…" for
        self._last_started: str | None = None       # last node that printed "→"
        self._pause_printed: set[str] = set()       # nodes whose "⏸" line was rendered
        self._pending: dict[str, dict] = {}         # node -> last output, awaiting ✓/⏸
        self._interrupt_value: dict[str, dict] = {}  # node -> interrupt payload
        self._started = False                       # already printed "→ START"

    # -- small helpers -----------------------------------------------------

    def _emit(self, text: str) -> None:
        console.print(text)

    def _interrupt_payload(self, node: str) -> dict:
        return self._interrupt_value.get(node, {})

    def _wait_reason(self, node: str) -> str:
        value = self._interrupt_payload(node)
        return _WAIT_REASONS.get(value.get("type", ""), value.get("type", "input"))

    def _detail(self, node: str, outputs: dict) -> str:
        """Trailing ` {detail}` for a completed node's `✓` line."""
        if node == "pattern_scoring" and outputs.get("pattern_conformance"):
            return f"  [dim]score={outputs['pattern_conformance']}[/dim]"
        if node == "confirm_low_score" and outputs.get("score_review_decision"):
            return f"  [dim]decision={outputs['score_review_decision']}[/dim]"
        if node == "human_review" and outputs.get("review_decision"):
            parts = [f"[dim]decision={outputs['review_decision']}[/dim]"]
            if outputs["review_decision"] == "rejected":
                retry = self._interrupt_payload(node).get("retry_count", 0)
                parts.append(f"[dim]retry {retry}/{MAX_RETRIES}[/dim]")
            return "  " + "  ".join(parts)
        if node == "error_handler":
            error = outputs.get("error")
            return f"  [dim]error: {error}[/dim]" if error else ""
        return ""

    # -- render rules ------------------------------------------------------

    def _complete_node(self, node: str) -> None:
        """Print the deferred `✓` line for a node that truly finished."""
        outputs = self._pending.pop(node, {}) or {}
        self._pause_printed.discard(node)  # a re-pause (retry loop) must print again
        self._emit(f"[bold green]✓ {node}[/bold green]{self._detail(node, outputs)}")

    def _pause_node(self, node: str) -> None:
        """Mark a node paused and print its `⏸` line (once per pause)."""
        if self._paused == node and node in self._pause_printed:
            return  # guard against a duplicated GraphInterrupt error event
        self._pending.pop(node, None)
        self._paused = node
        if node not in self._pause_printed:
            self._pause_printed.add(node)
            self._emit(f"[yellow]⏸ {node}[/yellow]  [dim]waiting for {self._wait_reason(node)}…[/dim]")

    # -- LangGraph callbacks -----------------------------------------------

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        node = (metadata or {}).get("langgraph_node")
        if node:
            self._node_by_run[run_id] = node
            if self._resumed == node:
                # "▸ resumed…" was already printed for this node - don't print
                # "→". Keep `_resumed` set: LangGraph can re-fire chain_start
                # for the resumed node, and all duplicates must be skipped.
                return
            if node == self._paused:
                # The graph was just resumed with `Command(resume=...)` and
                # this node is re-entering from its interrupt - print "▸"
                # instead of "→".
                self._paused = None
                self._resumed = node
                self._current = node
                self._pause_printed.discard(node)
                self._emit(f"[cyan]▸ {node}  resumed…[/cyan]")
                return
            if node == self._last_started:
                # A conditional-edge router fires its own chain_start under the
                # same node name after the node runs - don't print "→" twice.
                return
            # Any node still pending here truly finished (it didn't interrupt),
            # because a new node starting means the previous one completed.
            for done in list(self._pending):
                self._complete_node(done)
            self._last_started = node
            self._current = node
            self._emit(f"[cyan]→ {node}[/cyan]")
        elif parent_run_id is None and not self._started:
            self._started = True
            self._emit("[cyan]→ START[/cyan]")

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        if parent_run_id is None:
            # Graph-level end: flush pending completions, then the terminal
            # line - unless a node is paused, in which case the run will be
            # resumed later and no terminal state exists yet.
            for node in list(self._pending):
                self._complete_node(node)
            if self._paused is None:
                self._emit_terminal(outputs)
            return

        node = self._node_by_run.get(run_id)
        if node is None and self._current:
            # Resume path: the resumed node may emit chain_end without a matching
            # chain_start, so fall back to the node we're resuming into.
            node = self._current
            self._node_by_run[run_id] = node
        if node:
            # Only real node outputs (dicts) update the pending state. A
            # conditional-edge router also emits chain_end under the node's
            # name, but its output is the routing result (a string like
            # "gen") - ignore it so it can't clobber the node's actual output.
            if isinstance(outputs, dict) and outputs:
                self._pending[node] = outputs
            self._current = node
            if self._resumed == node:
                # The resumed node completed - clear so a future, genuinely new
                # invocation of the same node prints its own "→" line.
                self._resumed = None

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        node = self._node_by_run.get(run_id) or self._current
        if isinstance(error, GraphInterrupt):
            # The node hit `interrupt()` and paused. The interrupt payload (an
            # `Interrupt` value carrying the wait reason) is attached to the
            # exception - extract it here, since the old `on_interrupt`/
            # `on_resume` callback events no longer exist.
            value = _interrupt_value(error)
            if node:
                self._interrupt_value[node] = value
                self._pause_node(node)
            return
        if node:
            self._pending.pop(node, None)
            self._emit(f"[bold red]✖ {node}[/bold red]  [red]{error}[/red]")

    def _emit_terminal(self, outputs: dict[str, Any]) -> None:
        error = outputs.get("error")
        if error:
            self._emit(f"[bold red]✖ FAILED[/bold red]  [red]{error}[/red]")
        elif outputs.get("published"):
            run_id = outputs.get("testrail_run_id") or ""
            self._emit(f"[bold green]✓ PUBLISHED[/bold green]  [dim]run={run_id}[/dim]")
        else:
            self._emit("[dim]◻ NOT PUBLISHED[/dim]")
