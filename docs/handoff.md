# MVP開発 引き継ぎメモ

## 1. GitHubリポジトリ

```text
https://github.com/sumomo4/procedure-db-mvp
```

- owner: `sumomo4`
- visibility: `PRIVATE`
- default branch: `main`
- latest confirmed commit: `ddd9f4d Initialize standard and lab MVP structure`

## 2. ローカル作業場所

現在のPCでは、以下に作業フォルダを作成している。

```text
C:\Users\clove\OneDrive\ドキュメント\mvp-root
```

他PCでは、以下で取得する。

```powershell
git clone https://github.com/sumomo4/procedure-db-mvp.git
cd procedure-db-mvp
```

## 3. 現在の全体方針

standard MVP と lab MVP を同一リポジトリ内に同居させる。

ただし、論理的には別システムとして扱う。

- `standard`: チーム向け、安定優先、正式運用に近いMVP
- `lab`: 個人拡張、検証優先、新機能試作用MVP

Docker利用も想定し、Web / API / DB / storage / logs / env を分離しやすい構成にしている。

## 4. 現在のフォルダ構成

```text
mvp-root/
├─ .github/
│  └─ workflows/
│     └─ build.yml
├─ apps/
│  ├─ standard/
│  │  ├─ frontend/
│  │  ├─ backend/
│  │  └─ db/
│  └─ lab/
│     ├─ frontend/
│     ├─ backend/
│     └─ db/
├─ docs/
│  ├─ standard/
│  ├─ lab/
│  └─ handoff.md
├─ infra/
│  └─ env/
├─ storage/
│  ├─ standard/
│  └─ lab/
├─ logs/
│  ├─ standard/
│  └─ lab/
├─ docker-compose.yml
├─ docker-compose.standard.yml
├─ docker-compose.lab.yml
├─ .gitignore
└─ README.md
```

## 5. standard frontend の状態

`test_UI` で作成したReact WebUIは、以下へ移動済み。

```text
apps/standard/frontend
```

主な技術:

- React
- Vite
- TypeScript
- React Router
- npm

実装済み画面:

- ログイン画面
- HOME画面
- モジュール検索画面
- モジュール一覧画面
- モジュール登録画面
- 原本参照画面
- 原本作成 / 更新画面
- 原本詳細画面
- 承認状態確認 / 変更画面

実装済みUI:

- サイドバー
- 現在の導線表示
- ログアウトボタン
- ログアウト確認モーダル
- ログアウト後はログイン画面へ戻る

## 6. standard frontend の確認方法

他PCで確認する場合:

```powershell
cd apps\standard\frontend
npm ci
npm run build
npm run dev
```

開発サーバのURL:

```text
http://127.0.0.1:5173/
```

ビルドは以下で確認済み。

```powershell
npm ci
npm run build
```

## 7. Docker関連の現在状態

Dockerを見据えて、以下を作成済み。

```text
docker-compose.yml
docker-compose.standard.yml
docker-compose.lab.yml
apps/standard/frontend/Dockerfile
infra/env/standard.env.example
infra/env/lab.env.example
```

standard frontend のDockerfileは、Nodeでビルドし、Nginxで `dist` を配信する構成。

standard / lab のDBは別コンテナ想定。

- standard DB: `mvp_standard`
- lab DB: `mvp_lab`

想定ポート:

```text
standard-web: http://localhost:3000
standard-api: http://localhost:8000
standard-db:  localhost:5432

lab-web:      http://localhost:3100
lab-api:      http://localhost:8100
lab-db:       localhost:5433
```

## 8. ドキュメント

standard関連資料は以下に移動済み。

```text
docs/standard/SB1-04_WebUI構築手順書.md
docs/standard/SB1-04_ビルド時_ビルド後の注意点.md
docs/standard/SB1-04_WebUI教材.md
```

内容:

- WebUI構築手順
- ビルド時・ビルド後の注意点
- 権限周りの注意点
- React/Vite/Router教材
- 先生向け補足

なお、教材から演習問題は削除済み。

## 9. Git状態

初回コミット済み。

```text
ddd9f4d Initialize standard and lab MVP structure
```

ローカル `main` は `origin/main` を追跡済み。

```text
main...origin/main
```

GitHub private repository へのpushも確認済み。

## 10. 注意点

### Node.js / npm

Node.jsインストール直後はPowerShellにPATHが反映されない場合がある。

その場合:

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
```

またはPowerShellを開き直す。

### npm install / npm ci

環境によっては npm cache 書き込みで `EPERM` が出る場合がある。

```text
C:\Users\clove\AppData\Local\npm-cache
```

### Vite / esbuild

`npm run build` や `npm run dev` で以下が出る場合がある。

```text
Error: spawn EPERM
```

その場合は、権限のあるPowerShellで再実行する。

### OneDrive配下

OneDrive配下では、同期やファイルロックにより `node_modules` や `dist` の作成・削除で失敗する可能性がある。

## 11. 次にやる候補

次回の候補:

1. GitHub Actions の build 成功確認
2. standard frontend のフォルダ分割
3. standard backend の FastAPI 雛形作成
4. PostgreSQL / SQLAlchemy / Alembic の初期構成
5. Docker Compose で standard-web / standard-db 起動確認
6. lab 側の初期構成作成
7. Access連携・Excel生成処理の責務分離設計

## 12. 次回Codexへ伝える一言

他PCで再開する場合は、以下のように伝えるとよい。

```text
GitHubの sumomo4/procedure-db-mvp をclone済みです。
docs/handoff.md の内容を前提に、続きからお願いします。
まずは GitHub Actions の build 確認から進めたいです。
```
