from dataclasses import dataclass
from enum import Enum


class CheckStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    response_time_ms: float | None = None