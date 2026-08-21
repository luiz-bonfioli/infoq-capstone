# Evaluation

This document describes the demo eval suite in [`eval/`](../eval/) — a **golden
data set** plus one automated measurement, kept deliberately small because its
job is to *demonstrate* the eval loop, not to be a full CI harness.

The suite is self-contained (no LangSmith `evaluate()`, no external eval
platform). It runs the real graph headlessly over the golden set, auto-resumes
every human-gate interrupt deterministically, scores each run on two things,
and exits non-zero when a gate fails.

## 1. The golden data set

Each case is a real mock Aha! feature (`app/mocks/aha_features.py`) annotated
with the tier the system *should* assign:

| Case | Expected tier | Fixture intent |
|---|---|---|
| `AHA-201` | `divergent` | Empty ticket — the hard routing path (RAG + human gate) |
| `AHA-202` | `partial` | Thin ticket (1 concrete criterion) |
| `AHA-203` | `partial` | Thin ticket (1 criterion) |
| `AHA-204` | `partial` | Thin ticket (1 criterion + attachment) |
| `AHA-205` | `conformant` | Rich ticket (3 criteria) |
| `AHA-206` | `conformant` | Rich ticket (4 criteria) |

- **Expected tier** is hand-annotated design intent, guided by the "Ticket
  Completeness Standard" in `app/knowledge_base.py`: non-empty description
  **and** ≥2 concrete acceptance criteria → `conformant`; empty description and
  no criteria → `divergent`; otherwise `partial`.
- The six cases cover all three tiers and the interesting routing shapes, so a
  single run of the suite exercises the full pipeline.

## 2. What is measured

Each case runs through the real graph once (the headless runner auto-resumes
the `pattern_score_confirmation` and `test_case_review` interrupts with the
"continue / approved" decisions). Each run is scored on two things:

1. **Golden tier accuracy** — does the LLM-as-judge's `pattern_conformance`
   verdict match the expected tier? (One point per case, averaged.)
2. **Structural quality** — are the generated test cases well-formed against
   the company standards in `app/knowledge_base.py`?

### Structural checks (per generated case, mean → per-case score)

| Check | Passes when |
|---|---|
| `has_title` | non-empty `title` |
| `title_pattern_ok` | title has ≥3 segments split on `" - "` (`<Feature> - <Scenario> - <Expected outcome>`) |
| `has_preconditions` | non-empty `preconditions` |
| `has_expected_result` | non-empty `expected_result` |
| `steps_nonempty` | ≥1 non-blank numbered step |
| `priority_valid` | `priority` ∈ {High, Medium, Low} |

An empty generated batch scores 0.0.

## 3. Gates & thresholds

Thresholds are hardcoded in `eval/run_evals.py`. Defaults:

| Gate | Threshold | Fail means |
|---|---|---|
| per-case `structure` | ≥ 0.80 | a batch generated structurally weak cases |
| global `golden accuracy` | ≥ 0.50 | gross tier-classification drift |

**About the 0.50 accuracy threshold:** expected tiers encode design intent, and
the full-rubric LLM judge is *stricter* than that coarse rule — it applies the
whole rubric (title, attachments, priority), so a couple of thin fixtures
(`AHA-203`, `AHA-206`) get graded a tier down. The measured accuracy sits at
0.67, and the disagreements are *stable* (the judge is consistently stricter,
not flaky). The gate therefore catches gross drift (e.g. the system stopping to
recognize `divergent` tickets) rather than single-fixture disagreement. See
§5's reading.

Exit codes: **0** = pass · **1** = a gate failed · **2** = configuration/API-key
error.

## 4. How to run

```bash
python -m eval.run_evals
```

The chat model comes from the `OPENAI_CHAT_MODEL` env var (default `gpt-4o-mini`).

Each run prints a per-case table plus the gate results to the console and
**exits non-zero on failure**. No report files are written.

## 5. Current measured baseline

Run: full golden set, `gpt-4o-mini`, **all gates PASS**.

| Case | Expected | Observed | Tier match | Structure |
|---|---|---|---|---|
| `AHA-201` | divergent | divergent | ✓ | 1.00 |
| `AHA-202` | partial | partial | ✓ | 1.00 |
| `AHA-203` | partial | divergent | ✗ | 1.00 |
| `AHA-204` | partial | partial | ✓ | 1.00 |
| `AHA-205` | conformant | conformant | ✓ | 1.00 |
| `AHA-206` | conformant | partial | ✗ | 1.00 |
| **Global** | | | **0.67** | **1.00** |
