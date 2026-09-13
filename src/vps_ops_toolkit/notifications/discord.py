import os
from dataclasses import dataclass

import httpx

from vps_ops_toolkit.models import CheckStatus


DISCORD_WEBHOOK_ENV = "VPS_OPS_DISCORD_WEBHOOK_URL"


@dataclass
class NotificationResult:
    """Result of a notification attempt."""

    status: CheckStatus
    message: str
    http_status: int | None = None


def send_discord_notification(
    message: str,
    webhook_url: str | None = None,
    timeout: float = 5.0,
) -> NotificationResult:
    """Send a message to Discord using a webhook."""

    if timeout <= 0:
        raise ValueError(
            "timeout must be greater than 0"
        )

    url = webhook_url or os.getenv(
        DISCORD_WEBHOOK_ENV
    )

    if not url:
        return NotificationResult(
            status=CheckStatus.ERROR,
            message=(
                f"{DISCORD_WEBHOOK_ENV} is not set."
            ),
        )

    try:
        response = httpx.post(
            url,
            json={
                "content": message,
            },
            timeout=timeout,
        )

        if 200 <= response.status_code < 300:
            return NotificationResult(
                status=CheckStatus.OK,
                message=(
                    "Discord notification sent successfully."
                ),
                http_status=response.status_code,
            )

        return NotificationResult(
            status=CheckStatus.ERROR,
            message=(
                "Discord webhook returned "
                f"HTTP {response.status_code}."
            ),
            http_status=response.status_code,
        )

    except httpx.RequestError as exc:
        return NotificationResult(
            status=CheckStatus.ERROR,
            message=(
                f"Discord notification failed: {exc}"
            ),
        )