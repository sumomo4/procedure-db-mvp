# Standardオフライン配布物

## 対象

- Ubuntu Server 24.04 LTS
- `amd64` / `x86_64`
- Docker未導入の新規サーバー
- IPアドレス、ホスト名、SSHユーザー、sudo権限が設定済み

## 導入

配布物を展開したディレクトリで実行する。

```bash
sha256sum -c SHA256SUMS
sudo bash install_standard.sh
sudo bash verify_standard.sh
```

導入後はSSHへ再接続すると、対象ユーザーが`sudo`なしでDockerを操作できる。

WebUI:

```text
http://<server-ip>/
```

APIとPostgreSQLは`127.0.0.1`だけに公開される。

今回の導入はHTTP・80番で行う。証明書が未発行でも起動でき、HTTPS追加設定は自動適用しない。ローカル開発用の3000番とLabの3100番は変更しない。

HTTP通信は暗号化されないため、承認された社内ネットワークでの暫定利用に限定する。証明書の確認後にHTTPSへ切り替える。

初期モジュール・原本は0件で、seedデータや既存ユーザー・実行データは含まない。初回はログイン画面の新規ユーザー登録を利用する。自己登録のロールはmemberであるため、管理者権限が必要な場合は別途管理者の初期設定を行う。

Access抽出Excel、利用者が変更したプレースホルダ設定、DBバックアップ、秘密鍵は本配布物に含めない。必要なファイルは承認された経路で別途配置する。

同梱の`DEPLOY_MANIFEST.json`には、ベースコミット、未コミット変更の有無、ソースのSHA-256とDockerイメージIDを記録する。未コミット変更を含む配布物は、コミット済みの版と区別できる名前を付ける。

本スクリプトは新規導入用であり、導入先ディレクトリが存在する場合は停止する。既存サーバーのデータを削除したり、再インストールしたりしない。

## 本番HTTPS

本番サーバーは`https://10.58.143.28/`で接続する構成を用意している。443番でHTTPSを受け付け、80番からHTTPSへ転送する。

管理部門での証明書発行方法の確認後、SANに`iPAddress:10.58.143.28`を含む証明書をサーバーへ配置し、HTTPS追加設定を適用する。

- 設定: `config/docker-compose.standard.https.yml`、`config/nginx.standard.https.conf`
- 手順: [Standard本番サーバー HTTPS設定手順書](../../docs/standard/standard_server_https_setup_guide.md)

`install_standard.sh`と`verify_standard.sh`はHTTP・80番の基本導入用である。HTTPS設定の追加と切替後の検証は上記手順書に従う。配布物直下にも`docs/standard_server_https_setup_guide.md`を同梱する。

## 停止

データを残してコンテナだけ削除する。

```bash
sudo bash uninstall_standard.sh
```

## 完全撤去

次のコマンドはDBを含むStandardデータを削除する。

```bash
sudo bash uninstall_standard.sh --purge-data --remove-docker
```

## 配布物の内容

```text
standard-offline-bundle-<version>/
├─ config/
│  ├─ docker-compose.standard.server.yml
│  ├─ docker-compose.standard.https.yml
│  └─ nginx.standard.https.conf
├─ debs/
│  ├─ *.deb
│  └─ SHA256SUMS
├─ docs/
│  ├─ standard_docker_cli_server_offline_hands_on_guide.md
│  └─ standard_server_https_setup_guide.md
├─ payload/
│  ├─ procedure-db-mvp-standard-<commit>.tar.gz
│  └─ procedure-db-standard-images-<commit>.tar
├─ DEPLOY_SHA
├─ DEPLOY_MANIFEST.json
├─ SHA256SUMS
├─ install_standard.sh
├─ verify_standard.sh
├─ uninstall_standard.sh
└─ README.md
```

`install_standard.sh`はAPT、Docker Hub、npm、PyPIからダウンロードしない。
