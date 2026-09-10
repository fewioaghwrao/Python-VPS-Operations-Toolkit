import math
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone

from vps_ops_toolkit.models import CheckStatus


@dataclass
class TlsCheckResult:
    host: str
    port: int
    status: CheckStatus
    message: str
    expires_at: datetime | None = None
    days_left: int | None = None


def _get_certificate_expiry(
    host: str,
    port: int,
    timeout: float,
) -> datetime:
    """
    Connect to a TLS server and return the certificate expiration date.

    The default SSL context validates:
    - certificate chain
    - hostname
    - certificate validity
    """

    context = ssl.create_default_context()

    with socket.create_connection(
        (host, port),
        timeout=timeout,
    ) as sock:
        with context.wrap_socket(
            sock,
            server_hostname=host,
        ) as tls_socket:
            certificate = tls_socket.getpeercert()

    not_after = certificate.get("notAfter")

    if not not_after:
        raise ValueError(
            "Certificate does not contain an expiration date."
        )

    timestamp = ssl.cert_time_to_seconds(not_after)

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    )


def check_tls(
    host: str,
    port: int = 443,
    warning_days: int = 30,
    critical_days: int = 14,
    timeout: float = 5.0,
    now: datetime | None = None,
) -> TlsCheckResult:
    """Check TLS certificate expiration."""

    if critical_days < 0:
        raise ValueError(
            "critical_days must be 0 or greater"
        )

    if warning_days <= critical_days:
        raise ValueError(
            "warning_days must be greater than critical_days"
        )

    if timeout <= 0:
        raise ValueError(
            "timeout must be greater than 0"
        )

    try:
        expires_at = _get_certificate_expiry(
            host=host,
            port=port,
            timeout=timeout,
        )

        current_time = now or datetime.now(timezone.utc)

        remaining_seconds = (
            expires_at - current_time
        ).total_seconds()

        days_left = math.floor(
            remaining_seconds / 86400
        )

        if remaining_seconds <= 0:
            status = CheckStatus.CRITICAL
            message = "TLS certificate has expired."

        elif days_left <= critical_days:
            status = CheckStatus.CRITICAL
            message = (
                f"TLS certificate expires in "
                f"{days_left} day(s)."
            )

        elif days_left <= warning_days:
            status = CheckStatus.WARNING
            message = (
                f"TLS certificate expires in "
                f"{days_left} day(s)."
            )

        else:
            status = CheckStatus.OK
            message = (
                f"TLS certificate is valid for "
                f"{days_left} more day(s)."
            )

        return TlsCheckResult(
            host=host,
            port=port,
            status=status,
            message=message,
            expires_at=expires_at,
            days_left=days_left,
        )

    except (
        ssl.SSLError,
        socket.timeout,
        socket.gaierror,
        OSError,
        ValueError,
    ) as exc:
        return TlsCheckResult(
            host=host,
            port=port,
            status=CheckStatus.ERROR,
            message=f"TLS check failed: {exc}",
        )