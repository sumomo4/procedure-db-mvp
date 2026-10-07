# Standard更新配布物 React Router修正版の検証記録

検証日: 2026-10-07

1～6節は配布物作成時点の検証記録です。作成後のGitコミットとの対応は7節に追記しています。

## 1. 対象

| 項目 | 内容 |
| --- | --- |
| 配布物 | `standard-update-4c4fe7b-routerfix-http80-20261007.tar.gz` |
| 更新元 | `7ecf683-http80-20261001` |
| 更新先 | `4c4fe7b-routerfix-http80-20261007` |
| 基準コミット | `4c4fe7b30bc7ec548fbba1e3e16fa2717d439bb3` |
| 追加差分 | Standardの `package.json` と `package-lock.json` |
| 対象サーバー | `10.58.134.28` / SSHユーザー `cnw` / HTTP80 |
| 検証環境 | ローカルDockerの隔離環境、Linux amd64、PostgreSQL 16 |

本番サーバーには接続・更新していません。稼働中のStandard/Lab開発用コンテナとデータも変更していません。

今回の配布物は基準コミットそのものではなく、依存関係修正を追加したものです。`RELEASE.json` の `source_overlays` と `source_has_uncommitted_changes: true` に記録しています。更新後の `.deploy-version` にも `SOURCE_HAS_UNCOMMITTED_CHANGES=true` を記録します。commit・pushは行っていません。

## 2. 依存関係修正

| 環境 | パッケージ | 更新前 | 更新後 |
| --- | --- | --- | --- |
| Standard | react-router-dom / react-router | 7.14.1 | 7.18.4 |
| Lab | react-router-dom / react-router | 7.14.1 | 7.18.4 |

- `package.json` の指定を `^7.18.4` とし、ロックファイルは7.18.4に固定しました。
- 他パッケージのバージョンや無関係なロックファイルのメタデータは変更していません。
- 業務画面のコード、CSS、API、認証方式の変更はありません。
- 配布物に含むのはStandardだけです。Labの修正は開発リポジトリへの反映です。
- WebUIはViteで生成した静的ファイルをNginxで配信する構成です。React RouterのSSRやunstable RSCは使用していません。ただし、適用範囲の異なる警告を放置せず、今回依存関係を更新しました。

## 3. npm監査

2026-10-07、最終ロックファイルに対して確認しました。

| 監査範囲 | Standard | Lab |
| --- | --- | --- |
| `npm audit --omit=dev` | 0件 | 0件 |
| 開発用を含む `npm audit` | 8件 | 8件 |
| 全体監査の内訳 | High 5 / Moderate 1 / Low 2 | High 5 / Moderate 1 / Low 2 |

残る開発用依存関係: `@babel/core`、`baseline-browser-mapping`、`browserslist`、`esbuild`、`nanoid`、`postcss`、`source-map-js`、`vite`。

本番WebイメージにはNode/npm開発サーバーを同梱せず、ビルド結果を配信します。ただし、ビルド環境や開発サーバーに対するリスクは残るため、次の依存関係保守で対応が必要です。開発サーバーを外部公開しないでください。今回の0件という結果は、OS・Nginx・Pythonやアプリケーション全体の安全性を保証するものではありません。

監査原本:

- [Standard 本番用](npm-audit-production-standard-routerfix.json)
- [Lab 本番用](npm-audit-production-lab-routerfix.json)
- [Standard 全体](npm-audit-all-standard-routerfix.json)
- [Lab 全体](npm-audit-all-lab-routerfix.json)

## 4. ビルド・テスト

| 確認項目 | 結果 |
| --- | --- |
| Standard TypeScript / Vite本番ビルド | 成功 |
| Lab TypeScript / Vite本番ビルド | 成功 |
| Standardバックエンド | 243件成功 |
| 更新ツール | 15件成功 |
| Standardブラウザ画面遷移 | PC・モバイルの2パターンで成功 |
| Labブラウザ画面遷移 | PC・モバイルの2パターンで成功 |
| 更新前Standardの比較用画面遷移 | PC・モバイルの2パターンで成功 |
| 各ブラウザ実行のJavaScript例外 | 0件 |
| HOMEのページ幅・コンテンツ幅 | 更新前と一致 |

ブラウザはPlaywright Core + Edgeのヘッドレス実行です。画面サイズは1440x1000、390x844です。スクリーンショットも確認しています。APIはテスト用応答に置き換えており、実データの登録や変更を行っていません。

各パターンで確認した12項目: 未ログイン時の誘導、新規ユーザー登録へのリンク、ログイン、旧モジュール一覧URLからの検索条件維持、検索条件変更と戻る・進む、直接URLの再読み込み、選択中メニュー、管理者画面、未知URL、パスワード変更必須時の誘導、memberのメニュー、ログアウト。

ビルド時の大きなJSチャンクに関する警告と、テスト時のStarlette/AnyIOの非推奨警告は残っています。今回はUIの全面的な評価や全業務フローのブラウザE2Eを行ったものではありません。

初回の検証実行で、テスト用ディレクトリ階層、ダイアログのARIAロール指定、ユーザー候補APIのモック不足を修正しました。アプリ本体の変更は行わず、再実行で上記の結果を確認しています。

## 5. オフライン更新・復旧の実機相当テスト

専用Composeプロジェクトと使い捨てDBボリュームに旧版を起動し、検証用ユーザー・管理者権限・モジュール・原本・案件CS・実行記録・storage内のファイルを作成して確認しました。本番のデータは使用していません。

1. 更新元の版・イメージ・ポート・マウント先を事前確認できる。
2. 想定外の更新元はアプリを停止する前に拒否する。
3. DB・storage・設定・旧アプリイメージをバックアップできる。
4. 持ち込みイメージによる更新が成功する。
5. DBコンテナとボリュームが同じままで、業務データ・設定・storageの内容が保持される。
6. 既存パスワードとadminロールでログインでき、ユーザー管理・モジュール取得APIが使える。
7. 類似度キャッシュの列追加、旧データの版1と新規の既定値3が正しい。
8. 配布物の未コミット差分が導入メタデータへ記録される。
9. 同じ更新の二重適用を拒否する。
10. `pg_dump` のバックアップを別の検証DBに実際に復元できる。
11. 更新後の業務入力を保持して旧アプリへ切り戻せる。再生成可能な類似度キャッシュだけを削除する。
12. 切り戻し後に同じ修正版を再適用できる。

最終イメージに対するこのシナリオは成功しました。試験用コンテナ・DBボリュームは試験後に削除しています。HTTPの疎通確認は含みますが、本番環境のネットワークや実データによるExcel出力の確認を代替するものではありません。

## 6. 配布物と適用時の注意

- 外側tar.gzのSHA-256は隣接する `.tar.gz.sha256`、展開後の全ファイルは `SHA256SUMS` で照合します。
- `RELEASE.json` に対応ソースとイメージアーカイブのSHA-256、Web/APIイメージのmanifest IDとconfig IDを記録しています。
- 対応ソースアーカイブのSHA-256: `da2dceb973f4a66981d96e43c268537a0ca02d50c744f06809f9f5fee2f2c98e`
- イメージアーカイブのSHA-256: `19356fde9feb6ea7af4d9f056875ce73339fd5b24f7091a787af30f02ffb9e90`
- 以前の `routerfix` が付かない配布物ではなく、今回の修正版を使用してください。旧配布物をすでに適用済みの場合は、本手順の更新元と異なるため再確認が必要です。
- 本番適用前に利用停止、社内の変更承認、空き容量を確認してください。
- 本番適用後は、既存アカウント・権限・画像・案件の再開位置・証跡Excelを利用者側で確認してください。
- 切り戻すとReact Routerも旧版に戻ります。恒久的な解決ではなく、障害時の暫定措置として扱ってください。
- この資料では本番適用済みとはしていません。

関連資料: [更新手順](standard_server_offline_update_guide.md)、[復旧手順](standard_server_update_recovery_guide.md)。

## 7. 配布物とGitコミットの対応

配布後に依存関係修正をGitへ記録しました。配布済みtar.gz、内部の `RELEASE.json`、チェックサム、本番の導入メタデータは書き換えません。

| 項目 | 値 |
| --- | --- |
| 対応ソースコミット | `a646ca963367d73b62ba49938c4213260eb32e56` |
| コミット内容 | Standard / LabのReact Routerを7.18.4へ更新 |
| 配布バージョン | `4c4fe7b-routerfix-http80-20261007` |
| 配布tar.gzのSHA-256 | `78642b74fccd1f912510d98131734dbb28ed5aa05580ccdc2ae3270ff2ee6b36` |

配布物に収録したStandardソースと上記コミットの同じ対象パスについて、ファイル構成と内容を照合しました。SHA-256が異なるフロントエンドのJSONファイルは、Windows側のGit出力との改行コード差（CRLF / LF）だけであり、改行を揃えた内容が一致することを確認しています。コードや依存関係の意味上の差分はありません。Labのソースや更新ツール・手順書は、このStandardソースアーカイブとは別の管理対象です。

配布ファイル名にある `4c4fe7b` と `SOURCE_HAS_UNCOMMITTED_CHANGES=true` は、配布物作成時点の正しい記録です。コミット後も変更する必要はありません。本番への再転送・再更新も、このGitへの記録だけを理由に行う必要はありません。

この追記はリポジトリ側の管理記録です。配布済みtar.gz内の検証記録は当時の内容を保持します。

## 参考

- [React Router: client-side redirect advisory](https://github.com/remix-run/react-router/security/advisories/GHSA-wrjc-x8rr-h8h6)
- [React Router: request handling advisory](https://github.com/remix-run/react-router/security/advisories/GHSA-chx6-hx7r-mcp5)
- [React Router: unstable RSC advisory](https://github.com/remix-run/react-router/security/advisories/GHSA-qwww-vcr4-c8h2)
- [React Router 7.18.2 release](https://github.com/remix-run/react-router/releases/tag/react-router%407.18.2)
