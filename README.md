# AI-Powered Test Case Generation from Aha! Features Using RAG

A [LangGraph](https://langchain-ai.github.io/langgraph/) pipeline that extracts features from Aha!,
retrieves relevant organizational knowledge (RAG), generates TestRail test cases with an LLM, routes them
through human QA review, and publishes approved cases to TestRail.

See [`project.md`](./project.md) for the full problem statement and architecture.

## Project Structure

```
app/
  state.py                # Shared PipelineState / TestCase types
  main.py                 # CLI entrypoint (handles interrupt/resume loop)
  console.py              # rich-based console rendering/prompting (panels, tables, spinners)
  llm_config.py           # llm_configured() - detects OPENAI_API_KEY for real vs. stub behavior
  company_patterns.py     # Loads company_patterns.md (single source of truth for scoring + RAG)
  knowledge_base.py        # Seed company standards/guidelines documents for RAG
  tools/                   # @tool get_aha_feature / publish_test_cases_to_testrail (serve mock data)
  mocks/                    # Pre-configured mock Aha! features + TestRail responses
  graph/build_graph.py     # LangGraph StateGraph wiring + MemorySaver checkpointer
  nodes/
    aha_extractor.py       # Calls get_aha_feature tool
    preprocessing.py       # Convert to Markdown + metadata
    pattern_scoring.py     # Score ticket vs. company_patterns.md (LLM or heuristic) + routing
    confirm_low_score.py   # Human-in-the-loop gate: confirm whether to proceed on a low score
    rag_retrieval.py       # InMemoryVectorStore + OpenAIEmbeddings retrieval (optional, see below)
    llm_generation.py      # ChatOpenAI + structured output test case generation
    human_review.py        # Human-in-the-loop review via interrupt() + routing
    error_handler.py       # Terminal node for unrecoverable errors / exhausted retries
    utils.py               # safe_node error-catching decorator + route_on_error/log_edge helpers
company_patterns.md        # Single source of truth for ticket/test case standards
requirements.txt
```

> `aha_extractor`/`testrail_publish` currently call `@tool` functions serving mock data (`app/mocks/`)
> pending real Aha!/TestRail API clients. `pattern_scoring`, `rag_retrieval`, and `llm_generation` use real
> `ChatOpenAI`/`OpenAIEmbeddings` when `OPENAI_API_KEY` is set, else fall back to a heuristic/empty results
> so the graph stays runnable without credentials. Graph plumbing (state, routing, checkpointing, error
> handling, human-in-the-loop) is fully implemented.

## How scoring works

[`company_patterns.md`](./company_patterns.md) is the single source of truth for what a well-formed ticket
and test case look like (completeness, structure, coverage). `pattern_scoring` loads it
(`load_company_patterns()`) and injects the full text into the LLM prompt, so `divergent`/`partial`/
`conformant` is judged directly against that rubric (`_llm_score`, used when `OPENAI_API_KEY` is set). A
deterministic `_heuristic_score` fallback mirrors the same rubric using simple ticket-completeness counts
when no LLM is configured. The same standards are also seeded into the RAG vector store (`knowledge_base.py`,
manually kept in sync with the `.md` file) so generation is grounded in the same rules the ticket was scored
against. Edit `company_patterns.md` to change what "conformant" means company-wide.

Routing based on the score:
- `conformant` → skips straight to `llm_generation`.
- `partial`/`divergent` → pauses at `confirm_low_score` (human decides continue/abort); if continuing,
  `divergent` also runs `rag_retrieval` first, `partial` skips it.

## LangChain + LangGraph roles

- **LangGraph** owns orchestration: state (`PipelineState`), node sequencing, conditional routing, retries,
  checkpointing, human-in-the-loop pause/resume.
- **LangChain** provides building blocks inside nodes: `@tool`-decorated functions (`tools/`, called
  directly via `.invoke()`, not LLM tool-calling), `InMemoryVectorStore` + `OpenAIEmbeddings` for retrieval,
  and `ChatOpenAI.with_structured_output(...)` for scoring/generation.
- No agentic tool-calling (`bind_tools`/`ToolNode`) is used - this is a deterministic pipeline where
  LangGraph's conditional edges make all routing decisions.

```python
from app.tools import get_aha_feature
feature_raw = get_aha_feature.invoke({"feature_id": "PROJ-123"})
```

## Mock data & test fixtures

`app/mocks/aha_features.py` has 10 general mock features (`AHA-101`-`AHA-110`) plus 6 fixtures purpose-built
to deterministically hit each pattern-conformance tier under the heuristic scorer:

| Feature ID | Heuristic score | Exercises |
|---|---|---|
| `AHA-201` | `divergent` | Gate triggers, RAG runs if user continues |
| `AHA-202`/`203`/`204` | `partial` | Gate triggers, RAG skipped if user continues |
| `AHA-205`/`206` | `conformant` | Gate skipped, straight to `llm_generation` |

```powershell
python -m app.main --feature-id AHA-201   # divergent - answer "n" to abort
python -m app.main --feature-id AHA-202   # partial - answer "y" to continue
python -m app.main --feature-id AHA-205   # conformant - no gate
```

> If `OPENAI_API_KEY` is set, the real LLM scorer is used instead and may occasionally judge a fixture
> differently than the table above (guaranteed only for the heuristic fallback).

Any other `feature_id` falls back to `DEFAULT_AHA_FEATURE_MOCK` (empty, scores `divergent`). Swap the
`get_mock_*` calls in `app/tools/` for real HTTP calls once the real API clients are implemented.

## LangGraph features implemented

- **`StateGraph`** with typed `PipelineState`, plus **`MemorySaver`** checkpointing (swap for SQLite/Postgres
  for real persistence).
- **Human-in-the-loop**: `confirm_low_score` (resume `{"continue": true/false}`) and `human_review` (resume
  `{"decision": "approved"/"rejected", "feedback": str}`), both `interrupt()`-based.
- **Conditional edges / retry loop**: every node routes to `error_handler` on failure; `human_review` loops
  back to `llm_generation` on rejection, capped at `MAX_RETRIES` (default 3).
- **Error handling**: `safe_node` decorator wraps every node, catching exceptions into `state["error"]`
  without crashing the graph (while letting `GraphInterrupt` propagate).
- **Edge logging**: every conditional edge logs `EDGE: source -> (label) -> target` via `log_edge()`
  (`app/nodes/utils.py`), visible in console/log output for tracing which branch a run took.

## Graph shape

```
START -> aha_extractor -> preprocessing -> pattern_scoring
    --(conformant)--------------------------------> llm_generation
    --(partial/divergent)--> confirm_low_score
        --(abort)-----------------------------------> error_handler -> END
        --(continue, divergent)---------------------> rag_retrieval -> llm_generation
        --(continue, partial)------------------------> llm_generation
    -> human_review --(approved)--------> testrail_publish -> END
                    --(rejected, retries left)--> llm_generation (loop)
                    --(rejected, exhausted)--> error_handler -> END
    (any node error) --> error_handler -> END
```

### Visualizing the graph

**LangSmith tracing** - set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` in `.env`
(see `.env.example`), then run normally; each run appears as a trace at smith.langchain.com showing every
node executed and where `interrupt()` paused.

**LangGraph Studio** - `pip install "langgraph-cli[inmem]"` (in `requirements.txt`), then from the project
root run `langgraph dev` (uses [`langgraph.json`](./langgraph.json)). It opens/prints a Studio URL that
renders the graph, lets you invoke it, inspect state, and resume interrupts from a UI.

### Calling the agent over HTTP (PowerShell)

With `langgraph dev` running, use `curl.exe` (the real curl bundled with Windows; PowerShell's `curl` alias
doesn't support the same flags) against `http://127.0.0.1:2024`. Assistant id is `test_case_pipeline`.

```powershell
# 1. conformant (AHA-205) - runs straight through to the human_review interrupt
$threadId = (curl.exe -s -X POST http://127.0.0.1:2024/threads -H "Content-Type: application/json" -d '{}' | ConvertFrom-Json).thread_id
curl.exe -s -X POST "http://127.0.0.1:2024/threads/$threadId/runs/wait" `
  -H "Content-Type: application/json" `
  -d '{"assistant_id": "test_case_pipeline", "input": {"aha_feature_id": "AHA-205"}}'

# 2. partial (AHA-202) - pauses at confirm_low_score, then resume to continue
$threadId = (curl.exe -s -X POST http://127.0.0.1:2024/threads -H "Content-Type: application/json" -d '{}' | ConvertFrom-Json).thread_id
curl.exe -s -X POST "http://127.0.0.1:2024/threads/$threadId/runs/wait" -H "Content-Type: application/json" -d '{"assistant_id": "test_case_pipeline", "input": {"aha_feature_id": "AHA-202"}}'
curl.exe -s -X POST "http://127.0.0.1:2024/threads/$threadId/runs/wait" -H "Content-Type: application/json" -d '{"assistant_id": "test_case_pipeline", "command": {"resume": {"continue": true}}}'

# 3. divergent (AHA-201) - pauses at confirm_low_score, resume to abort (-> error_handler)
$threadId = (curl.exe -s -X POST http://127.0.0.1:2024/threads -H "Content-Type: application/json" -d '{}' | ConvertFrom-Json).thread_id
curl.exe -s -X POST "http://127.0.0.1:2024/threads/$threadId/runs/wait" -H "Content-Type: application/json" -d '{"assistant_id": "test_case_pipeline", "input": {"aha_feature_id": "AHA-201"}}'
curl.exe -s -X POST "http://127.0.0.1:2024/threads/$threadId/runs/wait" -H "Content-Type: application/json" -d '{"assistant_id": "test_case_pipeline", "command": {"resume": {"continue": false}}}'
```

To resume a `human_review` interrupt: `"command": {"resume": {"decision": "approved"}}` (or `"rejected"`
with `"feedback": "..."`).

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

```powershell
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY=sk-...` in `.env` (auto-loaded via `load_dotenv()`, gitignored). Without it,
`rag_retrieval`/`llm_generation` log a warning and return empty results - the rest of the graph still runs.

### Troubleshooting: SSL certificate errors on corporate networks

`httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] ...` means an SSL-inspecting corporate proxy's
certificate isn't trusted. `app/main.py` already calls `truststore.inject_into_ssl()` at startup, which
makes Python's `ssl` module trust the OS certificate store instead of `certifi`'s bundled list - just make
sure `truststore` is installed (`requirements.txt`). Fallback: `OPENAI_SKIP_SSL_VERIFY=true` in `.env`
disables verification for OpenAI calls only (don't use in production).

> A `403 Forbidden` from LangSmith is a *different* problem (bad/revoked `LANGSMITH_API_KEY`, not SSL) -
> regenerate the key at smith.langchain.com, or set `LANGSMITH_TRACING=false` to disable tracing.

## Running the pipeline

```powershell
python -m app.main --feature-id AHA-123
```

`--feature-id` doubles as the LangGraph `thread_id` (re-running the same ID resumes/replays that thread).
Console output uses [`rich`](https://github.com/Textualize/rich) (`app/console.py`): a spinner while the
graph runs, panels for the two `interrupt()` prompts, a table of generated test cases, and a final summary
panel + pretty-printed state. Answer `y`/`n` at each prompt (default `n`): approving proceeds to
`testrail_publish`; rejecting loops back to `llm_generation` (up to `MAX_RETRIES`).

## Next steps

- Implement the real Aha! API client (`aha_extractor.py`) and TestRail API client (`testrail_publish.py`).
- Wire up a persistent vector database (pgvector, Pinecone, Chroma) in `rag_retrieval.py`.
- Incorporate `review_feedback` into regeneration prompts in `llm_generation.py`.
- Replace the CLI prompt in `human_review`/`main.py` with a real UI/Slack/email integration.
- Swap `MemorySaver` for a persistent checkpointer (SQLite/Postgres) in `build_graph.py` for production.
