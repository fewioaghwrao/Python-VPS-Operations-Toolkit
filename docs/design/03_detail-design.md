# Python VPS Operations Toolkit 詳細設計書

- 文書名: 詳細設計書
- 対象: Python VPS Operations Toolkit
- 対象バージョン: 0.1.0
- 作成日: 2026-09-16
- 前提: 現行 Python 実装を正とする

---

## 1. パッケージ構成

```text
src/vps_ops_toolkit/
├─ __init__.py
├─ cli.py
├─ models.py
├─ checks/
│  ├─ __init__.py
│  ├─ deployment_check.py
│  ├─ docker_check.py
│  ├─ http_check.py
│  ├─ log_check.py
│  ├─ server_check.py
│  └─ tls_check.py
└─ notifications/
   ├─ __init__.py
   └─ discord.py
```

テスト:

```text
tests/
├─ checks/
├─ cli/
└─ notifications/
```

---

## 2. 共通モデル `models.py`

### 2.1 `CheckStatus`

```python
class CheckStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
```

全監視機能で共通利用する。

### 2.2 `CheckResult`

| Field | Type | 説明 |
|---|---|---|
| `name` | `str` | チェック名 / メトリクス名 |
| `status` | `CheckStatus` | 判定結果 |
| `message` | `str` | 表示メッセージ |
| `response_time_ms` | `float \| None` | HTTP 応答時間。非 HTTP では通常 `None` |

---

## 3. HTTP Check `checks/http_check.py`

### 3.1 `check_http`

```python
check_http(
    url: str,
    expected_status: int = 200,
    timeout: float = 5.0,
) -> CheckResult
```

### 3.2 処理手順

1. `perf_counter()` で開始時刻を記録する。
2. `httpx.get(url, timeout=timeout)` を実行する。
3. 応答後の経過時間を ms に換算する。
4. `response.status_code == expected_status` を比較する。
5. 一致なら `OK`、不一致なら `CRITICAL` を返す。
6. `httpx.RequestError` 発生時は `ERROR` を返す。

### 3.3 メッセージ

| 条件 | Message |
|---|---|
| 一致 | `HTTP {status}` |
| 不一致 | `Expected HTTP {expected}, but received HTTP {actual}` |
| RequestError | 例外文字列 |

### 3.4 注意点

`check_http` 単体では `expected_status` の 100～599 検証や `timeout > 0` の明示検証を行っていない。Deployment Check から呼び出す場合は Deployment 層で検証する。

---

## 4. Server Check `checks/server_check.py`

### 4.1 `_get_status`

```python
_get_status(
    value: float,
    warning_threshold: float,
    critical_threshold: float,
) -> CheckStatus
```

判定:

```text
value >= critical_threshold -> CRITICAL
value >= warning_threshold  -> WARNING
otherwise                   -> OK
```

### 4.2 `get_overall_status`

```python
get_overall_status(results: list[CheckResult]) -> CheckStatus
```

Priority map:

```python
OK=0, WARNING=1, CRITICAL=2, ERROR=3
```

`max(..., key=priority)` で最重度を返す。

### 4.3 `check_server`

```python
check_server(
    warning_threshold: float = 80.0,
    critical_threshold: float = 90.0,
    disk_path: str | None = None,
) -> list[CheckResult]
```

入力検証:

```text
warning_threshold >= critical_threshold -> ValueError
```

Disk path 未指定時:

```python
Path.home().anchor or "/"
```

取得 API:

| Metric | 実装 |
|---|---|
| CPU | `psutil.cpu_percent(interval=0.1)` |
| Memory | `psutil.virtual_memory().percent` |
| Disk | `psutil.disk_usage(disk_path).percent` |
| Swap | `psutil.swap_memory().percent` |

各値を `CheckResult` に変換し、`message` は小数 1 桁の `%` 文字列とする。

---

## 5. Docker Check `checks/docker_check.py`

### 5.1 `DockerContainerResult`

| Field | Type |
|---|---|
| `name` | `str` |
| `state` | `str` |
| `health` | `str` |
| `restart_count` | `int` |
| `status` | `CheckStatus` |

### 5.2 `DockerCheckResult`

| Field | Type |
|---|---|
| `status` | `CheckStatus` |
| `containers` | `list[DockerContainerResult]` |
| `message` | `str` |

### 5.3 `_get_container_status`

判定順序:

1. `state != "running"` → `CRITICAL`
2. `health == "unhealthy"` → `CRITICAL`
3. `health == "starting"` → `WARNING`
4. その他 → `OK`

HEALTHCHECK がない Container は `health="none"` とするため、running であれば OK となる。

### 5.4 `_get_overall_status`

- Container 0 件 → `WARNING`
- 1 件以上 → Status Priority の最大値

### 5.5 `check_docker`

```python
check_docker() -> DockerCheckResult
```

処理:

1. `docker.from_env()` で Client 作成。
2. `client.ping()` で Docker Engine 到達確認。
3. `client.containers.list(all=True)` で停止済みを含む全 Container 取得。
4. `container.attrs["State"]` から State / Health を取得。
5. `container.attrs["RestartCount"]` を取得。存在しない場合は 0。
6. Container 単位の Status を判定。
7. Container 名の lowercase 順にソート。
8. Overall を算出。
9. `finally` で Client を close する。

例外:

- `DockerException` → `ERROR`, `Docker error: ...`
- その他 Exception → `ERROR`, `Unexpected error: ...`
- close 時の例外は無視する。

---

## 6. TLS Check `checks/tls_check.py`

### 6.1 `TlsCheckResult`

| Field | Type |
|---|---|
| `host` | `str` |
| `port` | `int` |
| `status` | `CheckStatus` |
| `message` | `str` |
| `expires_at` | `datetime \| None` |
| `days_left` | `int \| None` |

### 6.2 `_get_certificate_expiry`

```python
_get_certificate_expiry(host: str, port: int, timeout: float) -> datetime
```

処理:

1. `ssl.create_default_context()` を作成。
2. `socket.create_connection((host, port), timeout=timeout)`。
3. `context.wrap_socket(..., server_hostname=host)` で TLS 接続。
4. `getpeercert()` から Certificate 取得。
5. `notAfter` を取得。
6. `ssl.cert_time_to_seconds()` で Epoch に変換。
7. UTC aware `datetime` へ変換して返す。

`notAfter` がない場合は `ValueError`。

### 6.3 `check_tls`

```python
check_tls(
    host: str,
    port: int = 443,
    warning_days: int = 30,
    critical_days: int = 14,
    timeout: float = 5.0,
    now: datetime | None = None,
) -> TlsCheckResult
```

入力検証:

- `critical_days < 0` → ValueError
- `warning_days <= critical_days` → ValueError
- `timeout <= 0` → ValueError

残日数:

```python
remaining_seconds = (expires_at - current_time).total_seconds()
days_left = math.floor(remaining_seconds / 86400)
```

判定:

1. `remaining_seconds <= 0` → CRITICAL / expired
2. `days_left <= critical_days` → CRITICAL
3. `days_left <= warning_days` → WARNING
4. otherwise → OK

以下の例外は `TlsCheckResult(ERROR)` に変換する。

- `ssl.SSLError`
- `socket.timeout`
- `socket.gaierror`
- `OSError`
- `ValueError`（証明書内容取得時）

---

## 7. Log Check `checks/log_check.py`

### 7.1 正規表現

ERROR:

```text
ERROR | ERR | FATAL | CRITICAL | FAIL | FAILED |
[error] | [crit] | [alert] | [emerg]
```

WARNING:

```text
WARN | WARNING | [warn]
```

いずれも case-insensitive。

### 7.2 `_detect_level`

ERROR Pattern を先に判定し、その後 WARNING Pattern を判定する。
同一行が両方に該当する場合は ERROR を優先する。

### 7.3 `LogMatch`

| Field | Type |
|---|---|
| `line_number` | `int` |
| `level` | `str` |
| `text` | `str` |

### 7.4 `LogCheckResult`

| Field | Type |
|---|---|
| `path` | `str` |
| `status` | `CheckStatus` |
| `error_count` | `int` |
| `warning_count` | `int` |
| `scanned_lines` | `int` |
| `matches` | `list[LogMatch]` |
| `message` | `str` |

### 7.5 `check_log`

```python
check_log(
    path: str,
    tail_lines: int = 1000,
    max_matches: int = 20,
    encoding: str = "utf-8",
) -> LogCheckResult
```

入力検証:

- `tail_lines <= 0` → ValueError
- `max_matches <= 0` → ValueError

読込:

```python
deque(maxlen=tail_lines)
```

を使い、全ファイルを逐次走査しつつ直近 N 行だけ保持する。

ファイルは以下で開く。

```python
open(..., encoding=encoding, errors="replace")
```

一致表示も `deque(maxlen=max_matches)` のため、直近 M 件のみ保持する。

判定:

- error_count > 0 → CRITICAL
- warning_count > 0 → WARNING
- otherwise → OK
- OSError → ERROR

---

## 8. Deployment Check `checks/deployment_check.py`

### 8.1 `DeploymentStepResult`

| Field | Type |
|---|---|
| `name` | `str` |
| `url` | `str` |
| `status` | `CheckStatus` |
| `message` | `str` |
| `response_time_ms` | `float \| None` |

### 8.2 `DeploymentCheckResult`

| Field | Type |
|---|---|
| `status` | `CheckStatus` |
| `checks` | `list[DeploymentStepResult]` |
| `message` | `str` |

### 8.3 `_check_endpoint`

`check_http()` を呼び出し、`CheckResult` を `DeploymentStepResult` に変換する。

### 8.4 `check_deployment`

```python
check_deployment(
    health_url: str,
    api_url: str | None = None,
    health_expected_status: int = 200,
    api_expected_status: int = 200,
    timeout: float = 5.0,
) -> DeploymentCheckResult
```

入力検証:

- `timeout <= 0` → ValueError
- Health Expected Status が 100～599 外 → ValueError
- API Expected Status が 100～599 外 → ValueError

処理:

1. Health を必ず `_check_endpoint(name="Health")` で確認。
2. `api_url` が truthy の場合のみ API を追加確認。
3. 各 Step の最重度を Overall とする。
4. `status == OK` の件数を集計。
5. Message を `{successful}/{total} deployment check(s) passed.` とする。

---

## 9. Discord Notification `notifications/discord.py`

### 9.1 定数

```python
DISCORD_WEBHOOK_ENV = "VPS_OPS_DISCORD_WEBHOOK_URL"
```

### 9.2 `NotificationResult`

| Field | Type |
|---|---|
| `status` | `CheckStatus` |
| `message` | `str` |
| `http_status` | `int \| None` |

### 9.3 `send_discord_notification`

```python
send_discord_notification(
    message: str,
    webhook_url: str | None = None,
    timeout: float = 5.0,
) -> NotificationResult
```

処理:

1. `timeout <= 0` なら ValueError。
2. `webhook_url` 引数があれば優先使用。
3. 未指定なら環境変数 `VPS_OPS_DISCORD_WEBHOOK_URL` を取得。
4. URL がなければ `ERROR` を返す。
5. `httpx.post(url, json={"content": message}, timeout=timeout)` を実行。
6. `200 <= status_code < 300` → OK。
7. 非 2xx → ERROR。
8. `httpx.RequestError` → ERROR。

---

## 10. CLI `cli.py`

### 10.1 `exit_for_status`

```python
exit_for_status(status: CheckStatus) -> None
```

Mapping:

```python
{
    OK: 0,
    WARNING: 1,
    CRITICAL: 2,
    ERROR: 3,
}
```

`typer.Exit(code=...)` を raise する。
未知値は fallback `3`。

### 10.2 `build_deployment_notification`

Deployment 結果から Discord 用 Plain Text を生成する。

形式:

```text
VPS Operations Toolkit

Check: Deployment Check
Status: {status}
Message: {message}

Results:
- Health: {status} ({message})
- API: {status} ({message})
```

### 10.3 `health`

- `check_http()` を呼び出す。
- Name / Status / Message / Response Time を表示。
- `exit_for_status(result.status)`。

### 10.4 `server`

- `check_server()` を呼ぶ。
- ValueError は ERROR / Exit 3。
- Rich Table に Metric / Usage / Status を表示。
- `get_overall_status()` で Overall 算出。
- Overall の Exit Code で終了。

### 10.5 `docker`

- `check_docker()` を呼ぶ。
- ERROR 時は Table を作らず Status / Message を表示。
- 通常は Container / State / Health / Restarts / Status を Table 表示。
- Overall の Exit Code で終了。

### 10.6 `tls`

- `check_tls()` を呼ぶ。
- 入力 ValueError は ERROR / Exit 3。
- Host / Port / Expires / Days Left / Status / Message を表示。
- Result Status で終了。

### 10.7 `logs`

- `check_log()` を呼ぶ。
- 入力 ValueError は ERROR / Exit 3。
- Path / Scanned / Errors / Warnings / Overall / Message を表示。
- Match が存在すれば Line / Level / Log を Table 表示。
- Result Status で終了。

### 10.8 `deploy-check`

- `check_deployment()` を呼ぶ。
- 入力 ValueError は ERROR / Exit 3。
- Check / URL / Result / Time / Status を Table 表示。
- `--notify` 未指定なら通知しない。
- `--notify` + Overall OK なら `Notification: skipped`。
- `--notify` + non-OK なら `build_deployment_notification()` → `send_discord_notification()`。
- Discord 成否を表示する。
- 最後は必ず Deployment Result の Status で終了する。

重要仕様:

```text
Deployment = CRITICAL
Discord     = ERROR
Final Exit  = 2
```

通知障害により監視対象の異常を Exit 3 へ置き換えない。

### 10.9 `notify-test`

固定メッセージを Discord へ送る。

```text
VPS Operations Toolkit

Status: OK
Test notification successfully sent.

Source: notify-test
```

ValueError は ERROR / Exit 3。
NotificationResult の Status で終了する。

---

## 11. CLI パラメータ詳細

| Command | Parameter | Type | Default | Validation / Notes |
|---|---|---:|---:|---|
| health | url | str | required | HTTP GET 対象 |
| health | expected_status | int | 200 | check_http 自体では明示範囲検証なし |
| health | timeout | float | 5.0 | HTTPX に渡す |
| server | warning | float | 80.0 | critical 未満必須 |
| server | critical | float | 90.0 | warning より大 |
| tls | host | str | required | SNI と hostname 検証に使用 |
| tls | port | int | 443 | TCP/TLS Port |
| tls | warning_days | int | 30 | critical_days より大 |
| tls | critical_days | int | 14 | 0以上 |
| tls | timeout | float | 5.0 | 0より大 |
| logs | path | str | required | Log file path |
| logs | tail_lines | int | 1000 | 1以上 |
| logs | max_matches | int | 20 | 1以上 |
| deploy-check | health_url | str | required | Health Endpoint |
| deploy-check | api_url | str \| None | None | Optional |
| deploy-check | health_expected_status | int | 200 | 100～599 |
| deploy-check | api_expected_status | int | 200 | 100～599 |
| deploy-check | timeout | float | 5.0 | 0より大 |
| deploy-check | notify | bool | False | non-OK 時 Discord |
| notify-test | timeout | float | 5.0 | 0より大 |

---

## 12. テスト設計対応表

現行テスト数: **42**

| Test Suite | Test Count | 主な確認内容 |
|---|---:|---|
| HTTP Monitor | 3 | 200 OK / Expected mismatch / Connection error |
| Server Monitor | 4 | OK / WARNING / CRITICAL / Invalid thresholds |
| Docker Monitor | 6 | healthy / exited / unhealthy / starting / no containers / daemon unavailable |
| TLS Monitor | 6 | OK / WARNING / CRITICAL / expired / connection error / invalid thresholds |
| Log Monitor | 6 | clean / warning / error / nginx error / missing file / invalid tail lines |
| Deployment Check | 6 | health only / health+api / expected 401 / critical / connection error / invalid timeout |
| Discord Notification | 7 | HTTP 204 / 200 / 400 / 401 / connection error / env missing / invalid timeout |
| CLI Notification | 4 | OK skip / CRITICAL send / notification failure preserves exit / no notify option |
| **Total** | **42** | |

---

## 13. GitHub Actions 詳細

File: `.github/workflows/ci.yml`

Trigger:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

Job:

- Runner: `ubuntu-latest`
- Python: `3.12`
- Checkout: `actions/checkout@v4`
- Python setup: `actions/setup-python@v5`
- pip upgrade
- `python -m pip install -e ".[dev]"`
- `pytest -v`

CI 内で実 VPS への SSH / 実 Discord Webhook 通知は行わない。

---

## 14. Secret / Git 管理詳細

`.env.example`:

```dotenv
# Discord notification
VPS_OPS_DISCORD_WEBHOOK_URL=
```

`.gitignore` では以下を除外する。

```text
.env
.env.*
logs/
*.log
```

ただし `.env.example` のみ例外として Git 管理する。

```text
!.env.example
```

---

## 15. 現行設計上の制約

- Docker Monitor は全 Container を対象とし、監視対象を絞り込めない。
- 停止済み Container も `all=True` により対象となり、CRITICAL になる。
- RestartCount は表示のみで、増加検知には使用しない。
- Server Monitor は remote host ではなく実行マシン自身を監視する。
- Log Monitor は File Path を対象とし、`docker logs` を直接取得しない。
- `.env` ファイルを自動ロードする処理は実装していない。環境変数は Shell / OS 側で設定する必要がある。
- 通知先は現行では Discord Webhook のみ。
- 定期実行スケジューラは内包しない。cron / systemd timer 等から呼び出す構成を想定できるが、スケジューラ自体は本ツールの実装外である。
