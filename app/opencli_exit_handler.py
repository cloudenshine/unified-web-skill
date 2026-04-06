"""opencli_exit_handler.py — OpenCLI exit code 处理策略"""
from dataclasses import dataclass

OPENCLI_EXIT_LABEL = {
    0: "SUCCESS",
    66: "NO_DATA",
    69: "SERVICE_UNAVAILABLE",
    75: "TEMPFAIL",
    77: "AUTH_REQUIRED",
    78: "NOT_FOUND",
}


@dataclass
class Decision:
    should_retry: bool
    fallback_to_scrapling: bool
    reason: str
    label: str = ""

    def __post_init__(self):
        if not self.label:
            self.label = self.reason


def evaluate_opencli_failure(
    exit_code: int,
    attempt: int,
    fallback_enabled: bool,
    stderr: str = "",
    stdout: str = "",
) -> Decision:
    label = OPENCLI_EXIT_LABEL.get(exit_code, f"unknown_{exit_code}")

    if exit_code == 0:
        return Decision(False, False, "success", label)

    if exit_code == 77:
        # AUTH_REQUIRED: no retry, always fallback + alert
        return Decision(False, True, "auth_required", label)

    if exit_code == 69:
        # SERVICE_UNAVAILABLE: retry up to 2 times, then fallback
        return Decision(attempt < 2, True, "service_unavailable_fallback", label)

    if exit_code == 75:
        # TEMPFAIL: backoff retry, then fallback
        return Decision(True, True, "temporary_failure_fallback", label)

    if exit_code == 66:
        # NO_DATA: scrapling dynamic补跑，不标记为失败
        return Decision(False, True, "no_data_scrapling_fallback", label)

    if exit_code == 78:
        # NOT_FOUND: silent fallback, don't block task
        return Decision(False, True, "opencli_not_found", label)

    return Decision(False, fallback_enabled, "unknown", label)
