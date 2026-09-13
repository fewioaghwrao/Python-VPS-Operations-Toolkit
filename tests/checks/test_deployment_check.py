from unittest.mock import call, patch

import pytest

from vps_ops_toolkit.checks.deployment_check import check_deployment
from vps_ops_toolkit.models import CheckResult, CheckStatus


@patch(
    "vps_ops_toolkit.checks.deployment_check.check_http"
)
def test_deployment_check_returns_ok_for_health_endpoint(
    mock_check_http,
):
    mock_check_http.return_value = CheckResult(
        name="HTTP Health Check",
        status=CheckStatus.OK,
        message="HTTP 200",
        response_time_ms=100.0,
    )

    result = check_deployment(
        health_url="https://example.com/health",
    )

    assert result.status == CheckStatus.OK
    assert len(result.checks) == 1
    assert result.checks[0].name == "Health"
    assert result.checks[0].status == CheckStatus.OK
    assert result.message == "1/1 deployment check(s) passed."


@patch(
    "vps_ops_toolkit.checks.deployment_check.check_http"
)
def test_deployment_check_returns_ok_for_health_and_api(
    mock_check_http,
):
    mock_check_http.side_effect = [
        CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.OK,
            message="HTTP 200",
            response_time_ms=100.0,
        ),
        CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.OK,
            message="HTTP 200",
            response_time_ms=150.0,
        ),
    ]

    result = check_deployment(
        health_url="https://example.com/health",
        api_url="https://example.com/api",
    )

    assert result.status == CheckStatus.OK
    assert len(result.checks) == 2
    assert result.message == "2/2 deployment check(s) passed."


@patch(
    "vps_ops_toolkit.checks.deployment_check.check_http"
)
def test_deployment_check_passes_expected_401_to_api(
    mock_check_http,
):
    mock_check_http.side_effect = [
        CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.OK,
            message="HTTP 200",
            response_time_ms=100.0,
        ),
        CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.OK,
            message="HTTP 401",
            response_time_ms=120.0,
        ),
    ]

    result = check_deployment(
        health_url="https://example.com/health",
        api_url="https://example.com/api/admin",
        api_expected_status=401,
    )

    assert result.status == CheckStatus.OK

    assert mock_check_http.call_args_list == [
        call(
            url="https://example.com/health",
            expected_status=200,
            timeout=5.0,
        ),
        call(
            url="https://example.com/api/admin",
            expected_status=401,
            timeout=5.0,
        ),
    ]


@patch(
    "vps_ops_toolkit.checks.deployment_check.check_http"
)
def test_deployment_check_returns_critical_when_api_fails(
    mock_check_http,
):
    mock_check_http.side_effect = [
        CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.OK,
            message="HTTP 200",
            response_time_ms=100.0,
        ),
        CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.CRITICAL,
            message="Expected HTTP 200, but received HTTP 503",
            response_time_ms=200.0,
        ),
    ]

    result = check_deployment(
        health_url="https://example.com/health",
        api_url="https://example.com/api",
    )

    assert result.status == CheckStatus.CRITICAL
    assert result.checks[1].status == CheckStatus.CRITICAL
    assert result.message == "1/2 deployment check(s) passed."


@patch(
    "vps_ops_toolkit.checks.deployment_check.check_http"
)
def test_deployment_check_returns_error_when_connection_fails(
    mock_check_http,
):
    mock_check_http.return_value = CheckResult(
        name="HTTP Health Check",
        status=CheckStatus.ERROR,
        message="Connection failed",
        response_time_ms=None,
    )

    result = check_deployment(
        health_url="https://example.com/health",
    )

    assert result.status == CheckStatus.ERROR
    assert result.checks[0].status == CheckStatus.ERROR
    assert result.message == "0/1 deployment check(s) passed."


def test_deployment_check_rejects_invalid_timeout():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than 0",
    ):
        check_deployment(
            health_url="https://example.com/health",
            timeout=0,
        )