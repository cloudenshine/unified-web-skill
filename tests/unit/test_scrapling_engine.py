from app.engines.scrapling_engine import _is_blocked


def test_long_success_page_with_access_denied_phrase_is_not_blocked():
    body = ("Normal article content about APIs and permissions. " * 120)
    body += "The documentation mentions access denied as an example error."

    assert _is_blocked(200, body) is False


def test_short_access_denied_page_is_blocked():
    assert _is_blocked(200, "Access Denied - please verify") is True


def test_long_success_page_with_captcha_configuration_is_not_blocked():
    body = ("Article content and navigation. " * 120)
    body += '"wgConfirmEditCaptchaNeededForGenericEdit":"hcaptcha"'

    assert _is_blocked(200, body) is False


def test_short_captcha_challenge_page_is_blocked():
    assert _is_blocked(200, "captcha verification required") is True


def test_block_status_is_blocked_even_with_long_body():
    body = "Legitimate looking text. " * 250

    assert _is_blocked(403, body) is True


def test_long_challenge_running_page_is_blocked():
    body = ("Normal page shell. " * 250) + "challenge-running"

    assert _is_blocked(200, body) is True


def test_latest_scrapling_dynamic_fetchers_import_cleanly():
    from scrapling import DynamicFetcher, StealthyFetcher

    assert DynamicFetcher.__name__ == "DynamicFetcher"
    assert StealthyFetcher.__name__ == "StealthyFetcher"
