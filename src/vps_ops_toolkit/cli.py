import typer
from rich.console import Console
from rich.table import Table

from vps_ops_toolkit.checks.http_check import check_http
from vps_ops_toolkit.checks.server_check import (
    check_server,
    get_overall_status,
)
from vps_ops_toolkit.models import CheckStatus


app = typer.Typer()
console = Console()


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

    if result.status == CheckStatus.OK:
        raise typer.Exit(0)

    if result.status == CheckStatus.WARNING:
        raise typer.Exit(1)

    if result.status == CheckStatus.CRITICAL:
        raise typer.Exit(2)

    raise typer.Exit(3)


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
        console.print(f"[bold]Server Status[/bold]")
        console.print(f"Status : {CheckStatus.ERROR.value}")
        console.print(f"Message: {exc}")

        raise typer.Exit(3)

    table = Table(title="Server Status")

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
    console.print(f"Overall: {overall.value}")

    if overall == CheckStatus.OK:
        raise typer.Exit(0)

    if overall == CheckStatus.WARNING:
        raise typer.Exit(1)

    if overall == CheckStatus.CRITICAL:
        raise typer.Exit(2)

    raise typer.Exit(3)


if __name__ == "__main__":
    app()