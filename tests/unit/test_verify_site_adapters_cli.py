from verify_site_adapters import _adapter_error, _items_from_json


def test_items_from_json_extracts_bb_browser_success_envelope_videos():
    items = _items_from_json(
        '{"success":true,"data":{"videos":[{"title":"One"},{"title":"Two"}]}}'
    )

    assert [item["title"] for item in items] == ["One", "Two"]


def test_items_from_json_extracts_bb_browser_success_envelope_posts():
    items = _items_from_json(
        '{"success":true,"data":{"posts":[{"title":"One"}]}}'
    )

    assert [item["title"] for item in items] == ["One"]


def test_items_from_json_extracts_bb_browser_success_envelope_papers():
    items = _items_from_json(
        '{"success":true,"data":{"papers":[{"title":"One"}]}}'
    )

    assert [item["title"] for item in items] == ["One"]


def test_adapter_error_extracts_json_error_from_stdout():
    error = _adapter_error(
        1,
        '{"success":false,"error":"bb-browser: Daemon did not start in time"}',
        "",
    )

    assert error == "bb-browser: Daemon did not start in time"


def test_adapter_error_prefers_stderr_when_present():
    error = _adapter_error(1, '{"success":false,"error":"from stdout"}', "from stderr")

    assert error == "from stderr"


def test_adapter_error_falls_back_to_exit_code():
    error = _adapter_error(7, "", "")

    assert error == "exit code 7"
