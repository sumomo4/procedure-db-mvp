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
http://<server-ip>:3000/
```

APIとPostgreSQLは`127.0.0.1`だけに公開される。

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
standard-offline-bundle-<commit>/
├─ config/
│  └─ docker-compose.standard.server.yml
├─ debs/
│  ├─ *.deb
│  └─ SHA256SUMS
├─ payload/
│  ├─ procedure-db-mvp-standard-<commit>.tar.gz
│  └─ procedure-db-standard-images-<commit>.tar
├─ DEPLOY_SHA
├─ SHA256SUMS
├─ install_standard.sh
├─ verify_standard.sh
├─ uninstall_standard.sh
└─ README.md
```

`install_standard.sh`はAPT、Docker Hub、npm、PyPIからダウンロードしない。
