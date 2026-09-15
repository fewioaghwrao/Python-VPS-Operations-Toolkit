# Python VPS Operations Toolkit 要件定義書

- 文書名: 要件定義書
- 対象: Python VPS Operations Toolkit
- 対象バージョン: 0.1.0
- 作成日: 2026-09-16
- 根拠: 現行リポジトリの README、`pyproject.toml`、実装コード、テストコード、GitHub Actions 設定

> 本書は、現行実装から確認できる仕様を基準に整理した「実装準拠」の要件定義書です。将来構想や未実装事項は、現行要件と分離して記載します。

---

## 1. 目的

VPS / Docker 環境の運用時に個別に実施していた以下の確認作業を、1つの Python CLI から実行できるようにする。

- HTTP エンドポイントの疎通確認
- VPS / 実行マシンの CPU・Memory・Disk・Swap 使用率確認
- Docker コンテナの稼働状態・Health 状態確認
- TLS 証明書の有効期限確認
- ログファイル内の ERROR / WARNING 検出
- デプロイ後の Health / API エンドポイント確認
- 異常時の Discord Webhook 通知

運用者が目視確認だけでなく、Exit Code を利用してシェルスクリプトや CI/CD から判定できることも目的とする。

---

## 2. システム概要

本ツールは `vps-ops` コマンドとして利用する CLI 運用支援ツールである。

```text
Operator / CI / Script
        |
        v
     vps-ops
        |
        +-- HTTP Health Check
        +-- Server Monitor
        +-- Docker Monitor
        +-- TLS Monitor
        +-- Log Monitor
        +-- Deployment Check
        +-- Discord Notification
```

Web UI や常駐サーバー機能は持たず、コマンド実行時に対象を確認して結果を標準出力と Exit Code で返す。

---

## 3. 利用者

| 利用者 | 利用目的 |
|---|---|
| VPS / Web API 運用者 | 稼働状況、リソース、証明書、ログ、デプロイ結果の確認 |
| 開発者 | デプロイ後の疎通確認、異常検知、手動運用の省力化 |
| CI/CD・シェルスクリプト | Exit Code による自動判定 |

---

## 4. 対象範囲

### 4.1 対象機能

| ID | 機能 | 概要 |
|---|---|---|
| FR-01 | HTTP Health Check | 指定 URL に HTTP リクエストを行い、期待 HTTP Status と比較する |
| FR-02 | Server Monitor | 実行マシンの CPU / Memory / Disk / Swap 使用率を確認する |
| FR-03 | Docker Monitor | Docker Engine に接続し、全コンテナの State / Health / RestartCount を確認する |
| FR-04 | TLS Certificate Monitor | 指定ホストへ TLS 接続し、証明書の有効期限を確認する |
| FR-05 | Log Monitor | 指定ログファイルの直近行から ERROR / WARNING を検出する |
| FR-06 | Deployment Check | Health Endpoint と任意の API Endpoint をまとめて確認する |
| FR-07 | Discord Notification | Discord Webhook へテスト通知または Deployment 異常通知を送る |
| FR-08 | Common Status / Exit Code | 全機能で共通の監視ステータスと Exit Code を使用する |
| FR-09 | Automated Tests / CI | pytest を GitHub Actions 上で実行し、main への push / pull request で検証する |

### 4.2 現行バージョンで対象外

以下は README の Future Improvements に位置付けられており、現行要件の対象外とする。

- 監視対象 Docker コンテナの個別指定
- RestartCount の前回値保持・増加検知
- SSH 経由でのリモート VPS 監視
- Docker logs の直接解析
- YAML 設定ファイル
- 複数チェックを一括実行する `check-all`
- Slack / Microsoft Teams 通知
- ツール自身による定期実行機能
- JSON 出力
- デプロイ処理そのものの自動化

---

## 5. 機能要件

### 5.1 FR-01 HTTP Health Check

1. 利用者は URL を指定できること。
2. 期待 HTTP Status を指定できること。既定値は `200` とする。
3. Timeout を指定できること。既定値は `5.0` 秒とする。
4. 実際の HTTP Status が期待値と一致した場合、`OK` とすること。
5. 実際の HTTP Status が期待値と異なる場合、`CRITICAL` とすること。
6. HTTP 接続処理が失敗した場合、`ERROR` とすること。
7. レスポンス取得時は応答時間をミリ秒で取得・表示できること。

CLI:

```text
vps-ops health URL [--expected-status N] [--timeout SEC]
```

### 5.2 FR-02 Server Monitor

1. コマンドを実行したマシン自身を監視対象とすること。
2. CPU 使用率を取得すること。
3. Memory 使用率を取得すること。
4. Disk 使用率を取得すること。
5. Swap 使用率を取得すること。
6. Warning 閾値の既定値を `80%` とすること。
7. Critical 閾値の既定値を `90%` とすること。
8. `value >= critical` は `CRITICAL`、`value >= warning` は `WARNING`、それ未満は `OK` とすること。
9. Warning 閾値が Critical 閾値以上の場合は入力エラーとして扱うこと。
10. Overall は各項目のうち最も重いステータスとすること。

CLI:

```text
vps-ops server [--warning PERCENT] [--critical PERCENT]
```

### 5.3 FR-03 Docker Monitor

1. Docker Engine へ接続できること。
2. Docker Engine 到達確認を行うこと。
3. Docker Engine 上の全コンテナ（停止済みを含む）を取得すること。
4. 各コンテナについて以下を表示すること。
   - Container Name
   - State
   - Health
   - RestartCount
   - Status
5. `state != running` の場合は `CRITICAL` とすること。
6. Health が `unhealthy` の場合は `CRITICAL` とすること。
7. Health が `starting` の場合は `WARNING` とすること。
8. `running` かつ Health が `healthy` または HEALTHCHECK 未設定 (`none`) の場合は `OK` とすること。
9. コンテナが 0 件の場合は `WARNING` とすること。
10. Docker Engine に接続できない場合は `ERROR` とすること。
11. Overall は最も重いコンテナステータスとすること。

CLI:

```text
vps-ops docker
```

### 5.4 FR-04 TLS Certificate Monitor

1. Host を指定して TLS 接続できること。
2. Port の既定値を `443` とすること。
3. 証明書チェーンとホスト名を検証すること。
4. 証明書の有効期限を UTC で取得すること。
5. 残日数を整数日で算出すること。
6. Warning 日数の既定値を `30` 日とすること。
7. Critical 日数の既定値を `14` 日とすること。
8. 期限切れ、または残日数が Critical 以下の場合は `CRITICAL` とすること。
9. 残日数が Warning 以下の場合は `WARNING` とすること。
10. 上記以外は `OK` とすること。
11. TLS / DNS / Socket 等の接続失敗時は `ERROR` とすること。
12. `critical_days < 0`、`warning_days <= critical_days`、`timeout <= 0` は入力エラーとすること。

CLI:

```text
vps-ops tls HOST [--port PORT] [--warning-days DAYS] [--critical-days DAYS] [--timeout SEC]
```

### 5.5 FR-05 Log Monitor

1. 指定したテキストログファイルを読み込めること。
2. 既定で直近 `1000` 行を解析すること。
3. 表示する一致ログは既定で直近 `20` 件までとすること。
4. 以下を ERROR として検出すること。
   - `ERROR`
   - `ERR`
   - `FATAL`
   - `CRITICAL`
   - `FAIL` / `FAILED`
   - nginx `[error]` / `[crit]` / `[alert]` / `[emerg]`
5. 以下を WARNING として検出すること。
   - `WARN`
   - `WARNING`
   - nginx `[warn]`
6. ERROR が 1 件以上あれば `CRITICAL` とすること。
7. ERROR がなく WARNING が 1 件以上あれば `WARNING` とすること。
8. ERROR / WARNING がなければ `OK` とすること。
9. ファイル読込失敗時は `ERROR` とすること。
10. `tail_lines <= 0` または `max_matches <= 0` は入力エラーとすること。

CLI:

```text
vps-ops logs PATH [--tail-lines N] [--max-matches N]
```

### 5.6 FR-06 Deployment Check

1. Health URL を必須入力とすること。
2. API URL を任意入力とすること。
3. Health / API ごとに期待 HTTP Status を指定できること。
4. Health / API の既定期待値を `200` とすること。
5. 認証必須 API 等について `401` など任意の HTTP Status を正常期待値として指定できること。
6. Timeout の既定値を `5.0` 秒とすること。
7. 各 Endpoint の判定には HTTP Health Check の処理を再利用すること。
8. Overall は各 Endpoint の最も重いステータスとすること。
9. `n/total deployment check(s) passed.` 形式で成功件数を表示すること。
10. HTTP Status の入力は `100` ～ `599` の範囲とすること。
11. Timeout は `0` より大きいこと。

CLI:

```text
vps-ops deploy-check HEALTH_URL \
  [--api-url URL] \
  [--health-expected-status N] \
  [--api-expected-status N] \
  [--timeout SEC] \
  [--notify]
```

### 5.7 FR-07 Discord Notification

1. Discord Webhook URL を環境変数 `VPS_OPS_DISCORD_WEBHOOK_URL` から取得できること。
2. Webhook URL をコードへハードコードしないこと。
3. 2xx 応答を通知成功 (`OK`) とすること。
4. 2xx 以外の応答を通知失敗 (`ERROR`) とすること。
5. HTTP 通信失敗を通知失敗 (`ERROR`) とすること。
6. Webhook URL 未設定時は `ERROR` とすること。
7. `notify-test` コマンドにより単独の通知テストを実行できること。
8. `deploy-check --notify` 指定時、Deployment 結果が `OK` の場合は通知を送信しないこと。
9. `deploy-check --notify` 指定時、Deployment 結果が `WARNING` / `CRITICAL` / `ERROR` の場合に Discord 通知を実行すること。
10. Discord 通知自体に失敗しても、Deployment Check 本来の Exit Code を上書きしないこと。

### 5.8 FR-08 共通ステータス / Exit Code

| Status | Exit Code | 意味 |
|---|---:|---|
| `OK` | 0 | 正常 |
| `WARNING` | 1 | 注意状態 |
| `CRITICAL` | 2 | 監視対象の異常 |
| `ERROR` | 3 | チェック処理自体の失敗 |

複数結果を集約する場合、優先度は以下とする。

```text
OK < WARNING < CRITICAL < ERROR
```

### 5.9 FR-09 テスト / CI

1. pytest により各監視処理、通知処理、CLI 統合処理を自動テストできること。
2. 現行実装では合計 42 テストを持つこと。
3. 外部 HTTP / Discord / Docker 等のテストでは Mock を利用し、テスト時に実サービスへ依存しない構成とすること。
4. GitHub Actions は `main` への push および `main` 向け pull request をトリガーとすること。
5. CI は `ubuntu-latest`、Python `3.12` で実行すること。
6. CI で `python -m pip install -e ".[dev]"` を実行後、`pytest -v` を実行すること。

---

## 6. 非機能要件・制約

### 6.1 実行環境

| 項目 | 要件 / 制約 |
|---|---|
| Python | 3.12 以上 |
| CLI Framework | Typer |
| CLI 表示 | Rich |
| HTTP | HTTPX |
| Resource Metrics | psutil |
| Docker | Docker SDK for Python |
| TLS | Python 標準 `ssl` / `socket` |
| Test | pytest |

### 6.2 可搬性

- HTTP / TLS / Deployment Check は対象へネットワーク到達できる環境から実行する。
- Server Monitor は「コマンドを実行したマシン自身」を監視する。
- Docker Monitor は実行環境から Docker Engine へ接続できる必要がある。
- Log Monitor は実行環境から対象ログファイルを読み取れる必要がある。

### 6.3 セキュリティ

- Discord Webhook URL は環境変数で管理する。
- `.env` および `.env.*` は Git 管理対象外とする。
- `.env.example` は変数名のみを示し、実値を含めない。
- Runtime log (`logs/`, `*.log`) を Git 管理対象外とする。

### 6.4 運用性

- 人間が確認しやすい表形式・メッセージを Rich で表示する。
- スクリプト・CI/CD から利用可能な Exit Code を返す。
- 異常通知機構の障害が監視対象の異常判定を隠さないこと。

### 6.5 性能に関する現行値

本プロジェクトでは SLA や応答時間保証値は定義されていない。実装上の既定値として、HTTP / TLS / Discord 通信の Timeout は原則 `5.0` 秒、CPU 取得は `0.1` 秒間隔でサンプリングする。

---

## 7. 外部インターフェース

| 外部要素 | 用途 | 必須条件 |
|---|---|---|
| HTTP/HTTPS Endpoint | Health / API 確認 | 実行環境から到達可能 |
| Docker Engine | Container 監視 | Docker socket / daemon へ接続可能 |
| Local OS Metrics | CPU / Memory / Disk / Swap | psutil で取得可能 |
| TLS Server | 証明書期限確認 | TCP/TLS 接続可能 |
| Log File | ログ監視 | ファイル読取権限あり |
| Discord Webhook | 異常通知 | Webhook URL を環境変数に設定 |
| GitHub Actions | CI | GitHub Repository 上で workflow が有効 |

---

## 8. 受入条件

以下を満たす場合、現行バージョンの要件を満たすものとする。

- `vps-ops --help` で 7 コマンドが表示される。
- HTTP Health Check が期待 HTTP Status 一致 / 不一致 / 接続失敗を判定できる。
- Server Monitor が CPU / Memory / Disk / Swap を取得し閾値判定できる。
- Docker Monitor が稼働・停止・Health 状態を判定できる。
- TLS Monitor が証明書残日数を判定できる。
- Log Monitor が ERROR / WARNING を検出できる。
- Deployment Check が Health + 任意 API をまとめて判定できる。
- Discord 通知が送信でき、未設定・HTTP エラー・接続エラーも扱える。
- `OK=0 / WARNING=1 / CRITICAL=2 / ERROR=3` の Exit Code が返る。
- pytest 42 件が成功する。
- GitHub Actions 上で pytest が実行される。

---

## 9. 現行実装で確認済みの実運用ユースケース

README の実稼働エビデンスでは、以下の利用を想定・確認している。

- VPS 上で Server Monitor を実行し、VPS 自身のリソースを確認する。
- VPS 上で Docker Monitor を実行し、複数アプリケーションのコンテナを一括確認する。
- 公開 API の Health Endpoint を確認する。
- 認証必須 API について HTTP 401 を期待値として Deployment Check する。
- 意図的な期待値不一致を `CRITICAL` と判定し、Discord へ通知する。
