"""tests/test_opencli_client.py"""
import asyncio
import json
import sys
import unittest.mock as mock
import pytest
from app.opencli_client import run_opencli


class TestRunOpenCLI:
    def test_file_not_found_returns_exit_78(self):
        """When binary is missing, returns exit_code=78"""
        with mock.patch("asyncio.create_subprocess_exec",
                        side_effect=FileNotFoundError("not found")):
            result = asyncio.run(run_opencli("bilibili", "hot"))
        assert result["exit_code"] == 78
        assert result["ok"] is False
        assert "not found" in result["stderr"]
        assert result["parsed"] == {}

    def test_successful_json_output(self):
        """Successful execution parses JSON output"""
        output_data = {"title": "Test Article", "items": [1, 2, 3]}
        output_bytes = json.dumps(output_data).encode()

        mock_proc = mock.AsyncMock()
        mock_proc.communicate = mock.AsyncMock(return_value=(output_bytes, b""))
        mock_proc.returncode = 0

        with mock.patch("asyncio.create_subprocess_exec",
                        return_value=mock_proc):
            result = asyncio.run(run_opencli("bilibili", "hot"))

        assert result["ok"] is True
        assert result["exit_code"] == 0
        assert result["parsed"] == output_data

    def test_non_json_stdout_stays_as_string(self):
        """Non-JSON stdout is kept as string, parsed is {}"""
        mock_proc = mock.AsyncMock()
        mock_proc.communicate = mock.AsyncMock(
            return_value=(b"plain text output", b"")
        )
        mock_proc.returncode = 0

        with mock.patch("asyncio.create_subprocess_exec",
                        return_value=mock_proc):
            result = asyncio.run(run_opencli("zhihu", "trending"))

        assert result["ok"] is True
        assert result["stdout"] == "plain text output"
        assert result["parsed"] == {}

    def test_non_zero_exit_code_not_ok(self):
        """Non-zero exit code → ok=False"""
        mock_proc = mock.AsyncMock()
        mock_proc.communicate = mock.AsyncMock(return_value=(b"", b"error message"))
        mock_proc.returncode = 69

        with mock.patch("asyncio.create_subprocess_exec",
                        return_value=mock_proc):
            result = asyncio.run(run_opencli("site", "cmd"))

        assert result["ok"] is False
        assert result["exit_code"] == 69
        assert result["stderr"] == "error message"

    def test_timeout_returns_exit_75(self):
        """Timeout returns exit_code=75 (TEMPFAIL)"""
        mock_proc = mock.AsyncMock()
        # First communicate() call times out; second (post-kill cleanup) succeeds
        mock_proc.communicate = mock.AsyncMock(
            side_effect=[asyncio.TimeoutError(), (b"", b"")]
        )
        mock_proc.kill = mock.MagicMock()

        with mock.patch("asyncio.create_subprocess_exec",
                        return_value=mock_proc):
            result = asyncio.run(
                run_opencli("site", "cmd", timeout_seconds=1)
            )

        assert result["exit_code"] == 75
        assert result["ok"] is False
        assert "timeout" in result["stderr"]

    def test_args_passed_through(self):
        """Additional args are forwarded to subprocess"""
        captured_cmd = []

        async def fake_exec(*args, **kwargs):
            captured_cmd.extend(args)
            mock_proc = mock.AsyncMock()
            mock_proc.communicate = mock.AsyncMock(return_value=(b"{}", b""))
            mock_proc.returncode = 0
            return mock_proc

        with mock.patch("asyncio.create_subprocess_exec", side_effect=fake_exec):
            asyncio.run(run_opencli("bilibili", "search", args=["--limit", "10"]))

        assert "--limit" in captured_cmd
        assert "10" in captured_cmd

    def test_unexpected_exception_returns_minus_one(self):
        """Unexpected exceptions return exit_code=-1"""
        with mock.patch("asyncio.create_subprocess_exec",
                        side_effect=PermissionError("denied")):
            result = asyncio.run(run_opencli("site", "cmd"))

        assert result["exit_code"] == -1
        assert result["ok"] is False
