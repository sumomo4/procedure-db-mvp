# 手順書DB standard API

Sprint 1 / SB1-08, SB1-09, SB1-13, SB1-14 向けの FastAPI 構成です。

## 主なエンドポイント

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | API疎通確認 |
| `GET` | `/api/v1/health/db` | PostgreSQL接続確認 |

## ローカル起動

```powershell
cd apps\standard\backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

疎通確認:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Docker Composeで起動している場合は、Windows側のポート予約状況によって `127.0.0.1` より `localhost` のほうが安定する場合があります。

## テスト

```powershell
cd apps\standard\backend
python -m pytest
```

DB接続確認APIは `psycopg` で `SELECT 1` を実行します。Docker Compose 起動時は `infra/env/standard.env.example` の値を利用します。
