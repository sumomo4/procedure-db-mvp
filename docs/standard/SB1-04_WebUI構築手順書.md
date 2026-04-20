# SB1-04 WebUI構築手順書

## 1. 目的

Sprint 1 のバックログ SB1-04 として、React + Vite + TypeScript + React Router を用いた WebUI の基本構成を作成し、ビルド確認まで実施する。

## 2. 前提

- 対象OS: Windows
- 作業フォルダ: `c:\Users\clove\OneDrive\デスクトップ\test_UI`
- フロントエンド: React + Vite + TypeScript + React Router
- パッケージ管理: npm
- CI: GitHub Actionsで build 確認

## 3. 作成した主なファイル

| ファイル | 内容 |
| --- | --- |
| `package.json` | npm scripts、依存関係定義 |
| `index.html` | ViteのHTMLエントリ |
| `vite.config.ts` | Vite + React設定 |
| `tsconfig.json` | TypeScript設定の親ファイル |
| `tsconfig.app.json` | アプリケーション用TypeScript設定 |
| `tsconfig.node.json` | Vite設定用TypeScript設定 |
| `src/main.tsx` | Reactアプリのエントリ |
| `src/App.tsx` | 画面遷移、主要画面、モックデータ |
| `src/styles.css` | 画面スタイル |
| `.github/workflows/build.yml` | GitHub Actionsのbuild確認 |
| `README.md` | 実行方法の概要 |

## 4. 実装した画面

画面遷移図と画面方針整理をもとに、以下の画面を作成した。

| 画面 | 概要 |
| --- | --- |
| ログイン画面 | ユーザ名、パスワード入力後にHOMEへ遷移 |
| HOME画面 | 主要メニューと遷移サマリーを表示 |
| モジュール検索画面 | 検索条件入力、検索実行 |
| モジュール一覧画面 | モジュール検索結果の一覧表示 |
| モジュール登録画面 | ExcelファイルDnD想定の登録画面 |
| 原本参照画面 | 原本検索と一覧確認 |
| 原本作成 / 更新画面 | モジュール組み合わせと原本入力 |
| 原本詳細画面 | 原本の内容、版数、状態、関連情報を確認 |
| 承認状態確認 / 変更画面 | Draft、approval、archiveの状態確認 |

## 5. Node.jsのインストール

### 5.1 Node.js / npm の存在確認

PowerShellで以下を実行する。

```powershell
node --version
npm --version
```

今回の作業開始時点では、以下のように `node` / `npm` が見つからない状態だった。

```text
node : 用語 'node' は、コマンドレット、関数、スクリプト ファイル、または操作可能なプログラムの名前として認識されません。
npm : 用語 'npm' は、コマンドレット、関数、スクリプト ファイル、または操作可能なプログラムの名前として認識されません。
```

### 5.2 winget の確認

```powershell
Get-Command winget -ErrorAction SilentlyContinue
```

`winget.exe` が見つかったため、wingetでNode.js LTSをインストールした。

### 5.3 Node.js LTS のインストール

```powershell
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
```

今回インストールされたバージョンは以下。

```text
Node.js: v24.14.1
npm: 11.11.0
```

## 6. PATH反映前の確認方法

Node.jsインストール直後は、開いているPowerShellにPATHが反映されない場合がある。

その場合は、新しいPowerShellを開き直すか、以下のようにインストール先を直接指定して確認する。

```powershell
& 'C:\Program Files\nodejs\node.exe' --version
& 'C:\Program Files\nodejs\npm.cmd' --version
```

また、現在のPowerShellセッションだけPATHを追加する場合は以下を実行する。

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
```

## 7. 依存関係のインストール

作業フォルダへ移動する。

```powershell
cd 'c:\Users\clove\OneDrive\デスクトップ\test_UI'
```

依存関係をインストールする。

```powershell
npm install
```

PATHがまだ反映されていない場合は、以下のように実行する。

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' install
```

今回の実行結果は以下。

```text
added 73 packages, and audited 74 packages
found 0 vulnerabilities
```

## 8. ビルド確認

以下を実行する。

```powershell
npm run build
```

PATHがまだ反映されていない場合は、以下のように実行する。

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' run build
```

今回のビルド結果は以下。

```text
> procedure-db-webui@0.1.0 build
> tsc -b && vite build

vite v7.3.2 building client environment for production...
✓ 41 modules transformed.
dist/index.html
dist/assets/index-7oH06UV7.css
dist/assets/index-9g-sEM49.js
✓ built in 1.31s
```

## 9. 開発サーバの起動

以下を実行する。

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

PATHがまだ反映されていない場合は、以下のように実行する。

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
& 'C:\Program Files\nodejs\npm.cmd' run dev -- --host 127.0.0.1 --port 5173
```

起動後、以下のURLをブラウザで開く。

```text
http://127.0.0.1:5173/
```

今回の起動結果は以下。

```text
VITE v7.3.2 ready in 434 ms
Local: http://127.0.0.1:5173/
```

HTTP応答確認では `200 OK` を確認した。

## 10. 今回発生したエラーと対処

### 10.1 Node.jsインストール直後に node / npm が見つからない

原因:

- 既に開いているPowerShellにPATHが反映されていないため。

対処:

- PowerShellを開き直す。
- または、以下を実行して一時的にPATHを追加する。

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
```

### 10.2 npm install で npm-cache 作成に失敗する

エラー例:

```text
npm error code EPERM
npm error syscall mkdir
npm error path C:\Users\clove\AppData\Local\npm-cache
```

原因:

- npmキャッシュ作成先への書き込み権限、または実行環境の制限によるもの。

対処:

- 権限のあるPowerShellで再実行する。
- 今回は権限付きで `npm install` を再実行して解消した。

### 10.3 esbuild の子プロセス起動で EPERM になる

エラー例:

```text
Error: spawn EPERM
```

発生箇所:

- `npm run build`
- `npm run dev`

原因:

- Viteが内部で使用する esbuild の子プロセス起動が実行環境の制限により拒否されたため。

対処:

- 権限付きで `npm run build` を再実行する。
- 開発サーバも同様に、権限付きで `npm run dev` を実行する。

## 11. GitHub Actions

`.github/workflows/build.yml` に、build確認用のワークフローを作成した。

内容:

```yaml
name: build

on:
  push:
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 22

      - name: Install dependencies
        run: npm install

      - name: Build
        run: npm run build
```

## 12. 完了条件

以下を確認できれば、SB1-04のWebUI基本構成として完了とする。

- `npm install` が成功すること
- `npm run build` が成功すること
- `dist/` 配下にビルド成果物が生成されること
- `npm run dev` で開発サーバが起動すること
- `http://127.0.0.1:5173/` で画面を表示できること
- ログイン画面から主要画面へ遷移できること

## 13. 次の作業候補

1. 画面項目と文言をSprint 1レビュー向けに調整する
2. FastAPIの疎通確認APIを作成する
3. WebUIから `fetch` で疎通確認APIを呼び出す
4. モジュール検索、登録、原本参照のAPI接続方針を整理する
