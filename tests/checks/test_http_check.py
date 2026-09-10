from unittest.mock import Mock, patch

import httpx

from vps_ops_toolkit.checks.http_check import check_http
from vps_ops_toolkit.models import CheckStatus


def test_http_check_returns_ok_when_status_is_200():
    response = Mock()
    response.status_code = 200

    with patch(
        "vps_ops_toolkit.checks.http_check.httpx.get",
        return_value=response,
    ):
        result = check_http("https://example.com/health")

    assert result.status == CheckStatus.OK
    assert result.message == "HTTP 200"
    assert result.response_time_ms is not None


def test_http_check_returns_critical_when_status_is_not_expected():
    response = Mock()
    response.status_code = 503

    with patch(
        "vps_ops_toolkit.checks.http_check.httpx.get",
        return_value=response,
    ):
        result = check_http("https://example.com/health")

    assert result.status == CheckStatus.CRITICAL
    assert result.message == "Expected HTTP 200, but received HTTP 503"
    assert result.response_time_ms is not None


def test_http_check_returns_error_when_connection_fails():
    request = httpx.Request(
        "GET",
        "https://example.com/health",
    )

    error = httpx.ConnectError(
        "Connection failed",
        request=request,
    )

    with patch(
        "vps_ops_toolkit.checks.http_check.httpx.get",
        side_effect=error,
    ):
        result = check_http("https://example.com/health")

    assert result.status == CheckStatus.ERROR
    assert "Connection failed" in result.message
    assert result.response_time_ms is None