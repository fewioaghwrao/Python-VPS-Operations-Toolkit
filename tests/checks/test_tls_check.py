import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from vps_ops_toolkit.checks.tls_check import check_tls
from vps_ops_toolkit.models import CheckStatus


@patch(
    "vps_ops_toolkit.checks.tls_check._get_certificate_expiry"
)
def test_tls_check_returns_ok(mock_expiry):
    mock_expiry.return_value = datetime(
        2026,
        12,
        31,
        tzinfo=timezone.utc,
    )

    now = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    result = check_tls(
        "example.com",
        now=now,
    )

    assert result.status == CheckStatus.OK
    assert result.days_left == 121


@patch(
    "vps_ops_toolkit.checks.tls_check._get_certificate_expiry"
)
def test_tls_check_returns_warning(mock_expiry):
    mock_expiry.return_value = datetime(
        2026,
        9,
        21,
        tzinfo=timezone.utc,
    )

    now = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    result = check_tls(
        "example.com",
        now=now,
    )

    assert result.status == CheckStatus.WARNING
    assert result.days_left == 20


@patch(
    "vps_ops_toolkit.checks.tls_check._get_certificate_expiry"
)
def test_tls_check_returns_critical(mock_expiry):
    mock_expiry.return_value = datetime(
        2026,
        9,
        11,
        tzinfo=timezone.utc,
    )

    now = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    result = check_tls(
        "example.com",
        now=now,
    )

    assert result.status == CheckStatus.CRITICAL
    assert result.days_left == 10


@patch(
    "vps_ops_toolkit.checks.tls_check._get_certificate_expiry"
)
def test_tls_check_returns_critical_when_expired(
    mock_expiry,
):
    mock_expiry.return_value = datetime(
        2026,
        8,
        31,
        tzinfo=timezone.utc,
    )

    now = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    result = check_tls(
        "example.com",
        now=now,
    )

    assert result.status == CheckStatus.CRITICAL
    assert result.days_left == -1
    assert "expired" in result.message


@patch(
    "vps_ops_toolkit.checks.tls_check._get_certificate_expiry"
)
def test_tls_check_returns_error_when_connection_fails(
    mock_expiry,
):
    mock_expiry.side_effect = OSError(
        "Connection failed"
    )

    result = check_tls(
        "example.com",
    )

    assert result.status == CheckStatus.ERROR
    assert result.days_left is None
    assert "Connection failed" in result.message

def test_tls_check_rejects_invalid_thresholds():
    with pytest.raises(
        ValueError,
        match="warning_days must be greater than critical_days",
    ):
        check_tls(
            "example.com",
            warning_days=10,
            critical_days=20,
        )