# Security Review

- **Reviewer:** ILongRun Security Auditor (`run-security-review`)
- **Status:** complete
- **Verdict:** pass

## Findings

1. **Resolved:** bb-browser fetches accepted arbitrary URLs without explicit public-target validation, which widened SSRF / local-resource risk.
2. **Resolved:** explicit `opts["command"]` / `opts["args"]` could widen the site-adapter surface without validation.

## Resolution

- Added public-target validation in `app/engines/bb_browser.py`:
  - only `http` / `https`
  - rejects loopback / private / local targets
- Added platform command allowlists and strict `args` type validation for explicit adapter invocation.
- Added unit coverage in `tests/unit/test_bb_browser_command.py`.

## Residual risks

1. External challenge/auth-heavy sites remain environment-sensitive and are handled through source-matrix truth plus non-blocking watch profiles.
2. `requirements.txt` uses minimum-version ranges, so future ecosystem drift still needs live verification.
