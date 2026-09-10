import typer
from rich.console import Console

from vps_ops_toolkit.checks.http_check import check_http
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

    if result.status == CheckStatus.CRITICAL:
        raise typer.Exit(2)

    raise typer.Exit(3)


if __name__ == "__main__":
    app()