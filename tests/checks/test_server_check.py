from types import SimpleNamespace
from unittest.mock import patch

import pytest

from vps_ops_toolkit.checks.server_check import (
    check_server,
    get_overall_status,
)
from vps_ops_toolkit.models import CheckStatus


@patch(
    "vps_ops_toolkit.checks.server_check.psutil.swap_memory"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.disk_usage"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.virtual_memory"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.cpu_percent"
)
def test_server_check_returns_ok(
    mock_cpu,
    mock_memory,
    mock_disk,
    mock_swap,
):
    mock_cpu.return_value = 20.0
    mock_memory.return_value = SimpleNamespace(percent=40.0)
    mock_disk.return_value = SimpleNamespace(percent=60.0)
    mock_swap.return_value = SimpleNamespace(percent=10.0)

    results = check_server()

    assert len(results) == 4

    assert all(
        result.status == CheckStatus.OK
        for result in results
    )

    assert get_overall_status(results) == CheckStatus.OK


@patch(
    "vps_ops_toolkit.checks.server_check.psutil.swap_memory"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.disk_usage"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.virtual_memory"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.cpu_percent"
)
def test_server_check_returns_warning(
    mock_cpu,
    mock_memory,
    mock_disk,
    mock_swap,
):
    mock_cpu.return_value = 20.0
    mock_memory.return_value = SimpleNamespace(percent=40.0)
    mock_disk.return_value = SimpleNamespace(percent=85.0)
    mock_swap.return_value = SimpleNamespace(percent=10.0)

    results = check_server()

    assert results[2].name == "Disk"
    assert results[2].status == CheckStatus.WARNING

    assert (
        get_overall_status(results)
        == CheckStatus.WARNING
    )


@patch(
    "vps_ops_toolkit.checks.server_check.psutil.swap_memory"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.disk_usage"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.virtual_memory"
)
@patch(
    "vps_ops_toolkit.checks.server_check.psutil.cpu_percent"
)
def test_server_check_returns_critical(
    mock_cpu,
    mock_memory,
    mock_disk,
    mock_swap,
):
    mock_cpu.return_value = 95.0
    mock_memory.return_value = SimpleNamespace(percent=40.0)
    mock_disk.return_value = SimpleNamespace(percent=60.0)
    mock_swap.return_value = SimpleNamespace(percent=10.0)

    results = check_server()

    assert results[0].name == "CPU"
    assert results[0].status == CheckStatus.CRITICAL

    assert (
        get_overall_status(results)
        == CheckStatus.CRITICAL
    )


def test_server_check_rejects_invalid_thresholds():
    with pytest.raises(
        ValueError,
        match="warning_threshold must be less than critical_threshold",
    ):
        check_server(
            warning_threshold=90.0,
            critical_threshold=80.0,
        )