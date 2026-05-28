# Strategy

## Mode choice

- **Mode**: internal coding run, not fleet.
- **Why**: the work touched overlapping write sets (`requirements.txt`, engine adapters, source-matrix truth, tests, docs) and required local environment surgery (`.venv`, browser binaries, bb-browser daemon repair), so serial ownership was safer than parallel code writes.

## Phase / wave split

1. **DEFINE**
   - inspect repo shape, manifests, baseline diagnostics, existing tests, and skill protocol.
2. **PLAN**
   - identify upgrade surface: dependency declarations, runtime compatibility, matrix truth, docs, and verification path.
3. **BUILD**
   - wave 1: dependency/runtime/tooling fixes
   - wave 2: bb-browser compatibility + matrix truth updates
4. **VERIFY**
   - lint, diagnostics, full pytest, promoted-http / promoted-structured / promoted-browser, plus evidence-watch profiles.
5. **REVIEW / AUDIT / FINALIZE**
   - independent code / security / test-evidence review, final audit, adjudication, then completion.

## Parallel vs serial

- **Serial**: build and verification workstreams because each changed the same repo and depended on fresh evidence from the previous step.
- **Parallel**: review agents only, after BUILD/VERIFY had converged.

## Model allocation

- **Main agent (GPT-5.4)**: strategy, implementation, verification, adjudication, and final audit synthesis.
- **Review agents**:
  - code-review for correctness scrutiny
  - iLongRun Security Auditor for security gate
  - iLongRun Test Engineer for fresh-evidence gate

## Completion standard

- release-blocking promoted profiles all pass
- `check.py` passes
- full pytest passes
- review-code / review-security / review-test-evidence produce no must-fix findings
- `reviews/gpt54-final-review.md` and `reviews/adjudication.md` exist and agree that must-fix is empty

## Block standard

- any promoted profile returns weak/failed
- full pytest or diagnostics fail
- review or audit finds unresolved must-fix

## Downgrade path

- when a previously promoted source becomes externally login-gated or challenge-blocked, update source-matrix truth to `matrix_only` instead of pretending the promoted batch is still stable
- when a public webpage becomes JS/challenge gated, prefer stable official API endpoints for regression coverage
