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

## standard frontend のビルド

```powershell
cd apps\standard\frontend
npm run build
```

## Docker 起動イメージ

standardのみ:

```powershell
docker compose -f docker-compose.yml -f docker-compose.standard.yml up -d
```

labのみ:

```powershell
docker compose -f docker-compose.yml -f docker-compose.lab.yml up -d
```

## ドキュメント

- [standard WebUI構築手順書](./docs/standard/SB1-04_WebUI構築手順書.md)
- [standard ビルド時・ビルド後の注意点](./docs/standard/SB1-04_ビルド時_ビルド後の注意点.md)
- [standard WebUI教材](./docs/standard/SB1-04_WebUI教材.md)
