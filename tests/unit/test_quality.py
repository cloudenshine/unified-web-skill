"""Tests for app.pipeline.quality — QualityGate."""

import pytest
from app.pipeline.quality import QualityGate


@pytest.fixture
def gate():
    return QualityGate()


class TestValidateGoodContent:
    def test_good_content_passes(self, gate):
        extracted = {
            "text": "A" * 200,  # long enough
        }
        passed, reason = gate.validate(extracted)
        assert passed is True
        assert reason == "ok"

    def test_good_content_with_date(self, gate):
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        extracted = {
            "text": "Valid content " * 50,
            "date": recent,
        }
        passed, reason = gate.validate(extracted, time_window_days=365)
        assert passed is True


class TestValidateTooShort:
    def test_too_short_default(self, gate):
        extracted = {"text": "short"}
        passed, reason = gate.validate(extracted)
        assert passed is False
        assert "too short" in reason

    def test_too_short_custom_threshold(self, gate):
        extracted = {"text": "A" * 50}
        passed, reason = gate.validate(extracted, min_length=100)
        assert passed is False

    def test_exactly_at_threshold(self, gate):
        extracted = {"text": "A" * 100}
        passed, reason = gate.validate(extracted, min_length=100)
        assert passed is True

    def test_empty_text(self, gate):
        extracted = {"text": ""}
        passed, reason = gate.validate(extracted)
        assert passed is False

    def test_whitespace_only(self, gate):
        extracted = {"text": "   \n\n   "}
        passed, reason = gate.validate(extracted)
        assert passed is False


class TestValidateBoilerplate:
    def test_access_denied_page(self, gate):
        extracted = {"text": "Access Denied - You do not have permission."}
        passed, reason = gate.validate(extracted, min_length=10)
        assert passed is False
        assert "boilerplate" in reason

    def test_404_page(self, gate):
        extracted = {"text": "404 Not Found - The page you requested does not exist."}
        passed, reason = gate.validate(extracted, min_length=10)
        assert passed is False
        assert "boilerplate" in reason

    def test_cloudflare_challenge(self, gate):
        extracted = {"text": "Just a moment... Checking your browser before accessing."}
        passed, reason = gate.validate(extracted, min_length=10)
        assert passed is False

    def test_long_boilerplate_passes(self, gate):
        # Boilerplate markers only trigger for short pages (<500 chars)
        extracted = {"text": "Access denied. " + "Real content " * 100}
        passed, reason = gate.validate(extracted, min_length=10)
        assert passed is True


class TestValidateDateFreshness:
    def test_old_content_rejected(self, gate):
        extracted = {
            "text": "A" * 200,
            "date": "2020-01-01",
        }
        passed, reason = gate.validate(extracted, time_window_days=30)
        assert passed is False
        assert "too old" in reason

    def test_fresh_content_passes(self, gate):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        extracted = {
            "text": "A" * 200,
            "date": today,
        }
        passed, reason = gate.validate(extracted, time_window_days=30)
        assert passed is True

    def test_no_date_window_not_checked(self, gate):
        extracted = {
            "text": "A" * 200,
            "date": "2020-01-01",
        }
        passed, reason = gate.validate(extracted, time_window_days=0)
        assert passed is True

    def test_unparseable_date_passes(self, gate):
        extracted = {
            "text": "A" * 200,
            "date": "not-a-date",
        }
        passed, reason = gate.validate(extracted, time_window_days=30)
        assert passed is True  # unparseable dates are not rejected


class TestDeduplicate:
    def test_dedup_by_hash(self, gate):
        class Record:
            def __init__(self, h):
                self.content_hash = h

        records = [Record("aaa"), Record("bbb"), Record("aaa"), Record("ccc")]
        unique, dup_count = gate.deduplicate(records)
        assert len(unique) == 3
        assert dup_count == 1

    def test_no_duplicates(self, gate):
        class Record:
            def __init__(self, h):
                self.content_hash = h

        records = [Record("aaa"), Record("bbb"), Record("ccc")]
        unique, dup_count = gate.deduplicate(records)
        assert len(unique) == 3
        assert dup_count == 0

    def test_all_duplicates(self, gate):
        class Record:
            def __init__(self, h):
                self.content_hash = h

        records = [Record("aaa"), Record("aaa"), Record("aaa")]
        unique, dup_count = gate.deduplicate(records)
        assert len(unique) == 1
        assert dup_count == 2

    def test_empty_hash_not_deduped(self, gate):
        class Record:
            def __init__(self, h):
                self.content_hash = h

        records = [Record(""), Record(""), Record("aaa")]
        unique, dup_count = gate.deduplicate(records)
        # Empty hashes are not added to seen set
        assert len(unique) == 3
        assert dup_count == 0

    def test_empty_list(self, gate):
        unique, dup_count = gate.deduplicate([])
        assert unique == []
        assert dup_count == 0
