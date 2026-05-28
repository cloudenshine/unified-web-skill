# Code Review

- **Reviewer:** code-review agent (`run-code-review`)
- **Status:** complete
- **Verdict:** pass after fix

## Findings

1. **Resolved:** `_wait_for_tab_text()` reused the full caller timeout for each polling `eval`, which could exceed the intended capped wait budget.

## Resolution

- Updated `app/engines/bb_browser.py` to pass the remaining deadline budget into each `_eval_tab()` call.
- Added `test_wait_for_tab_text_caps_eval_timeout_to_remaining_budget` in `tests/unit/test_bb_browser_command.py`.

## Residual concerns

- None.
