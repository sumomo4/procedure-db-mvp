# MVP Root

standard MVP と lab MVP を同一リポジトリ内に同居させるための構成です。

## 構成

```text
apps/standard/frontend  標準MVPのWebUI
apps/standard/backend   標準MVPのAPI
apps/standard/db        標準MVPのDB関連
apps/lab/frontend       個人拡張MVPのWebUI
apps/lab/backend        個人拡張MVPのAPI
apps/lab/db             個人拡張MVPのDB関連
infra/env               環境変数サンプル
storage                 生成物・入力ファイル保存領域
logs                    ログ保存領域
docs                    ドキュメント
```

## standard frontend の起動

```powershell
cd apps\standard\frontend
npm install
npm run dev
```

## standard backend の起動

```powershell
cd apps\standard\backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

疎通確認:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

## standard frontend のビルド

```powershell
cd apps\standard\frontend
npm run build
```

## Docker 起動イメージ

standardのみ:

```powershell
docker compose -f docker-compose.yml -f docker-compose.standard.yml up -d --build
```

labのみ:

```powershell
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d
```

## ドキュメント

- [standard WebUI構築手順書](./docs/standard/SB1-04_WebUI構築手順書.md)
- [standard ビルド時・ビルド後の注意点](./docs/standard/SB1-04_ビルド時_ビルド後の注意点.md)
- [standard WebUI教材](./docs/standard/SB1-04_WebUI教材.md)
- [standard API構成方針](./docs/standard/SB1-06_07_API構成方針.md)
- [standard API/DB構築手順書](./docs/standard/SB1-08_09_13_14_API_DB構築手順書.md)
- [standard API実装基盤](./docs/standard/SB1-15_API実装基盤.md)
- [Sprint 1 SB1-08/09/13/14 完了チェック](./docs/standard/Sprint1_SB1-08_09_13_14_完了チェック.md)
- [Sprint 1 レビュー資料](./docs/standard/Sprint1_レビュー資料.md)
