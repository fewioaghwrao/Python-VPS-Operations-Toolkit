from dataclasses import dataclass

import docker
from docker.errors import DockerException

from vps_ops_toolkit.models import CheckStatus


@dataclass
class DockerContainerResult:
    """Result for a single Docker container."""

    name: str
    state: str
    health: str
    restart_count: int
    status: CheckStatus


@dataclass
class DockerCheckResult:
    """Overall Docker monitoring result."""

    status: CheckStatus
    containers: list[DockerContainerResult]
    message: str


def _get_container_status(
    state: str,
    health: str,
) -> CheckStatus:
    """
    Determine container status.

    CRITICAL:
        - Container is not running
        - Docker health check reports unhealthy

    WARNING:
        - Docker health check is still starting

    OK:
        - Container is running
        - Health is healthy or no HEALTHCHECK is configured
    """

    if state != "running":
        return CheckStatus.CRITICAL

    if health == "unhealthy":
        return CheckStatus.CRITICAL

    if health == "starting":
        return CheckStatus.WARNING

    return CheckStatus.OK


def _get_overall_status(
    containers: list[DockerContainerResult],
) -> CheckStatus:
    """Return the most severe container status."""

    priority = {
        CheckStatus.OK: 0,
        CheckStatus.WARNING: 1,
        CheckStatus.CRITICAL: 2,
        CheckStatus.ERROR: 3,
    }

    if not containers:
        return CheckStatus.WARNING

    return max(
        (container.status for container in containers),
        key=lambda status: priority[status],
    )


def check_docker() -> DockerCheckResult:
    """
    Check Docker daemon and container states.

    Returns:
        DockerCheckResult containing:
        - Docker overall status
        - Container statuses
        - Result message
    """

    client = None

    try:
        client = docker.from_env()

        # Verify that Docker Engine is reachable.
        client.ping()

        docker_containers = client.containers.list(all=True)

        containers: list[DockerContainerResult] = []

        for container in docker_containers:
            state_data = container.attrs.get("State", {})

            state = state_data.get(
                "Status",
                container.status or "unknown",
            )

            health_data = state_data.get("Health")

            if health_data:
                health = health_data.get(
                    "Status",
                    "unknown",
                )
            else:
                # Container has no Docker HEALTHCHECK configured.
                health = "none"

            restart_count = container.attrs.get(
                "RestartCount",
                0,
            )

            status = _get_container_status(
                state=state,
                health=health,
            )

            containers.append(
                DockerContainerResult(
                    name=container.name,
                    state=state,
                    health=health,
                    restart_count=restart_count,
                    status=status,
                )
            )

        # Keep CLI output deterministic.
        containers.sort(
            key=lambda container: container.name.lower()
        )

        if not containers:
            return DockerCheckResult(
                status=CheckStatus.WARNING,
                containers=[],
                message=(
                    "Docker daemon is reachable, "
                    "but no containers were found."
                ),
            )

        overall = _get_overall_status(containers)

        return DockerCheckResult(
            status=overall,
            containers=containers,
            message=(
                f"{len(containers)} container(s) checked."
            ),
        )

    except DockerException as exc:
        return DockerCheckResult(
            status=CheckStatus.ERROR,
            containers=[],
            message=f"Docker error: {exc}",
        )

    except Exception as exc:
        return DockerCheckResult(
            status=CheckStatus.ERROR,
            containers=[],
            message=f"Unexpected error: {exc}",
        )

    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass