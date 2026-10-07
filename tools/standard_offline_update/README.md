# Standard オフライン更新専用配布物

本番のユーザー・モジュール・原本・案件CS・画像・Access抽出ファイル・プレースホルダ設定を保持して、WebUIとAPIだけを更新します。

- 更新元: `7ecf683-http80-20261001`
- 更新先: `4c4fe7b-routerfix-http80-20261007`
- 対象: Ubuntu 24.04 / amd64 / Docker Engine + Compose v2 / Python 3.11以上
- 接続先: `http://10.58.134.28/`、SSHユーザー: `cnw`
- 初回インストール用ではありません。Docker・PostgreSQLイメージ・Labは変更しません。

React Routerを7.14.1から7.18.4へ更新しています。2026-10-07の `npm audit --omit=dev` で本番用npm依存関係の警告は0件です。開発用を含む全体監査には8件が残り、システム全体のセキュリティ確認完了を意味しません。[検証記録](docs/standard_update_verification_routerfix_20261007.md) を参照してください。

基準コミット `4c4fe7b30bc7ec548fbba1e3e16fa2717d439bb3` にStandardの `package.json` と `package-lock.json` の修正を加えた配布物です。`RELEASE.json` と更新後の `.deploy-version` には未コミット差分があることを記録します。以前の `routerfix` が付かない更新配布物は使用しないでください。すでに以前の更新を適用済みの場合は今回の更新元と異なるため、手順の再確認が必要です。

手順は [更新手順書](docs/standard_server_offline_update_guide.md) と [復旧手順書](docs/standard_server_update_recovery_guide.md) を参照してください。

```bash
sha256sum -c SHA256SUMS
sudo bash update_standard.sh --check
sudo bash update_standard.sh
sudo bash verify_update.sh
```

更新時は利用を停止し、`UPDATE` と入力して実行します。`BACKUP_READY=` に表示されたバックアップ先を記録してください。

更新は `docker-compose.standard.update.yml` を追加して、版を固定したイメージを指定します。本番のCompose基本設定、環境変数、ソースディレクトリ、storage、logsは上書きしません。`payload/standard-source-*.tar.gz` は対応するソースの保管用です。稼働コードは新しいイメージに含まれます。本番で古いソースから `docker compose build` を行わないでください。

DB変更は類似度計算用 `algorithm_version` 列の追加と既定値の変更だけです。旧データはバージョン1として保持し、新APIが必要時に再計算します。復旧時は旧アプリ用にこの計算キャッシュだけを削除して再計算させます。業務データとユーザーの権限は変更しません。

バックアップにはDB・storage・設定・旧アプリイメージを含めます。パスワードハッシュや業務情報を含むため、管理者限定で保管してください。自動削除はしません。

`--check` は対象版・ポート・保存先・空き容量の概算を確認します。バックアップ先の書込み確認やDocker領域の実空き容量、利用者の操作停止、社内の変更承認は別途確認が必要です。既存の初回導入用 `verify_standard.sh` は使用しません。

`RELEASE.json` のイメージ識別情報には、Dockerの保存方式の違いに対応するためmanifest IDとconfig IDを記録しています。バックアップ・更新・復旧スクリプトは同時実行を拒否します。
