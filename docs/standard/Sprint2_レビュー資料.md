# Sprint 2 レビュー資料

## 1. Sprintゴールに対する結果

Sprint 2 の目的である「主要画面の実データ化」は、おおむね達成できた。

- モジュール / 原本 / 承認状態の最小項目整理を実施
- DBテーブル方針を整理し、初期化SQLとseedデータを追加
- モジュール / 原本 / 承認状態の一覧 / 詳細APIを実装
- WebUI を API 接続へ切り替え
- ローカル Docker とテストサーバーで疎通確認
- Sprint 3 に向けた Excel 取込前提を整理

## 2. 完了項目

| 項目 | 状態 | 主な成果物 |
| --- | --- | --- |
| SB2-01〜SB2-05 | 完了 | `Downloads` 配下の整理資料、`docs/standard` 既存資料 |
| SB2-06 | 完了 | `apps/standard/db/init/001_standard_schema.sql` |
| SB2-07 / SB2-08 | 完了 | `/api/v1/modules`、`/api/v1/modules/{module_id}` |
| SB2-09 / SB2-10 | 完了 | `/api/v1/source-docs`、`/api/v1/source-docs/{source_doc_id}` |
| SB2-11 / SB2-12 | 完了 | `/api/v1/statuses`、`/api/v1/statuses/{target_id}` |
| SB2-13 | 完了 | `apps/standard/backend/tests` |
| SB2-14 / SB2-15 / SB2-16 | 完了 | `apps/standard/frontend/src/App.tsx` |
| SB2-17 | 完了 | `.github/workflows/build.yml` |
| SB2-18 | 完了 | テストサーバー `192.168.10.5` 反映結果 |

## 3. 画面確認ポイント

テストサーバー確認先:

- `http://192.168.10.5/modules/list`
- `http://192.168.10.5/modules/1`
- `http://192.168.10.5/documents/search`
- `http://192.168.10.5/documents/1`
- `http://192.168.10.5/approval`

API確認先:

- `http://192.168.10.5/api/v1/modules`
- `http://192.168.10.5/api/v1/modules/1`
- `http://192.168.10.5/api/v1/source-docs`
- `http://192.168.10.5/api/v1/source-docs/1`
- `http://192.168.10.5/api/v1/statuses`
- `http://192.168.10.5/api/v1/statuses/1`

## 4. DB / API の要点

### DB

主要テーブル:

- `proc.modules`
- `proc.module_versions`
- `proc.module_rows`
- `proc.blueprints`
- `proc.blueprint_versions`
- `proc.blueprint_items`

補足:

- `module_rows` は Excel 風表示を意識した列を保持
- `indent_level` を追加し、Excel の E/F/G/H 列配置に基づく段差を保持
- 今は「業務データ中心」で保持し、罫線やセル結合などの Excel 書式情報は持たない

### API

共通レスポンス形式:

- `result`
- `data`
- `message`

実装済み一覧 / 詳細 API:

- modules
- source-docs
- statuses

## 5. テスト / CI / デプロイ

ローカル確認:

- backend `pytest`: 41 passed
- frontend `npm run build`: 成功
- Docker で API / WebUI 疎通確認済み

CI:

- frontend build
- backend pytest
- deploy script 構文チェック
  - `bash -n infra/ubuntu/setup_standard_server.sh`
  - `bash -n infra/ubuntu/finish_standard_server.sh`

テストサーバー:

- Ubuntu LTS 24.04
- Nginx + systemd + PostgreSQL の直載せ構成
- `finish_standard_server.sh` で再反映可能

## 6. 既知課題 / 後回し事項

- Excel の見た目完全再現は未対応
- 大 / 中 / 小 の採番ルール確定は後回し
- 登録 / 更新 API は未着手
- Excel 出力は未着手
- Access 連携は未着手
- 認証 / 権限管理は暫定

## 7. Sprint 3 へ渡す前提

- モジュール / 原本 / 承認状態の閲覧系は一通り成立
- テストサーバーで関係者確認できる
- 次は登録 / 更新 / Excel入出力 / Access連携へ進める状態
