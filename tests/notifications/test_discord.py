from unittest.mock import patch

import httpx
import pytest

from vps_ops_toolkit.models import CheckStatus
from vps_ops_toolkit.notifications.discord import (
    DISCORD_WEBHOOK_ENV,
    send_discord_notification,
)


@patch(
    "vps_ops_toolkit.notifications.discord.httpx.post"
)
def test_discord_notification_returns_ok_for_204(
    mock_post,
):
    response = httpx.Response(
        status_code=204,
    )

    mock_post.return_value = response

    result = send_discord_notification(
        message="Test notification",
        webhook_url="https://example.com/webhook",
    )

    assert result.status == CheckStatus.OK
    assert result.http_status == 204
    assert (
        result.message
        == "Discord notification sent successfully."
    )

    mock_post.assert_called_once_with(
        "https://example.com/webhook",
        json={
            "content": "Test notification",
        },
        timeout=5.0,
    )


@patch(
    "vps_ops_toolkit.notifications.discord.httpx.post"
)
def test_discord_notification_returns_ok_for_200(
    mock_post,
):
    mock_post.return_value = httpx.Response(
        status_code=200,
    )

    result = send_discord_notification(
        message="Test notification",
        webhook_url="https://example.com/webhook",
    )

    assert result.status == CheckStatus.OK
    assert result.http_status == 200


@patch(
    "vps_ops_toolkit.notifications.discord.httpx.post"
)
def test_discord_notification_returns_error_for_400(
    mock_post,
):
    mock_post.return_value = httpx.Response(
        status_code=400,
    )

    result = send_discord_notification(
        message="Test notification",
        webhook_url="https://example.com/webhook",
    )

    assert result.status == CheckStatus.ERROR
    assert result.http_status == 400
    assert (
        result.message
        == "Discord webhook returned HTTP 400."
    )


@patch(
    "vps_ops_toolkit.notifications.discord.httpx.post"
)
def test_discord_notification_returns_error_for_401(
    mock_post,
):
    mock_post.return_value = httpx.Response(
        status_code=401,
    )

    result = send_discord_notification(
        message="Test notification",
        webhook_url="https://example.com/webhook",
    )

    assert result.status == CheckStatus.ERROR
    assert result.http_status == 401
    assert (
        result.message
        == "Discord webhook returned HTTP 401."
    )


@patch(
    "vps_ops_toolkit.notifications.discord.httpx.post"
)
def test_discord_notification_returns_error_when_connection_fails(
    mock_post,
):
    request = httpx.Request(
        "POST",
        "https://example.com/webhook",
    )

    mock_post.side_effect = httpx.ConnectError(
        "Connection failed",
        request=request,
    )

    result = send_discord_notification(
        message="Test notification",
        webhook_url="https://example.com/webhook",
    )

    assert result.status == CheckStatus.ERROR
    assert result.http_status is None
    assert "Discord notification failed" in result.message
    assert "Connection failed" in result.message


def test_discord_notification_returns_error_when_webhook_is_not_set(
    monkeypatch,
):
    monkeypatch.delenv(
        DISCORD_WEBHOOK_ENV,
        raising=False,
    )

    result = send_discord_notification(
        message="Test notification",
    )

    assert result.status == CheckStatus.ERROR
    assert result.http_status is None
    assert (
        result.message
        == f"{DISCORD_WEBHOOK_ENV} is not set."
    )


def test_discord_notification_rejects_invalid_timeout():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than 0",
    ):
        send_discord_notification(
            message="Test notification",
            webhook_url="https://example.com/webhook",
            timeout=0,
        )