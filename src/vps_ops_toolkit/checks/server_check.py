from pathlib import Path

import psutil

from vps_ops_toolkit.models import CheckResult, CheckStatus


def _get_status(
    value: float,
    warning_threshold: float,
    critical_threshold: float,
) -> CheckStatus:
    if value >= critical_threshold:
        return CheckStatus.CRITICAL

    if value >= warning_threshold:
        return CheckStatus.WARNING

    return CheckStatus.OK


def get_overall_status(
    results: list[CheckResult],
) -> CheckStatus:
    priority = {
        CheckStatus.OK: 0,
        CheckStatus.WARNING: 1,
        CheckStatus.CRITICAL: 2,
        CheckStatus.ERROR: 3,
    }

    return max(
        (result.status for result in results),
        key=lambda status: priority[status],
    )


def check_server(
    warning_threshold: float = 80.0,
    critical_threshold: float = 90.0,
    disk_path: str | None = None,
) -> list[CheckResult]:

    if warning_threshold >= critical_threshold:
        raise ValueError(
            "warning_threshold must be less than critical_threshold"
        )

    if disk_path is None:
        disk_path = Path.home().anchor or "/"

    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage(disk_path).percent
    swap_percent = psutil.swap_memory().percent

    metrics = [
        ("CPU", cpu_percent),
        ("Memory", memory_percent),
        ("Disk", disk_percent),
        ("Swap", swap_percent),
    ]

    return [
        CheckResult(
            name=name,
            status=_get_status(
                value,
                warning_threshold,
                critical_threshold,
            ),
            message=f"{value:.1f}%",
        )
        for name, value in metrics
    ]