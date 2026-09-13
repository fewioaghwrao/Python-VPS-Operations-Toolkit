import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from vps_ops_toolkit.checks.deployment_check import check_deployment
from vps_ops_toolkit.checks.docker_check import check_docker
from vps_ops_toolkit.checks.http_check import check_http
from vps_ops_toolkit.checks.log_check import check_log
from vps_ops_toolkit.checks.server_check import (
    check_server,
    get_overall_status,
)
from vps_ops_toolkit.checks.tls_check import check_tls
from vps_ops_toolkit.models import CheckStatus
from vps_ops_toolkit.notifications.discord import (
    send_discord_notification,
)


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
        code=exit_codes.get(status, 3)
    )


def build_deployment_notification(result) -> str:
    """Build a Discord message for a deployment failure."""

    lines = [
        "VPS Operations Toolkit",
        "",
        "Check: Deployment Check",
        f"Status: {result.status.value}",
        f"Message: {result.message}",
        "",
        "Results:",
    ]

    for check in result.checks:
        lines.append(
            f"- {check.name}: "
            f"{check.status.value} "
            f"({check.message})"
        )

    return "\n".join(lines)


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
    console.print(
        f"Status : {result.status.value}"
    )
    console.print(
        f"Message: {result.message}"
    )

    if result.response_time_ms is not None:
        console.print(
            f"Time   : "
            f"{result.response_time_ms:.2f} ms"
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
        console.print(
            "[bold]Server Status[/bold]"
        )
        console.print(
            f"Status : {CheckStatus.ERROR.value}"
        )
        console.print(
            f"Message: {exc}"
        )

        exit_for_status(
            CheckStatus.ERROR
        )
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

        exit_for_status(
            result.status
        )
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


@app.command()
def tls(
    host: str,
    port: int = 443,
    warning_days: int = 30,
    critical_days: int = 14,
    timeout: float = 5.0,
):
    """Check TLS certificate expiration."""

    try:
        result = check_tls(
            host=host,
            port=port,
            warning_days=warning_days,
            critical_days=critical_days,
            timeout=timeout,
        )

    except ValueError as exc:
        console.print()
        console.print(
            "[bold]TLS Certificate Status[/bold]"
        )
        console.print(
            f"Status : {CheckStatus.ERROR.value}"
        )
        console.print(
            f"Message: {exc}"
        )

        exit_for_status(
            CheckStatus.ERROR
        )
        return

    console.print()
    console.print(
        "[bold]TLS Certificate Status[/bold]"
    )

    console.print(
        f"Host      : {result.host}"
    )
    console.print(
        f"Port      : {result.port}"
    )

    if result.expires_at is not None:
        console.print(
            "Expires   : "
            f"{result.expires_at:%Y-%m-%d %H:%M:%S} UTC"
        )

    if result.days_left is not None:
        console.print(
            f"Days Left : {result.days_left}"
        )

    console.print(
        f"Status    : {result.status.value}"
    )
    console.print(
        f"Message   : {result.message}"
    )

    exit_for_status(result.status)


@app.command("logs")
def logs(
    path: str,
    tail_lines: int = 1000,
    max_matches: int = 20,
):
    """Scan a log file for errors and warnings."""

    try:
        result = check_log(
            path=path,
            tail_lines=tail_lines,
            max_matches=max_matches,
        )

    except ValueError as exc:
        console.print()
        console.print(
            "[bold]Log Status[/bold]"
        )
        console.print(
            f"Status : {CheckStatus.ERROR.value}"
        )
        console.print(
            f"Message: {exc}"
        )

        exit_for_status(
            CheckStatus.ERROR
        )
        return

    console.print()
    console.print(
        "[bold]Log Status[/bold]"
    )

    console.print(
        f"Path      : {result.path}"
    )
    console.print(
        f"Scanned   : "
        f"{result.scanned_lines} line(s)"
    )
    console.print(
        f"Errors    : {result.error_count}"
    )
    console.print(
        f"Warnings  : {result.warning_count}"
    )
    console.print(
        f"Overall   : {result.status.value}"
    )
    console.print(
        f"Message   : {result.message}"
    )

    if result.matches:
        table = Table(
            title="Recent Matches"
        )

        table.add_column(
            "Line",
            justify="right",
        )
        table.add_column("Level")
        table.add_column("Log")

        for match in result.matches:
            table.add_row(
                str(match.line_number),
                match.level,
                Text(match.text),
            )

        console.print()
        console.print(table)

    exit_for_status(result.status)


@app.command("deploy-check")
def deploy_check(
    health_url: str,
    api_url: str | None = None,
    health_expected_status: int = 200,
    api_expected_status: int = 200,
    timeout: float = 5.0,
    notify: bool = typer.Option(
        False,
        "--notify",
        help=(
            "Send a Discord notification "
            "when the deployment check is not OK."
        ),
    ),
):
    """
    Verify a deployment using health and API endpoints.

    When --notify is specified, WARNING, CRITICAL,
    and ERROR results are sent to Discord.
    """

    try:
        result = check_deployment(
            health_url=health_url,
            api_url=api_url,
            health_expected_status=(
                health_expected_status
            ),
            api_expected_status=(
                api_expected_status
            ),
            timeout=timeout,
        )

    except ValueError as exc:
        console.print()
        console.print(
            "[bold]Deployment Check[/bold]"
        )
        console.print(
            f"Status : {CheckStatus.ERROR.value}"
        )
        console.print(
            f"Message: {exc}"
        )

        # Invalid command arguments are treated
        # as an execution error.
        exit_for_status(
            CheckStatus.ERROR
        )
        return

    table = Table(
        title="Deployment Check"
    )

    table.add_column("Check")
    table.add_column("URL")
    table.add_column("Result")
    table.add_column("Time")
    table.add_column("Status")

    for check in result.checks:
        response_time = "-"

        if check.response_time_ms is not None:
            response_time = (
                f"{check.response_time_ms:.2f} ms"
            )

        table.add_row(
            check.name,
            check.url,
            check.message,
            response_time,
            check.status.value,
        )

    console.print()
    console.print(table)

    console.print()
    console.print(
        f"Overall: {result.status.value}"
    )
    console.print(
        f"Message: {result.message}"
    )

    # Only notify about abnormal states.
    if notify:
        if result.status == CheckStatus.OK:
            console.print()
            console.print(
                "Notification: skipped "
                "(deployment status is OK)."
            )

        else:
            message = (
                build_deployment_notification(
                    result
                )
            )

            notification = (
                send_discord_notification(
                    message=message,
                )
            )

            console.print()

            if (
                notification.status
                == CheckStatus.OK
            ):
                console.print(
                    "Notification: "
                    "Discord message sent."
                )

            else:
                console.print(
                    "Notification: "
                    "Discord delivery failed."
                )
                console.print(
                    f"Notification Error: "
                    f"{notification.message}"
                )

    # IMPORTANT:
    # Discord notification failure must not
    # replace the deployment result.
    exit_for_status(result.status)


@app.command("notify-test")
def notify_test(
    timeout: float = 5.0,
):
    """Send a test notification to Discord."""

    message = (
        "VPS Operations Toolkit\n\n"
        "Status: OK\n"
        "Test notification successfully sent.\n\n"
        "Source: notify-test"
    )

    try:
        result = (
            send_discord_notification(
                message=message,
                timeout=timeout,
            )
        )

    except ValueError as exc:
        console.print()
        console.print(
            "[bold]Discord Notification[/bold]"
        )
        console.print(
            f"Status : {CheckStatus.ERROR.value}"
        )
        console.print(
            f"Message: {exc}"
        )

        exit_for_status(
            CheckStatus.ERROR
        )
        return

    console.print()
    console.print(
        "[bold]Discord Notification[/bold]"
    )
    console.print(
        f"Status : {result.status.value}"
    )
    console.print(
        f"Message: {result.message}"
    )

    if result.http_status is not None:
        console.print(
            f"HTTP   : {result.http_status}"
        )

    exit_for_status(result.status)


if __name__ == "__main__":
    app()