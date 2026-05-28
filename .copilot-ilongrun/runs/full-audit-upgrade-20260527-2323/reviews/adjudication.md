# Adjudication

- **Decision:** ship / complete
- **Must-fix count:** 0
- **Should-fix count:** 0

## Gate status

1. `review-code` → complete
2. `review-test-evidence` → complete
3. `review-security` → complete
4. `phase-audit` → complete
5. `phase-finalize` → complete

## Evidence used

1. `python -m ruff check app tests` → pass
2. `python check.py` → pass
3. `python -m pytest -q` → `415 passed, 34 skipped`
4. `python verify_source_matrix.py --regression-profile promoted-http --fail-on-unverified` → `83 verified`
5. `python verify_source_matrix.py --regression-profile promoted-structured --fail-on-unverified` → `3 verified`
6. `python verify_source_matrix.py --regression-profile promoted-browser --fail-on-unverified` → `4 verified`
7. `python test_deploy_v3.py` → `28 pass, 0 fail, 3 warn`

## Notes

- The remaining warnings are non-blocking and environment-shaped.
- The final worktree includes the review-driven timeout and input-boundary hardening fixes.
