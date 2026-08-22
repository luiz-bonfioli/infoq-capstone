# Capstone Submission Checklist

Checklist against the **System-Building Project Guide** (InfoQ Certified AI Engineering Program).
Tick items off as they are completed. Target: **Aug 31 submission**.

- `[x]` = done · `[ ]` = not done · `[ ] ⚠` = partial / unverified

---

## A. Project Checklist (guide Section 9)

- [x] Project Owner designated (N/A if solo — repo is single-author)
- [x] GitHub repository set up (`luiz-bonfioli/july-2026-ai-cohort-luiz-bonfioli`)
- [x] **Repo renamed to `[cohort]-[team]` format** — remote verified: `july-2026-ai-cohort-luiz-bonfioli` (⚠ confirm cohort string: README §1 says `july-2026-ai-americas-cohort`; repo prefix omits `americas`)
- [x] README includes **cohort name**
- [x] README includes **team name**
- [x] README includes **system description**
- [x] README includes **build & run instructions**
- [ ] **Demo video (~5 min)** — private/unlisted, downloadable by the InfoQ team
- [ ] ⚠ **Full repo access granted to Facilitator + InfoQ team** — unverified
- [ ] **Submitted via Project Submission Form** by Aug 31

## B. Technical Review requirements

- [x] **High-level design (components)** — `README.md`, `docs/HOW_IT_WORKS.md`, `docs/NODES_AND_STATE.md`, `project.md`
- [x] **Evaluation data set** — `eval/dataset.py` + `docs/EVALS.md` (6 golden fixtures, hand-annotated expected tiers)
- [x] **Lessons learned** — README §"Lessons learned" (6 lessons: Copilot→agent authoring, observability/traceability, evals-as-load-bearing-wall, RAG techniques, frameworks, production guardrails)

## C. Eval suite — the capstone's core requirement

> *"The connective tissue of the entire project is evaluation… your evals should function not as a final chapter but as the load-bearing wall of the system."*

- [x] In-loop **LLM-as-judge** (`pattern_scoring` → `conformant` / `partial` / `divergent`) — judges the *input*, not the system's output
- [x] **Human-in-the-loop** gates (`confirm_low_score`, `human_review`)
- [x] **Evaluation data set / golden fixtures** — `eval/dataset.py` (6 fixtures + hand-annotated expected tiers) + `docs/EVALS.md`
- [x] **Regression eval** of generated test cases against the rubric — structural checks (title pattern, preconditions, steps, expected result, priority) via `python -m eval.run_evals`
- [x] **Golden-tier accuracy** — does the LLM-as-judge verdict match the expected tier (gated at ≥ 0.50, currently 0.67)

## D. Milestones timeline

- [x] W1–W4: team, domain, architecture, eval plan, working prototype (Jul 25 – Aug 15)
- [ ] W5: **live demo & peer feedback** — Aug 22 (⚠ `presentation_prompt_and_script.md`, referenced here as prep, is not present anywhere in the repo — locate or regenerate)
- [ ] Integrate W5 feedback (Aug 22 – Aug 29)
- [ ] Final eval pass + checklist review
- [ ] Submission (Aug 31)

