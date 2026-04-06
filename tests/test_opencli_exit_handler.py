"""tests/test_opencli_exit_handler.py"""
import pytest
from app.opencli_exit_handler import evaluate_opencli_failure, Decision


class TestEvaluateOpenCLIFailure:
    # exit_code = 0 (SUCCESS)
    def test_success(self):
        d = evaluate_opencli_failure(0, attempt=0, fallback_enabled=True)
        assert d.should_retry is False
        assert d.fallback_to_scrapling is False
        assert d.label == "SUCCESS"

    # exit_code = 77 (AUTH_REQUIRED)
    def test_auth_required_no_retry(self):
        d = evaluate_opencli_failure(77, attempt=0, fallback_enabled=True)
        assert d.should_retry is False
        assert d.fallback_to_scrapling is True
        assert d.label == "AUTH_REQUIRED"

    def test_auth_required_regardless_of_fallback(self):
        d = evaluate_opencli_failure(77, attempt=0, fallback_enabled=False)
        # AUTH still fallbacks regardless of fallback_enabled
        assert d.fallback_to_scrapling is True

    # exit_code = 69 (SERVICE_UNAVAILABLE)
    def test_service_unavailable_first_attempt_retries(self):
        d = evaluate_opencli_failure(69, attempt=0, fallback_enabled=True)
        assert d.should_retry is True

    def test_service_unavailable_third_attempt_no_retry(self):
        d = evaluate_opencli_failure(69, attempt=2, fallback_enabled=True)
        assert d.should_retry is False
        assert d.fallback_to_scrapling is True

    # exit_code = 75 (TEMPFAIL)
    def test_tempfail_retries(self):
        d = evaluate_opencli_failure(75, attempt=0, fallback_enabled=True)
        assert d.should_retry is True
        assert d.fallback_to_scrapling is True

    def test_tempfail_second_attempt_still_retries(self):
        d = evaluate_opencli_failure(75, attempt=2, fallback_enabled=True)
        assert d.should_retry is True

    # exit_code = 66 (NO_DATA)
    def test_no_data_fallback_to_scrapling(self):
        d = evaluate_opencli_failure(66, attempt=0, fallback_enabled=True)
        assert d.should_retry is False
        assert d.fallback_to_scrapling is True
        assert d.label == "NO_DATA"

    # exit_code = 78 (NOT_FOUND)
    def test_not_found_silent_fallback(self):
        d = evaluate_opencli_failure(78, attempt=0, fallback_enabled=True)
        assert d.should_retry is False
        assert d.fallback_to_scrapling is True
        assert d.label == "NOT_FOUND"

    def test_not_found_without_fallback(self):
        d = evaluate_opencli_failure(78, attempt=0, fallback_enabled=False)
        # NOT_FOUND always falls back silently
        assert d.fallback_to_scrapling is True

    # Unknown exit codes
    def test_unknown_exit_code_with_fallback(self):
        d = evaluate_opencli_failure(99, attempt=0, fallback_enabled=True)
        assert d.fallback_to_scrapling is True

    def test_unknown_exit_code_without_fallback(self):
        d = evaluate_opencli_failure(99, attempt=0, fallback_enabled=False)
        assert d.fallback_to_scrapling is False

    # Decision dataclass
    def test_decision_label_defaults_to_reason(self):
        d = Decision(should_retry=False, fallback_to_scrapling=False, reason="my_reason")
        assert d.label == "my_reason"

    def test_decision_label_explicit(self):
        d = Decision(should_retry=False, fallback_to_scrapling=False, reason="r", label="L")
        assert d.label == "L"
