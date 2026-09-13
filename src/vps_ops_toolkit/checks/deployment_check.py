from dataclasses import dataclass

from vps_ops_toolkit.checks.http_check import check_http
from vps_ops_toolkit.models import CheckStatus


@dataclass
class DeploymentStepResult:
    """Result of a single deployment verification step."""

    name: str
    url: str
    status: CheckStatus
    message: str
    response_time_ms: float | None = None


@dataclass
class DeploymentCheckResult:
    """Overall deployment verification result."""

    status: CheckStatus
    checks: list[DeploymentStepResult]
    message: str


def _get_overall_status(
    checks: list[DeploymentStepResult],
) -> CheckStatus:
    """Return the most severe status."""

    priority = {
        CheckStatus.OK: 0,
        CheckStatus.WARNING: 1,
        CheckStatus.CRITICAL: 2,
        CheckStatus.ERROR: 3,
    }

    return max(
        (check.status for check in checks),
        key=lambda status: priority[status],
    )


def _check_endpoint(
    name: str,
    url: str,
    expected_status: int,
    timeout: float,
) -> DeploymentStepResult:
    """Execute an HTTP deployment check."""

    result = check_http(
        url=url,
        expected_status=expected_status,
        timeout=timeout,
    )

    return DeploymentStepResult(
        name=name,
        url=url,
        status=result.status,
        message=result.message,
        response_time_ms=result.response_time_ms,
    )


def check_deployment(
    health_url: str,
    api_url: str | None = None,
    health_expected_status: int = 200,
    api_expected_status: int = 200,
    timeout: float = 5.0,
) -> DeploymentCheckResult:
    """
    Verify a deployment using HTTP endpoints.

    Health URL is required.
    API URL is optional.
    """

    if timeout <= 0:
        raise ValueError(
            "timeout must be greater than 0"
        )

    if not 100 <= health_expected_status <= 599:
        raise ValueError(
            "health_expected_status must be between 100 and 599"
        )

    if not 100 <= api_expected_status <= 599:
        raise ValueError(
            "api_expected_status must be between 100 and 599"
        )

    checks = [
        _check_endpoint(
            name="Health",
            url=health_url,
            expected_status=health_expected_status,
            timeout=timeout,
        )
    ]

    if api_url:
        checks.append(
            _check_endpoint(
                name="API",
                url=api_url,
                expected_status=api_expected_status,
                timeout=timeout,
            )
        )

    overall = _get_overall_status(checks)

    successful_checks = sum(
        check.status == CheckStatus.OK
        for check in checks
    )

    return DeploymentCheckResult(
        status=overall,
        checks=checks,
        message=(
            f"{successful_checks}/{len(checks)} "
            "deployment check(s) passed."
        ),
    )