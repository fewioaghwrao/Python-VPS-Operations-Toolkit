import typer
from rich.console import Console
from rich.table import Table

from vps_ops_toolkit.checks.docker_check import check_docker
from vps_ops_toolkit.checks.http_check import check_http
from vps_ops_toolkit.checks.server_check import (
    check_server,
    get_overall_status,
)
from vps_ops_toolkit.models import CheckStatus


app = typer.Typer()
console = Console()


def exit_for_status(status: CheckStatus) -> None:
    """
    Convert monitoring status to CLI exit code.

    0 = OK
    1 = WARNING
    2 = CRITICAL
    3 = ERROR
    """

    exit_codes = {
        CheckStatus.OK: 0,
        CheckStatus.WARNING: 1,
        CheckStatus.CRITICAL: 2,
        CheckStatus.ERROR: 3,
    }

    raise typer.Exit(
        code=exit_codes.get(
            status,
            3,
        )
    )


@app.callback()
def main():
    """VPS and Docker operations monitoring toolkit."""
    pass


@app.command()
def health(
    url: str,
    expected_status: int = 200,
    timeout: float = 5.0,
):
    """Check an HTTP health endpoint."""

    result = check_http(
        url=url,
        expected_status=expected_status,
        timeout=timeout,
    )

    console.print()
    console.print(f"[bold]{result.name}[/bold]")
    console.print(f"Status : {result.status.value}")
    console.print(f"Message: {result.message}")

    if result.response_time_ms is not None:
        console.print(
            f"Time   : {result.response_time_ms:.2f} ms"
        )

    exit_for_status(result.status)


@app.command()
def server(
    warning: float = 80.0,
    critical: float = 90.0,
):
    """Check CPU, memory, disk, and swap usage."""

    try:
        results = check_server(
            warning_threshold=warning,
            critical_threshold=critical,
        )

    except ValueError as exc:
        console.print()
        console.print("[bold]Server Status[/bold]")
        console.print(
            f"Status : {CheckStatus.ERROR.value}"
        )
        console.print(f"Message: {exc}")

        exit_for_status(CheckStatus.ERROR)
        return

    table = Table(
        title="Server Status"
    )

    table.add_column("Metric")
    table.add_column("Usage")
    table.add_column("Status")

    for result in results:
        table.add_row(
            result.name,
            result.message,
            result.status.value,
        )

    console.print()
    console.print(table)

    overall = get_overall_status(results)

    console.print()
    console.print(
        f"Overall: {overall.value}"
    )

    exit_for_status(overall)


@app.command("docker")
def docker_status():
    """Check Docker containers and health status."""

    result = check_docker()

    console.print()

    if result.status == CheckStatus.ERROR:
        console.print(
            "[bold]Docker Status[/bold]"
        )
        console.print(
            f"Status : {result.status.value}"
        )
        console.print(
            f"Message: {result.message}"
        )

        exit_for_status(result.status)
        return

    table = Table(
        title="Docker Status"
    )

    table.add_column("Container")
    table.add_column("State")
    table.add_column("Health")
    table.add_column(
        "Restarts",
        justify="right",
    )
    table.add_column("Status")

    for container in result.containers:
        table.add_row(
            container.name,
            container.state,
            container.health,
            str(container.restart_count),
            container.status.value,
        )

    console.print(table)

    console.print()
    console.print(
        f"Overall: {result.status.value}"
    )
    console.print(
        f"Message: {result.message}"
    )

    exit_for_status(result.status)


if __name__ == "__main__":
    app()