from time import perf_counter

import httpx

from vps_ops_toolkit.models import CheckResult, CheckStatus


def check_http(
    url: str,
    expected_status: int = 200,
    timeout: float = 5.0,
) -> CheckResult:

    started = perf_counter()

    try:
        response = httpx.get(
            url,
            timeout=timeout,
        )

        elapsed_ms = (perf_counter() - started) * 1000

        if response.status_code == expected_status:
            return CheckResult(
                name="HTTP Health Check",
                status=CheckStatus.OK,
                message=f"HTTP {response.status_code}",
                response_time_ms=elapsed_ms,
            )

        return CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.CRITICAL,
            message=(
                f"Expected HTTP {expected_status}, "
                f"but received HTTP {response.status_code}"
            ),
            response_time_ms=elapsed_ms,
        )

    except httpx.RequestError as exc:
        return CheckResult(
            name="HTTP Health Check",
            status=CheckStatus.ERROR,
            message=str(exc),
        )