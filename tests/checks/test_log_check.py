import pytest

from vps_ops_toolkit.checks.log_check import check_log
from vps_ops_toolkit.models import CheckStatus


def test_log_check_returns_ok_when_no_warning_or_error(tmp_path):
    log_file = tmp_path / "app.log"

    log_file.write_text(
        "\n".join(
            [
                "2026-09-11 07:00:00 INFO Application started",
                "2026-09-11 07:01:00 INFO Database connected",
                "2026-09-11 07:02:00 INFO Request completed",
            ]
        ),
        encoding="utf-8",
    )

    result = check_log(str(log_file))

    assert result.status == CheckStatus.OK
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.scanned_lines == 3
    assert result.matches == []


def test_log_check_returns_warning_when_warning_exists(tmp_path):
    log_file = tmp_path / "app.log"

    log_file.write_text(
        "\n".join(
            [
                "2026-09-11 07:00:00 INFO Application started",
                "2026-09-11 07:01:00 WARN Response time is high",
                "2026-09-11 07:02:00 INFO Request completed",
            ]
        ),
        encoding="utf-8",
    )

    result = check_log(str(log_file))

    assert result.status == CheckStatus.WARNING
    assert result.error_count == 0
    assert result.warning_count == 1

    assert len(result.matches) == 1
    assert result.matches[0].level == "WARNING"
    assert result.matches[0].line_number == 2


def test_log_check_returns_critical_when_error_exists(tmp_path):
    log_file = tmp_path / "app.log"

    log_file.write_text(
        "\n".join(
            [
                "2026-09-11 07:00:00 INFO Application started",
                "2026-09-11 07:01:00 WARN Retry started",
                "2026-09-11 07:02:00 ERROR Database connection failed",
            ]
        ),
        encoding="utf-8",
    )

    result = check_log(str(log_file))

    assert result.status == CheckStatus.CRITICAL
    assert result.error_count == 1
    assert result.warning_count == 1

    assert len(result.matches) == 2
    assert result.matches[1].level == "ERROR"
    assert result.matches[1].line_number == 3


def test_log_check_detects_nginx_error(tmp_path):
    log_file = tmp_path / "nginx-error.log"

    log_file.write_text(
        "\n".join(
            [
                (
                    "2026/09/11 07:00:00 [error] 123#123: "
                    "upstream timed out while connecting to upstream"
                ),
                "2026/09/11 07:01:00 [warn] 123#123: test warning",
            ]
        ),
        encoding="utf-8",
    )

    result = check_log(str(log_file))

    assert result.status == CheckStatus.CRITICAL
    assert result.error_count == 1
    assert result.warning_count == 1

    assert result.matches[0].level == "ERROR"
    assert result.matches[1].level == "WARNING"


def test_log_check_returns_error_when_file_does_not_exist(tmp_path):
    log_file = tmp_path / "missing.log"

    result = check_log(str(log_file))

    assert result.status == CheckStatus.ERROR
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.scanned_lines == 0
    assert result.matches == []
    assert "Failed to read log file" in result.message


def test_log_check_rejects_invalid_tail_lines(tmp_path):
    log_file = tmp_path / "app.log"

    log_file.write_text(
        "2026-09-11 07:00:00 INFO Application started",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="tail_lines must be greater than 0",
    ):
        check_log(
            str(log_file),
            tail_lines=0,
        )