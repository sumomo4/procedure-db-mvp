# Sprint 1 レビュー資料

## 1. Sprint 1 ゴール

WebUI + API + DB の基本構成を成立させ、Sprint 2以降の主要機能実装に進める状態にする。

## 2. 完了状況

| 領域 | 成果 | 状態 |
| --- | --- | --- |
| WebUI | React + Vite + React Routerで主要画面と導線を作成 | 完了 |
| API | FastAPI基本構成、共通レスポンス、エラー処理、CORSを作成 | 完了 |
| DB | PostgreSQL接続設定、初期化SQL、DB疎通確認APIを作成 | 完了 |
| 連携 | WebUI HOMEからAPI/DB疎通状態を表示 | 完了 |
| Sprint 2準備 | `modules`, `source-docs`, `statuses` router雛形を作成 | 完了 |
| CI | frontend build、backend pytestをGitHub Actionsに追加 | 完了 |

## 3. 動作確認結果

| 確認項目 | 結果 |
| --- | --- |
| `npm run build` | OK |
| `python -m pytest` | OK |
| `docker compose ... config --quiet` | OK |
| `GET /api/v1/health` | OK |
| `GET /api/v1/health/db` | OK |
| `GET /api/v1/modules/foundation` | OK |
| `GET /api/v1/source-docs/foundation` | OK |
| `GET /api/v1/statuses/foundation` | OK |
| `http://localhost:3000/` | OK |

## 4. 主要URL

```text
WebUI: http://localhost:3000/
API Docs: http://localhost:8000/docs
API health: http://localhost:8000/api/v1/health
DB health: http://localhost:8000/api/v1/health/db
```

## 5. Sprint 2 着手条件

| 条件 | 状態 |
| --- | --- |
| モジュール系APIのrouter入口がある | OK |
| 原本系APIのrouter入口がある | OK |
| 承認状態系APIのrouter入口がある | OK |
| WebUIからAPI疎通を確認できる | OK |
| DB接続確認がDocker環境で通る | OK |

## 6. 未決事項 / Sprint 2で決めること

- モジュール登録時の入力項目とDBテーブル定義
- 原本作成 / 更新時のモジュール組み合わせデータ構造
- Draft / approval / archive の状態遷移制約
- 画面モックデータをAPI接続へ切り替える順序
- Access連携やExcel出力をSprint 2対象に含めるかどうか

## 7. レビュー結論

Sprint 1の目的である基本構成は成立した。Sprint 2では、router雛形をもとにモジュール登録・検索、原本参照、承認状態確認の実APIとDBテーブルを具体化する。
