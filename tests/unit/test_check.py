from check import classify_smoke


def test_classify_smoke_ok_is_not_critical():
    label, critical = classify_smoke(True)
    assert label == "[OK]"
    assert critical is False


def test_classify_smoke_warning_is_not_critical():
    label, critical = classify_smoke(False)
    assert label == "[WARN]"
    assert critical is False


def test_classify_smoke_critical_failure():
    label, critical = classify_smoke(False, critical=True)
    assert label == "[FAIL]"
    assert critical is True
