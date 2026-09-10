import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from vps_ops_toolkit.models import CheckStatus


ERROR_PATTERN = re.compile(
    r"(?:"
    r"\bERROR\b|"
    r"\bERR\b|"
    r"\bFATAL\b|"
    r"\bCRITICAL\b|"
    r"\bFAIL(?:ED)?\b|"
    r"\[(?:error|crit|alert|emerg)\]"
    r")",
    re.IGNORECASE,
)

WARNING_PATTERN = re.compile(
    r"(?:"
    r"\bWARN\b|"
    r"\bWARNING\b|"
    r"\[warn\]"
    r")",
    re.IGNORECASE,
)


@dataclass
class LogMatch:
    """A matched warning or error log entry."""

    line_number: int
    level: str
    text: str


@dataclass
class LogCheckResult:
    """Result of a log file check."""

    path: str
    status: CheckStatus
    error_count: int
    warning_count: int
    scanned_lines: int
    matches: list[LogMatch]
    message: str


def _detect_level(line: str) -> str | None:
    """Detect the severity level of a log line."""

    if ERROR_PATTERN.search(line):
        return "ERROR"

    if WARNING_PATTERN.search(line):
        return "WARNING"

    return None


def check_log(
    path: str,
    tail_lines: int = 1000,
    max_matches: int = 20,
    encoding: str = "utf-8",
) -> LogCheckResult:
    """
    Scan recent log lines for errors and warnings.

    Status rules:
        ERROR    -> log file could not be read
        CRITICAL -> one or more ERROR entries were found
        WARNING  -> one or more WARNING entries were found
        OK       -> no ERROR or WARNING entries were found
    """

    if tail_lines <= 0:
        raise ValueError(
            "tail_lines must be greater than 0"
        )

    if max_matches <= 0:
        raise ValueError(
            "max_matches must be greater than 0"
        )

    log_path = Path(path)

    try:
        recent_lines: deque[tuple[int, str]] = deque(
            maxlen=tail_lines
        )

        with log_path.open(
            "r",
            encoding=encoding,
            errors="replace",
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                recent_lines.append(
                    (
                        line_number,
                        line.rstrip("\r\n"),
                    )
                )

    except OSError as exc:
        return LogCheckResult(
            path=str(log_path),
            status=CheckStatus.ERROR,
            error_count=0,
            warning_count=0,
            scanned_lines=0,
            matches=[],
            message=f"Failed to read log file: {exc}",
        )

    matches: deque[LogMatch] = deque(
        maxlen=max_matches
    )

    error_count = 0
    warning_count = 0

    for line_number, line in recent_lines:
        level = _detect_level(line)

        if level is None:
            continue

        if level == "ERROR":
            error_count += 1
        elif level == "WARNING":
            warning_count += 1

        matches.append(
            LogMatch(
                line_number=line_number,
                level=level,
                text=line,
            )
        )

    if error_count > 0:
        status = CheckStatus.CRITICAL
        message = (
            f"{error_count} error(s) and "
            f"{warning_count} warning(s) found."
        )

    elif warning_count > 0:
        status = CheckStatus.WARNING
        message = (
            f"{warning_count} warning(s) found."
        )

    else:
        status = CheckStatus.OK
        message = (
            "No errors or warnings were found."
        )

    return LogCheckResult(
        path=str(log_path),
        status=status,
        error_count=error_count,
        warning_count=warning_count,
        scanned_lines=len(recent_lines),
        matches=list(matches),
        message=message,
    )