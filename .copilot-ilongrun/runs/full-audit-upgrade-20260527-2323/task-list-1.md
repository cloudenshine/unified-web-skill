# Task List 1

## Workstream ws-01-upgrade-runtime

- **Goal**: update dependency/runtime declarations and repair runtime compatibility with latest tool versions.
- **Inputs / Dependencies**: baseline repo inspection, requirements, Dockerfile, README, engine adapters.
- **Outputs**: updated requirements/docs/runtime files, bb-browser compatibility code, matrix truth fixes.
- **Owner Role / Owner Model**: main-agent / GPT-5.4
- **Acceptance**: repo declares latest tested dependencies; latest scrapling and bb-browser work with current code paths.
- **Verify**: `.venv\Scripts\python.exe -m ruff check app tests`, focused pytest for adapter logic.
- **Retry Budget**: 3
- **Status**: complete

## Workstream ws-02-verify-regressions

- **Goal**: produce fresh evidence that upgraded repo still works.
- **Inputs / Dependencies**: ws-01 complete, `.venv`, required browser binaries, bb-browser daemon healthy.
- **Outputs**: passing diagnostics, full pytest, promoted-http / promoted-structured / promoted-browser outputs, watch evidence.
- **Owner Role / Owner Model**: main-agent / GPT-5.4
- **Acceptance**: all release-blocking promoted profiles pass with no weak/failed results.
- **Verify**: `check.py`, `pytest -q`, `verify_source_matrix.py --regression-profile ...`
- **Retry Budget**: 3
- **Status**: complete

## Workstream ws-03-review-audit

- **Goal**: converge code / security / test-evidence reviews, final audit, and adjudication.
- **Inputs / Dependencies**: ws-02 complete and fresh evidence available.
- **Outputs**: review markdown files, `gpt54-final-review.md`, `adjudication.md`.
- **Owner Role / Owner Model**: main-agent + review agents / GPT-5.4 family
- **Acceptance**: no unresolved must-fix findings remain.
- **Verify**: review artifacts exist and agree that completion is justified.
- **Retry Budget**: 2
- **Status**: in_progress
