from unittest.mock import MagicMock, patch

from docker.errors import DockerException

from vps_ops_toolkit.checks.docker_check import check_docker
from vps_ops_toolkit.models import CheckStatus


@patch("vps_ops_toolkit.checks.docker_check.docker.from_env")
def test_docker_check_returns_ok_when_container_is_healthy(
    mock_from_env,
):
    client = MagicMock()
    mock_from_env.return_value = client

    container = MagicMock()
    container.name = "test-api"
    container.status = "running"
    container.attrs = {
        "State": {
            "Status": "running",
            "Health": {
                "Status": "healthy",
            },
        },
        "RestartCount": 0,
    }

    client.containers.list.return_value = [container]

    result = check_docker()

    assert result.status == CheckStatus.OK
    assert len(result.containers) == 1

    checked = result.containers[0]

    assert checked.name == "test-api"
    assert checked.state == "running"
    assert checked.health == "healthy"
    assert checked.restart_count == 0
    assert checked.status == CheckStatus.OK


@patch("vps_ops_toolkit.checks.docker_check.docker.from_env")
def test_docker_check_returns_critical_when_container_is_exited(
    mock_from_env,
):
    client = MagicMock()
    mock_from_env.return_value = client

    container = MagicMock()
    container.name = "test-api"
    container.status = "exited"
    container.attrs = {
        "State": {
            "Status": "exited",
        },
        "RestartCount": 0,
    }

    client.containers.list.return_value = [container]

    result = check_docker()

    assert result.status == CheckStatus.CRITICAL
    assert result.containers[0].status == CheckStatus.CRITICAL


@patch("vps_ops_toolkit.checks.docker_check.docker.from_env")
def test_docker_check_returns_critical_when_health_is_unhealthy(
    mock_from_env,
):
    client = MagicMock()
    mock_from_env.return_value = client

    container = MagicMock()
    container.name = "test-db"
    container.status = "running"
    container.attrs = {
        "State": {
            "Status": "running",
            "Health": {
                "Status": "unhealthy",
            },
        },
        "RestartCount": 0,
    }

    client.containers.list.return_value = [container]

    result = check_docker()

    assert result.status == CheckStatus.CRITICAL
    assert result.containers[0].health == "unhealthy"
    assert result.containers[0].status == CheckStatus.CRITICAL


@patch("vps_ops_toolkit.checks.docker_check.docker.from_env")
def test_docker_check_returns_warning_when_health_is_starting(
    mock_from_env,
):
    client = MagicMock()
    mock_from_env.return_value = client

    container = MagicMock()
    container.name = "test-api"
    container.status = "running"
    container.attrs = {
        "State": {
            "Status": "running",
            "Health": {
                "Status": "starting",
            },
        },
        "RestartCount": 0,
    }

    client.containers.list.return_value = [container]

    result = check_docker()

    assert result.status == CheckStatus.WARNING
    assert result.containers[0].status == CheckStatus.WARNING


@patch("vps_ops_toolkit.checks.docker_check.docker.from_env")
def test_docker_check_returns_warning_when_no_containers_exist(
    mock_from_env,
):
    client = MagicMock()
    mock_from_env.return_value = client

    client.containers.list.return_value = []

    result = check_docker()

    assert result.status == CheckStatus.WARNING
    assert result.containers == []


@patch("vps_ops_toolkit.checks.docker_check.docker.from_env")
def test_docker_check_returns_error_when_docker_is_unavailable(
    mock_from_env,
):
    mock_from_env.side_effect = DockerException(
        "Docker daemon unavailable"
    )

    result = check_docker()

    assert result.status == CheckStatus.ERROR
    assert result.containers == []
    assert "Docker daemon unavailable" in result.message