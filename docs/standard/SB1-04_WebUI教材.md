# SB1-04 WebUI教材

## 1. この教材のゴール

この教材では、今回作成したWebUIを題材にして、以下を学びます。

- React + Vite + TypeScript の基本的な役割
- React Router による画面遷移
- HTML/CSSの知識がReactでどう使われるか
- JavaScriptの状態管理の考え方
- ログアウト確認モーダルの作り方
- `npm install`、`npm run dev`、`npm run build` の意味

対象は、HTML/CSSを少し知っていて、JavaScriptはクラスまで粗く理解している人です。  
同期/非同期処理はまだ前提にしません。

## 2. 今回作ったもの

今回作ったのは、手順書DBプロジェクトのM1向けWebUIです。

画面としては、以下を用意しました。

| 画面 | 役割 |
| --- | --- |
| ログイン画面 | ユーザーが最初に入る画面 |
| HOME画面 | 主要メニューを選ぶ画面 |
| モジュール検索画面 | 登録済みモジュールを探す画面 |
| モジュール一覧画面 | 検索結果を見る画面 |
| モジュール登録画面 | Excelファイルを登録する想定の画面 |
| 原本参照画面 | 原本を検索・参照する画面 |
| 原本作成 / 更新画面 | 原本を作成・更新する画面 |
| 原本詳細画面 | 原本の詳細を見る画面 |
| 承認状態確認画面 | Draft、承認待ち、保管済みを確認する画面 |

最後に、サイドバーへログアウトボタンを追加し、押したときに確認モーダルを表示するようにしました。

## 3. 使った技術

今回の技術スタックは以下です。

| 技術 | 役割 |
| --- | --- |
| HTML | Webページの土台 |
| CSS | 見た目の調整 |
| JavaScript | 画面の動き |
| TypeScript | JavaScriptに型を追加したもの |
| React | 画面を部品として作るライブラリ |
| React Router | Reactで画面遷移を扱うライブラリ |
| Vite | 開発サーバ、ビルドを担当するツール |
| npm | ライブラリを管理するツール |

## 4. ReactをHTMLの延長で考える

HTMLでは、例えばボタンを次のように書きます。

```html
<button>ログアウト</button>
```

Reactでも見た目はかなり似ています。

```tsx
<button type="button">ログアウト</button>
```

違いは、ReactではこのようなHTMLに似た記法を、JavaScriptの中に書くことです。  
この記法をJSXと呼びます。

TypeScriptを使う場合、拡張子は `.tsx` になります。

## 5. コンポーネントとは

Reactでは、画面を小さな部品に分けて作ります。  
この部品をコンポーネントと呼びます。

今回の例では、以下のようなコンポーネントがあります。

```tsx
function HomePage() {
  return (
    <Page title="HOME" description="画面遷移図の入口として、主要メニューと現在の作業状況を確認します。">
      <section className="dashboard-grid">
        ...
      </section>
    </Page>
  );
}
```

これは、`HomePage` という名前の画面部品です。

ポイント:

- `function HomePage()` はJavaScriptの関数
- `return (...)` の中に画面の見た目を書く
- HTMLに似ているが、実際にはReactのJSX
- `class` ではなく `className` を使う

HTMLでは以下のように書きます。

```html
<section class="dashboard-grid">
```

Reactでは以下のように書きます。

```tsx
<section className="dashboard-grid">
```

これは、JavaScriptでは `class` が予約語として使われるためです。

## 6. ファイル構成

今回の主なファイルは以下です。

```text
test_UI/
  index.html
  package.json
  vite.config.ts
  tsconfig.json
  src/
    main.tsx
    App.tsx
    styles.css
```

### 6.1 index.html

Reactアプリを差し込むためのHTMLです。

```html
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

`id="root"` の場所に、Reactの画面が表示されます。

### 6.2 src/main.tsx

Reactアプリを起動する入口です。

```tsx
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
```

ここでは、HTMLの `root` に対して、`App` コンポーネントを表示しています。

### 6.3 src/App.tsx

画面遷移と各画面の中身を書いている中心ファイルです。

今回の作業では、主にこのファイルを編集しました。

### 6.4 src/styles.css

画面の見た目を調整するCSSです。

Reactで作った部品にも、通常のCSSを使えます。

## 7. 画面遷移の考え方

通常のHTMLだけで画面遷移をする場合、別のHTMLファイルへ移動することが多いです。

例:

```html
<a href="home.html">HOMEへ</a>
```

Reactでは、1つのアプリの中で表示する画面を切り替えることができます。  
今回使っているのが React Router です。

```tsx
<Routes>
  <Route path="/" element={<LoginPage />} />
  <Route element={<Shell />}>
    <Route path="/home" element={<HomePage />} />
    <Route path="/modules/search" element={<ModuleSearchPage />} />
    <Route path="/approval" element={<ApprovalPage />} />
  </Route>
</Routes>
```

意味:

| 書き方 | 意味 |
| --- | --- |
| `path="/"` | ログイン画面 |
| `path="/home"` | HOME画面 |
| `element={<HomePage />}` | そのURLで表示するコンポーネント |

## 8. Shellとは

今回のアプリでは、ログイン後の画面に共通のサイドバーがあります。

その共通レイアウトを `Shell` というコンポーネントで作っています。

```tsx
function Shell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        ...
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
```

`aside` がサイドバー、`main` が画面のメイン部分です。

`Outlet` は、現在のURLに応じた画面を表示する場所です。  
たとえば `/home` なら `HomePage` が、`/approval` なら `ApprovalPage` がここに入ります。

## 9. ログアウトボタンの追加

サイドバーの「現在の導線」の下に、ログアウトボタンを追加しました。

```tsx
<div className="flow-box">
  <span>現在の導線</span>
  <strong>{routeTitle(location.pathname)}</strong>
</div>

<button
  className="logout-button"
  type="button"
  onClick={() => setIsLogoutDialogOpen(true)}
>
  <span aria-hidden="true">↩</span>
  ログアウト
</button>
```

ポイント:

- `button` はHTMLとほぼ同じ
- `className="logout-button"` でCSSを当てる
- `onClick` はクリックされたときの処理
- `setIsLogoutDialogOpen(true)` でモーダルを開く

## 10. 状態管理とは

ログアウト確認モーダルは、常に表示するわけではありません。

必要な状態は次の2つです。

| 状態 | 意味 |
| --- | --- |
| `false` | モーダルを表示しない |
| `true` | モーダルを表示する |

Reactでは、こうした画面の状態を `useState` で管理します。

```tsx
const [isLogoutDialogOpen, setIsLogoutDialogOpen] = useState(false);
```

意味:

| 名前 | 意味 |
| --- | --- |
| `isLogoutDialogOpen` | 今モーダルが開いているか |
| `setIsLogoutDialogOpen` | モーダルの開閉状態を変更する関数 |
| `useState(false)` | 最初は閉じている |

### 10.1 ボタンを押したとき

```tsx
onClick={() => setIsLogoutDialogOpen(true)}
```

これは、ボタンがクリックされたら `isLogoutDialogOpen` を `true` にするという意味です。

つまり、モーダルを表示します。

### 10.2 キャンセルしたとき

```tsx
onClick={() => setIsLogoutDialogOpen(false)}
```

これは、モーダルを閉じるという意味です。

## 11. モーダルの表示

モーダルは、以下の条件で表示しています。

```tsx
{isLogoutDialogOpen && (
  <div className="modal-backdrop" role="presentation">
    ...
  </div>
)}
```

これは少しJavaScriptらしい書き方です。

意味:

```text
isLogoutDialogOpen が true なら、右側のモーダルを表示する
isLogoutDialogOpen が false なら、何も表示しない
```

HTML/CSSだけでは、こうした状態による表示切り替えは少し面倒です。  
Reactでは、状態を変えることで画面が自動的に更新されます。

## 12. ログイン画面へ戻る処理

ログアウト確定ボタンでは、以下の処理をしています。

```tsx
onClick={() => {
  setIsLogoutDialogOpen(false);
  navigate("/");
}}
```

意味:

1. モーダルを閉じる
2. ログイン画面 `/` へ移動する

`navigate("/")` は、React Routerの画面遷移用の関数です。

```tsx
const navigate = useNavigate();
```

このように用意してから使います。

## 13. モーダルのHTML構造

今回のモーダルは、以下のような構造です。

```tsx
<div className="modal-backdrop" role="presentation">
  <section
    aria-labelledby="logout-dialog-title"
    aria-modal="true"
    className="modal-dialog"
    role="dialog"
  >
    <span className="modal-icon" aria-hidden="true">↩</span>
    <h2 id="logout-dialog-title">ログアウトしますか？</h2>
    <p>現在の画面を終了し、ログイン画面へ戻ります。</p>
    <div className="modal-actions">
      <button className="secondary" type="button">
        キャンセル
      </button>
      <button className="danger" type="button">
        ログアウト
      </button>
    </div>
  </section>
</div>
```

ポイント:

- `modal-backdrop` は画面全体の暗い背景
- `modal-dialog` は中央の白いダイアログ
- `role="dialog"` は支援技術向けに「これはダイアログです」と伝える指定
- `aria-modal="true"` は、今はモーダルが前面に出ていることを示す指定

## 14. モーダルのCSS

背景部分のCSSです。

```css
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  padding: 24px;
  display: grid;
  place-items: center;
  background: rgba(23, 32, 38, 0.56);
}
```

意味:

| CSS | 意味 |
| --- | --- |
| `position: fixed` | 画面に固定する |
| `inset: 0` | 上下左右を0にして画面全体を覆う |
| `z-index: 20` | 他の要素より前に出す |
| `display: grid` | 中央配置しやすくする |
| `place-items: center` | 中央に配置する |
| `background: rgba(...)` | 半透明の暗い背景 |

ダイアログ部分のCSSです。

```css
.modal-dialog {
  width: min(420px, 100%);
  border-radius: 8px;
  padding: 26px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
  display: grid;
  gap: 14px;
}
```

意味:

| CSS | 意味 |
| --- | --- |
| `width: min(420px, 100%)` | 最大420px、狭い画面では100% |
| `border-radius: 8px` | 角を少し丸める |
| `padding: 26px` | 内側の余白 |
| `background: #ffffff` | 白背景 |
| `box-shadow` | 浮いて見える影 |
| `gap: 14px` | 子要素の間隔 |

## 15. ボタンの見た目

ログアウトボタン用のCSSです。

```css
.logout-button {
  width: 100%;
  color: #172026;
  background: #d7a84f;
}

.logout-button:hover {
  background: #e5bd69;
}
```

危険操作用のボタンです。

```css
.danger {
  color: #ffffff;
  background: #b84d3a;
}

.danger:hover {
  background: #9f3f2f;
}
```

ログアウトはユーザーを画面外へ戻す操作なので、通常ボタンとは色を分けています。

## 16. ビルドとは

開発中のReactコードは、そのまま本番配布に向いた形ではありません。

ビルドとは、開発用のコードをブラウザで配布しやすい形に変換する作業です。

実行コマンド:

```powershell
npm run build
```

今回の `package.json` では、次のように定義されています。

```json
{
  "scripts": {
    "build": "tsc -b && vite build"
  }
}
```

意味:

| コマンド | 役割 |
| --- | --- |
| `tsc -b` | TypeScriptの型チェック |
| `vite build` | 本番用ファイルを作成 |

## 17. 開発サーバとは

開発中に画面を確認するためのサーバです。

実行コマンド:

```powershell
npm run dev
```

今回の確認URL:

```text
http://127.0.0.1:5173/
```

ブラウザでこのURLを開くと、作成したWebUIを確認できます。

## 18. 今回のビルド確認結果

ログアウト確認モーダルを追加した後、以下のコマンドでビルド確認しました。

```powershell
npm run build
```

結果:

```text
✓ 41 modules transformed.
✓ built in 1.85s
```

これは、TypeScriptのチェックとViteのビルドが通ったという意味です。

## 19. 同期/非同期について

今回の教材では、同期/非同期処理を深く扱っていません。

理由は、今回の画面はまだAPIと接続しておらず、モックデータで動いているためです。

今後、FastAPIなどのサーバーからデータを取得するようになると、以下のような処理が出てきます。

```tsx
fetch("/api/health")
```

このような通信処理では、同期/非同期の理解が必要になります。

今の段階では、次の理解で十分です。

```text
現在のUI:
画面の中にあるデータを表示している

今後のUI:
サーバーに問い合わせて、返ってきたデータを表示する
```

## 20. 今回学んだこと

今回の作業で学んだことを整理します。

- Reactでは画面をコンポーネントとして作る
- JSXはHTMLに似ているが、JavaScriptの中に書く
- `class` ではなく `className` を使う
- React Routerで画面遷移を管理できる
- `useState` で画面の状態を管理できる
- 状態が変わると、Reactが画面を更新してくれる
- モーダルは「表示する / 表示しない」という状態で制御できる
- CSSの知識はReactでもそのまま活かせる
- `npm run build` で本番用に変換できる
- ビルドが通っても、画面の見た目や操作感は別途確認する必要がある

## 21. 次に学ぶとよいこと

次に学ぶとよい内容は以下です。

1. Reactのprops
2. Reactのstate
3. 配列を使った一覧表示
4. フォーム入力の扱い
5. `fetch` を使ったAPI通信
6. 同期処理と非同期処理
7. エラー表示とローディング表示

特に、次工程でFastAPIと接続する場合は、`fetch` と非同期処理が重要になります。

## 22. 設計思想

ここでは、今回のWebUIをどのような考え方で作ったかを説明します。

プログラムは「動けばよい」だけでなく、あとから直しやすいこと、説明しやすいこと、チームで扱いやすいことも大切です。

### 22.1 1画面1目的を基本にする

今回の画面方針では、1つの画面に多くの役割を詰め込みすぎないようにしています。

例:

| 画面 | 主な目的 |
| --- | --- |
| モジュール検索画面 | 条件を入力して検索する |
| モジュール一覧画面 | 検索結果を確認する |
| モジュール登録画面 | 新しいモジュールを登録する |
| 原本詳細画面 | 原本の内容を確認する |
| 承認状態確認画面 | 状態を確認・変更する |

画面の目的を分けると、次のメリットがあります。

- 画面ごとの責任がわかりやすい
- どこを修正すればよいか探しやすい
- レビュー時に説明しやすい
- 将来APIを接続するときに処理を分けやすい

### 22.2 共通レイアウトをShellにまとめる

ログイン後の画面には、共通してサイドバーがあります。

もし各画面に毎回サイドバーを書いてしまうと、修正が大変になります。

悪い例:

```tsx
function HomePage() {
  return (
    <>
      <aside>サイドバー</aside>
      <main>HOME</main>
    </>
  );
}

function ApprovalPage() {
  return (
    <>
      <aside>サイドバー</aside>
      <main>承認状態</main>
    </>
  );
}
```

この書き方だと、サイドバーにログアウトボタンを追加するとき、すべての画面を直す必要があります。

今回の設計では、共通部分を `Shell` にまとめています。

```tsx
function Shell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        サイドバー
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
```

`Outlet` の場所だけが画面ごとに入れ替わります。

このため、ログアウトボタンを追加するときも、`Shell` を1か所直すだけで済みました。

### 22.3 まずはモックで画面遷移を確認する

今回の段階では、APIやDBにはまだ接続していません。

そのため、画面内に仮のデータを置いています。

```tsx
const modules: ModuleRow[] = [
  { id: "MOD-001", name: "初期点検手順", status: "Draft", version: "0.2" },
  ...
];
```

これをモックデータと呼びます。

モックデータを使う理由:

- APIが未完成でも画面を先に確認できる
- 画面遷移や表示レイアウトを早くレビューできる
- 必要な項目の過不足を発見しやすい
- 後からAPIに置き換える前提を作れる

今後APIと接続する場合は、モックデータの部分を `fetch` に置き換えていきます。

### 22.4 画面遷移図をルーティングに落とし込む

資料にあった画面遷移は、次のような形でした。

```text
ログイン画面
  ↓
HOME画面
  ├─ モジュール
  │   ├─ 検索
  │   │   └─ 一覧/詳細画面
  │   └─ 登録
  ├─ 原本
  │   ├─ 作成/更新
  │   └─ 検索
  └─ 承認状態確認
```

これをReact Routerでは、次のようなURLに対応させています。

| 画面 | URL |
| --- | --- |
| ログイン画面 | `/` |
| HOME画面 | `/home` |
| モジュール検索画面 | `/modules/search` |
| モジュール一覧画面 | `/modules/list` |
| モジュール登録画面 | `/modules/register` |
| 原本参照画面 | `/documents/search` |
| 原本作成 / 更新画面 | `/documents/create` |
| 原本詳細画面 | `/documents/:id` |
| 承認状態確認画面 | `/approval` |

URLを見ただけで、どの機能の画面か想像しやすくしています。

### 22.5 HashRouterを選んだ理由

今回のアプリでは `HashRouter` を使っています。

```tsx
<HashRouter>
  <App />
</HashRouter>
```

`HashRouter` を使うと、URLは次のようになります。

```text
http://127.0.0.1:5173/#/home
```

`#/home` の部分をReactが見て、画面を切り替えます。

今回 `HashRouter` にした理由:

- 静的ファイルとして配布しやすい
- サーバー側のリライト設定が不要
- Sprint 1のWebUI確認では扱いやすい

将来的に本格的なWebアプリとして運用する場合は、`BrowserRouter` に変更する可能性があります。

### 22.6 CSSは画面全体の統一感を優先する

今回のCSSでは、次のことを意識しています。

- サイドバーは固定的なナビゲーションとして見せる
- メイン画面は白背景の領域を中心に見やすくする
- ステータスは色付きラベルで判別しやすくする
- 危険操作であるログアウトは赤系ボタンにする
- 画面が狭くなっても縦並びに変わるようにする

CSSは単に色を付けるだけではありません。  
利用者が迷わず操作できるように、情報の優先順位を見た目で伝える役割があります。

## 23. 構築方法

ここでは、今回のWebUIをゼロから作る場合の流れを説明します。

### 23.1 作業フォルダを用意する

PowerShellで作業フォルダへ移動します。

```powershell
cd 'c:\Users\clove\OneDrive\デスクトップ\test_UI'
```

### 23.2 Node.jsを確認する

```powershell
node --version
npm --version
```

Node.jsが見つからない場合は、以下でインストールします。

```powershell
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
```

インストール直後にPowerShellが認識しない場合は、PowerShellを開き直します。

または一時的にPATHを追加します。

```powershell
$env:Path = 'C:\Program Files\nodejs;' + $env:Path
```

### 23.3 package.jsonを用意する

`package.json` は、アプリの名前、依存ライブラリ、実行コマンドを書くファイルです。

今回の重要な部分:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.1.0",
    "react-dom": "^19.1.0",
    "react-router-dom": "^7.6.0"
  },
  "devDependencies": {
    "@types/react": "^19.1.0",
    "@types/react-dom": "^19.1.0",
    "@vitejs/plugin-react": "^5.0.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0"
  }
}
```

ここで大事なのは `scripts` です。

| script | 使い方 | 役割 |
| --- | --- | --- |
| `dev` | `npm run dev` | 開発サーバを起動する |
| `build` | `npm run build` | 本番用にビルドする |
| `preview` | `npm run preview` | ビルド成果物を確認する |

### 23.4 依存関係を入れる

```powershell
npm install
```

これにより、`node_modules/` が作られます。

`node_modules/` はライブラリ本体が入る場所です。  
とても大きくなるので、通常Gitには含めません。

### 23.5 TypeScriptとViteの設定を用意する

今回の主な設定ファイル:

```text
tsconfig.json
tsconfig.app.json
tsconfig.node.json
vite.config.ts
```

最初のうちは、これらを全部理解しようとしなくても大丈夫です。

まずは次の理解で十分です。

| ファイル | 役割 |
| --- | --- |
| `tsconfig.json` | TypeScript全体の設定入口 |
| `tsconfig.app.json` | Reactアプリ側のTypeScript設定 |
| `tsconfig.node.json` | Vite設定ファイル用のTypeScript設定 |
| `vite.config.ts` | ViteでReactを使うための設定 |

### 23.6 Reactの入口を作る

`index.html` にReactを差し込む場所を作ります。

```html
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

`src/main.tsx` でReactを起動します。

```tsx
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
```

### 23.7 App.tsxで画面を作る

`App.tsx` では主に次のことをしています。

- ルーティングを書く
- 共通レイアウトを書く
- 各画面を書く
- モックデータを書く
- ログアウトモーダルを書く

最初は1ファイルにまとめていますが、画面が増えてきたら分割します。

分割例:

```text
src/
  pages/
    HomePage.tsx
    ModuleSearchPage.tsx
    ApprovalPage.tsx
  components/
    Shell.tsx
    DataTable.tsx
    StatusPill.tsx
    LogoutDialog.tsx
```

### 23.8 CSSで見た目を整える

`src/styles.css` に画面全体のCSSを書いています。

最初に確認するとよいCSS:

| CSSクラス | 役割 |
| --- | --- |
| `.app-shell` | サイドバーとメイン画面の2カラム |
| `.sidebar` | 左側メニュー |
| `.content` | 右側の表示領域 |
| `.page-header` | 各画面の見出し |
| `.table-wrap` | 一覧表の表示 |
| `.modal-backdrop` | モーダル背景 |
| `.modal-dialog` | モーダル本体 |

### 23.9 開発サーバを起動する

```powershell
npm run dev
```

または、ポートを指定します。

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

ブラウザで開きます。

```text
http://127.0.0.1:5173/
```

### 23.10 ビルドする

```powershell
npm run build
```

成功すると `dist/` が作られます。

```text
dist/
  index.html
  assets/
    index-xxxxx.css
    index-xxxxx.js
```

この `dist/` が本番配布用の成果物です。

## 24. 先生向けの補足

この教材を教えるときは、最初からReactのすべてを説明しようとしない方が進めやすいです。

おすすめの順番:

1. まず画面を触ってもらう
2. HTMLに似ている部分を見つけてもらう
3. `className` とCSSの関係を見る
4. ボタンの `onClick` を見る
5. `useState` でモーダルが開閉することを見る
6. 最後にReact Routerの画面遷移を見る

同期/非同期は、この段階では軽く触れるだけで十分です。

FastAPI接続のタイミングで、次のように説明するとつながりやすくなります。

```text
今までは画面の中にあるデータを表示していた。
次はサーバーに問い合わせて、返ってきたデータを表示する。
その「返ってくるまで待つ」考え方が非同期処理。
```

### 24.1 授業の進行例

60分から90分程度の授業で扱う場合は、次の流れがおすすめです。

| 時間 | 内容 | ねらい |
| --- | --- | --- |
| 5分 | 完成画面を触る | これから作るものの全体像を掴む |
| 10分 | ファイル構成を見る | `index.html`、`main.tsx`、`App.tsx`、`styles.css` の役割を知る |
| 10分 | ReactとHTMLの違いを見る | JSX、`className`、コンポーネントを理解する |
| 10分 | 画面遷移を見る | React Router、`Routes`、`Route`、`navigate` を知る |
| 15分 | ログアウトモーダルを見る | `useState` による表示切り替えを理解する |
| 20分 | コードを読み解く | JSX、CSS、状態管理のつながりを確認する |
| 10分 | ビルド確認 | 作ったものが壊れていないか確認する習慣をつける |

時間が短い場合は、完成画面、`App.tsx`、`styles.css` の関係を見るだけでも十分です。  
時間が長い場合は、モーダル表示、画面遷移、ビルド確認まで順に追うと理解しやすくなります。

### 24.2 先生が最初に伝えるとよいこと

授業の最初に、次のように伝えると生徒が安心しやすいです。

```text
今日はReactを全部覚える日ではありません。
HTML/CSSで知っていることが、Reactではどう見えるかを確認する日です。
まずは、完成している画面とコードを見比べて、どのコードがどの画面に対応しているかを確認しましょう。
```

Reactは新しい用語が多いため、最初から完璧に説明しようとすると難しく感じやすいです。  
まずは「見たことがあるHTMLに似ている部分」を見つけてもらうのが入り口として有効です。

### 24.3 生徒がつまずきやすいポイント

| つまずき | 原因 | フォロー例 |
| --- | --- | --- |
| `class` と書いてしまう | HTMLの習慣が残っている | Reactでは `className` と書く、と繰り返し確認する |
| JSXのタグを閉じ忘れる | HTMLよりエラーが厳密に出る | エラー行の少し上を見るように伝える |
| `{}` の意味がわからない | JSX内でJavaScriptを書く経験が少ない | `{}` は「ここからJavaScript」と説明する |
| `useState` が難しい | 変数との違いがわかりにくい | 「画面を更新できる特別な変数」と説明する |
| `navigate("/")` がわからない | URLと画面の対応が未整理 | `/` はログイン画面、`/home` はHOME画面と表で確認する |
| `npm run build` が怖い | コマンド操作に慣れていない | まずは成功例のログを見せて、同じ表示を探してもらう |

### 24.4 説明に使えるたとえ

#### コンポーネント

```text
コンポーネントは、画面の部品です。
HTMLで毎回同じまとまりを書く代わりに、名前をつけて再利用できる部品にします。
```

#### useState

```text
useStateは、画面の状態を覚える箱です。
普通の変数と違って、中身を変えるとReactが画面を描き直してくれます。
```

#### React Router

```text
React Routerは、URLと表示する部品の対応表です。
/homeならHOME画面、/approvalなら承認状態画面、というように切り替えます。
```

#### ビルド

```text
ビルドは、開発者向けに書いたコードを、ブラウザで配りやすい形にまとめる作業です。
```

### 24.5 問いかけ例

授業中に使える問いかけです。

| 場面 | 問いかけ |
| --- | --- |
| 完成画面を見るとき | この画面で、HTMLの知識が使われていそうな場所はどこですか？ |
| サイドバーを見るとき | すべての画面に同じサイドバーを書くと、何が困りそうですか？ |
| ルーティングを見るとき | `/modules/search` というURLから、どんな画面だと想像できますか？ |
| `useState` を見るとき | モーダルが開いている状態は、true / false のどちらで表せそうですか？ |
| CSSを見るとき | ログアウトボタンを赤くすると、利用者にどんな印象を与えますか？ |
| ビルド後 | ビルド成功と画面の使いやすさは、同じ確認と言えるでしょうか？ |

### 24.6 理解度確認の観点

講義後は、単に画面を見たかどうかだけでなく、次の観点で確認します。

- `index.html`、`main.tsx`、`App.tsx` のつながりを説明できるか
- ReactのコードからHTMLに似た部分を見つけられるか
- `className` とCSSクラスの関係を説明できるか
- ログアウトボタンを押したとき、どの状態が変わるか説明できるか
- `navigate("/")` がログイン画面への遷移であることを説明できるか
- `npm run build` が何を確認するコマンドか説明できるか

生徒に聞くとよい質問:

```text
ログアウトモーダルは、どの変数が true のときに表示されますか？
CSS側でモーダルの背景を暗くしているクラスはどれですか？
HOME画面へ移動するURLはどれですか？
```

### 24.7 エラーが出たときの教え方

初心者はエラーが出ると「全部壊した」と感じやすいです。  
先生は、エラーを失敗ではなく、場所を教えてくれるヒントとして扱うとよいです。

伝え方の例:

```text
エラーは、ReactやTypeScriptが意地悪をしているのではなく、
どこを直せばよいか教えてくれているメッセージです。
まず一番上のエラーを見ましょう。
```

よく見る場所:

- エラーが出ているファイル名
- 行番号
- `Expected` や `Unexpected` の近く
- タグの閉じ忘れ
- `{}`、`()`, `[]` の閉じ忘れ

### 24.8 板書・説明用の簡易図

Reactの表示の流れ:

```text
index.html
  ↓
src/main.tsx
  ↓
App.tsx
  ↓
Routes
  ↓
各画面コンポーネント
```

ログアウトモーダルの流れ:

```text
ログアウトボタンを押す
  ↓
setIsLogoutDialogOpen(true)
  ↓
isLogoutDialogOpen が true
  ↓
モーダル表示
  ↓
キャンセル → false に戻す
ログアウト → false に戻す + navigate("/")
```

画面遷移の流れ:

```text
URLが変わる
  ↓
React Routerが対応するRouteを探す
  ↓
対応するコンポーネントを表示する
```

### 24.9 先生側のゴール設定

この教材の授業では、最終的に次の状態を目指します。

生徒ができるようになること:

- ReactのコードからHTMLに似た部分を見つけられる
- CSSクラスを探して見た目を変更できる
- ボタンのクリック処理を読める
- `useState` が表示切り替えに使われることを説明できる
- ルーティングのURLと画面の対応を説明できる
- `npm run build` がビルド確認のためのコマンドだと説明できる

まだできなくてもよいこと:

- TypeScriptの型を完全に理解すること
- React Hooksをすべて理解すること
- 非同期処理を自力で書けること
- Vite設定を一から書けること
- コンポーネント設計を最初から最適化すること

この段階では、Reactに対する苦手意識を減らし、既存コードを少し読んで、少し変えられるようになることが大切です。

