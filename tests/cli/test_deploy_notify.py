from unittest.mock import patch

from typer.testing import CliRunner

from vps_ops_toolkit.checks.deployment_check import (
    DeploymentCheckResult,
    DeploymentStepResult,
)
from vps_ops_toolkit.cli import app
from vps_ops_toolkit.models import CheckStatus
from vps_ops_toolkit.notifications.discord import (
    NotificationResult,
)


runner = CliRunner()


@patch("vps_ops_toolkit.cli.send_discord_notification")
@patch("vps_ops_toolkit.cli.check_deployment")
def test_deploy_check_notify_skips_notification_when_ok(
    mock_check_deployment,
    mock_send_notification,
):
    mock_check_deployment.return_value = DeploymentCheckResult(
        status=CheckStatus.OK,
        checks=[
            DeploymentStepResult(
                name="Health",
                url="https://example.com/health",
                status=CheckStatus.OK,
                message="HTTP 200",
                response_time_ms=100.0,
            ),
        ],
        message="1/1 deployment check(s) passed.",
    )

    result = runner.invoke(
        app,
        [
            "deploy-check",
            "https://example.com/health",
            "--notify",
        ],
    )

    assert result.exit_code == 0

    assert "Overall: OK" in result.stdout

    assert (
        "Notification: skipped "
        "(deployment status is OK)."
        in result.stdout
    )

    mock_send_notification.assert_not_called()


@patch("vps_ops_toolkit.cli.send_discord_notification")
@patch("vps_ops_toolkit.cli.check_deployment")
def test_deploy_check_notify_sends_discord_when_critical(
    mock_check_deployment,
    mock_send_notification,
):
    mock_check_deployment.return_value = DeploymentCheckResult(
        status=CheckStatus.CRITICAL,
        checks=[
            DeploymentStepResult(
                name="Health",
                url="https://example.com/health",
                status=CheckStatus.OK,
                message="HTTP 200",
                response_time_ms=100.0,
            ),
            DeploymentStepResult(
                name="API",
                url="https://example.com/api",
                status=CheckStatus.CRITICAL,
                message=(
                    "Expected HTTP 200, "
                    "but received HTTP 401"
                ),
                response_time_ms=120.0,
            ),
        ],
        message="1/2 deployment check(s) passed.",
    )

    mock_send_notification.return_value = NotificationResult(
        status=CheckStatus.OK,
        message="Discord notification sent successfully.",
        http_status=204,
    )

    result = runner.invoke(
        app,
        [
            "deploy-check",
            "https://example.com/health",
            "--api-url",
            "https://example.com/api",
            "--notify",
        ],
    )

    assert result.exit_code == 2

    assert "Overall: CRITICAL" in result.stdout
    assert (
        "Notification: Discord message sent."
        in result.stdout
    )

    mock_send_notification.assert_called_once()

    notification_message = (
        mock_send_notification.call_args.kwargs["message"]
    )

    assert "Check: Deployment Check" in notification_message
    assert "Status: CRITICAL" in notification_message
    assert "Health: OK" in notification_message
    assert "API: CRITICAL" in notification_message


@patch("vps_ops_toolkit.cli.send_discord_notification")
@patch("vps_ops_toolkit.cli.check_deployment")
def test_deploy_check_keeps_critical_exit_code_when_notification_fails(
    mock_check_deployment,
    mock_send_notification,
):
    mock_check_deployment.return_value = DeploymentCheckResult(
        status=CheckStatus.CRITICAL,
        checks=[
            DeploymentStepResult(
                name="Health",
                url="https://example.com/health",
                status=CheckStatus.CRITICAL,
                message=(
                    "Expected HTTP 200, "
                    "but received HTTP 503"
                ),
                response_time_ms=150.0,
            ),
        ],
        message="0/1 deployment check(s) passed.",
    )

    mock_send_notification.return_value = NotificationResult(
        status=CheckStatus.ERROR,
        message="Discord webhook returned HTTP 500.",
        http_status=500,
    )

    result = runner.invoke(
        app,
        [
            "deploy-check",
            "https://example.com/health",
            "--notify",
        ],
    )

    # Important:
    # Notification failure must NOT replace
    # the deployment CRITICAL exit code.
    assert result.exit_code == 2

    assert "Overall: CRITICAL" in result.stdout

    assert (
        "Notification: Discord delivery failed."
        in result.stdout
    )

    assert (
        "Discord webhook returned HTTP 500."
        in result.stdout
    )

    mock_send_notification.assert_called_once()


@patch("vps_ops_toolkit.cli.send_discord_notification")
@patch("vps_ops_toolkit.cli.check_deployment")
def test_deploy_check_does_not_notify_without_notify_option(
    mock_check_deployment,
    mock_send_notification,
):
    mock_check_deployment.return_value = DeploymentCheckResult(
        status=CheckStatus.CRITICAL,
        checks=[
            DeploymentStepResult(
                name="API",
                url="https://example.com/api",
                status=CheckStatus.CRITICAL,
                message="HTTP 503",
                response_time_ms=100.0,
            ),
        ],
        message="0/1 deployment check(s) passed.",
    )

    result = runner.invoke(
        app,
        [
            "deploy-check",
            "https://example.com/health",
        ],
    )

    assert result.exit_code == 2

    assert "Overall: CRITICAL" in result.stdout

    mock_send_notification.assert_not_called()