# SB1-15 API実装基盤

## 1. 目的

Sprint 2でモジュール、原本、承認状態のAPI実装へ進めるように、リソース別routerの雛形を作成する。

## 2. 対象バックログ

| SB-ID | 内容 | 判定 |
| --- | --- | --- |
| SB1-15 | 基本API実装の土台を反映する | 完了 |

## 3. 実装したrouter

| router | prefix | Sprint 2で載せる主なAPI |
| --- | --- | --- |
| `modules` | `/api/v1/modules` | モジュール一覧 / 検索、詳細、登録、更新 |
| `source-docs` | `/api/v1/source-docs` | 原本一覧 / 検索、詳細、作成、更新 |
| `statuses` | `/api/v1/statuses` | 承認状態一覧、対象別確認、状態変更 |

## 4. 雛形確認API

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/api/v1/modules/foundation` | モジュールrouterの実装予定確認 |
| `GET` | `/api/v1/source-docs/foundation` | 原本routerの実装予定確認 |
| `GET` | `/api/v1/statuses/foundation` | 承認状態routerの実装予定確認 |

## 5. 完了条件

- リソース別にrouterが分割されている
- `app.main` から各routerが読み込まれている
- Swagger UIでSprint 2向けの入口を確認できる
- pytestでrouter雛形の応答を確認できる

## 6. 確認コマンド

```powershell
cd apps\standard\backend
.\.venv\Scripts\python.exe -m pytest
```

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/modules/foundation
Invoke-RestMethod http://localhost:8000/api/v1/source-docs/foundation
Invoke-RestMethod http://localhost:8000/api/v1/statuses/foundation
```
