# Standardオフライン導入テスト実施手順書

## 1. 目的

事前に作成済みのオフライン配布物を使い、作業PCからテストサーバーへStandard環境を導入する。

この手順では、Docker用パッケージ、Dockerイメージ、アプリケーションソースをインターネットから取得しない。

## 2. 対象

### 2.1 テストサーバー

| 項目 | 値 |
| --- | --- |
| IPアドレス | `10.58.143.28` |
| SSHユーザー | `user` |
| OS | Ubuntu Server 24.04 LTS |
| CPUアーキテクチャ | `amd64` / `x86_64` |
| 初期状態 | IPアドレス、hostname、SSH、sudo設定済み |

SSHパスワードは手順書へ記載せず、別途安全な方法で管理する。

### 2.2 作業PC

- Windows PowerShellを使用できること
- `ssh`と`scp`を使用できること
- `10.58.143.28`のTCP 22番ポートへ接続できること

### 2.3 使用する配布物

作業PCのDownloadsフォルダに、次の2ファイルがあること。

```text
standard-offline-bundle-7bf0862.tar.gz
standard-offline-bundle-7bf0862.tar.gz.sha256
```

## 3. 導入前確認

### 3.1 作業PCからSSH疎通を確認する

PowerShellで実行する。

```powershell
Test-NetConnection 10.58.143.28 -Port 22
```

`TcpTestSucceeded : True`となることを確認する。

### 3.2 サーバーの初期状態を確認する

```powershell
ssh user@10.58.143.28
```

接続後、サーバーで実行する。

```bash
hostname
hostname -I
cat /etc/os-release
uname -m
command -v docker || echo "Dockerは未導入です"
ss -lnt | grep -E ':(3000|8000|5432)[[:space:]]' || echo "Standard用ポートは未使用です"
```

次を確認する。

- Ubuntu 24.04である
- `uname -m`が`x86_64`である
- Dockerが未導入である
- `3000`、`8000`、`5432`番ポートが未使用である

確認後、いったんSSHから退出する。

```bash
exit
```

## 4. 作業PC上の配布物確認

PowerShellで実行する。

```powershell
cd "$env:USERPROFILE\Downloads"
Get-Item .\standard-offline-bundle-7bf0862.tar.gz
Get-Item .\standard-offline-bundle-7bf0862.tar.gz.sha256
Get-FileHash .\standard-offline-bundle-7bf0862.tar.gz -Algorithm SHA256
Get-Content .\standard-offline-bundle-7bf0862.tar.gz.sha256
```

算出したSHA-256と`.sha256`ファイルの値が、次の値で一致することを確認する。

```text
21181cd8113a7c934f4c6cc511d072be3f12a06b2bdedf6480a7e477fb6dd24c
```

一致しない場合は転送せず、配布物を再取得する。

## 5. テストサーバーへ転送する

PowerShellで実行する。

```powershell
cd "$env:USERPROFILE\Downloads"
scp .\standard-offline-bundle-7bf0862.tar.gz user@10.58.143.28:/home/user/
scp .\standard-offline-bundle-7bf0862.tar.gz.sha256 user@10.58.143.28:/home/user/
```

転送完了後、SSH接続する。

```powershell
ssh user@10.58.143.28
```

## 6. サーバー上でチェックサムを確認する

ここからはテストサーバー上で実行する。

```bash
cd /home/user
sha256sum -c standard-offline-bundle-7bf0862.tar.gz.sha256
```

次のように`OK`と表示されることを確認する。

```text
standard-offline-bundle-7bf0862.tar.gz: OK
```

`FAILED`となった場合は展開せず、ファイルを削除して転送し直す。

## 7. 配布物を展開する

```bash
cd /home/user
tar -xzf standard-offline-bundle-7bf0862.tar.gz
cd standard-offline-bundle-7bf0862
```

展開後のファイルを確認する。

```bash
ls -la
ls -la debs payload config
```

配布物内部のチェックサムも確認する。

```bash
sha256sum -c SHA256SUMS
cd debs
sha256sum -c SHA256SUMS
cd ..
```

すべて`OK`になることを確認する。

## 8. Standardをオフライン導入する

```bash
cd /home/user/standard-offline-bundle-7bf0862
sudo bash install_standard.sh
```

処理中にsudoパスワードを求められた場合は、SSHユーザー`user`のパスワードを入力する。

スクリプトは次の処理を自動実行する。

1. OSとCPUアーキテクチャの確認
2. 配布物のチェックサム確認
3. ローカル`.deb`からDocker CLIを導入
4. Dockerイメージを`docker load`で読み込む
5. `/home/user/procedure-db-mvp`へソースを展開
6. Compose設定を検証
7. `--no-build --pull never`でStandardを起動
8. コンテナ状態を表示

最後に`[9/9] Installation completed`と表示されることを確認する。

## 9. 自動検証を実行する

```bash
cd /home/user/standard-offline-bundle-7bf0862
sudo bash verify_standard.sh
```

このスクリプトでは次を確認する。

- DBとAPIが`healthy`である
- Webが`running`である
- Webだけが`0.0.0.0:3000`で公開されている
- APIが`127.0.0.1:8000`に限定されている
- PostgreSQLが`127.0.0.1:5432`に限定されている
- APIとDBのhealthが正常である
- 初期データが`modules=0`、`blueprints=0`である
- 再起動ポリシーが`unless-stopped`である

最後に`[6/6] Verification passed`と表示されることを確認する。

## 10. 作業PCからWebUIを確認する

作業PCのブラウザで次を開く。

```text
http://10.58.143.28:3000/
```

最低限、次を確認する。

- ログイン画面が表示される
- ログイン後にHOME画面が表示される
- API疎通とDB疎通が正常表示になる
- モジュール検索でseedデータ3件を確認できる
- 原本検索でseedデータ2件を確認できる

APIとDBの8000番・5432番ポートは、作業PCから直接接続できないことが正しい状態である。

## 11. サーバー再起動後の復旧を確認する

テストサーバー上で実行する。

```bash
sudo reboot
```

数分待ってから、作業PCのPowerShellで再接続する。

```powershell
ssh user@10.58.143.28
```

再接続後、サーバーで自動検証を再実行する。

```bash
cd /home/user/standard-offline-bundle-7bf0862
sudo bash verify_standard.sh
```

再び`[6/6] Verification passed`になることと、ブラウザからWebUIへ接続できることを確認する。

## 12. 検証結果を記録する

| 確認項目 | 結果 | 備考 |
| --- | --- | --- |
| SSH接続 |  |  |
| 外側チェックサム |  |  |
| 内側チェックサム |  |  |
| Dockerオフライン導入 |  |  |
| Dockerイメージ読込み |  |  |
| 3コンテナ起動 |  |  |
| health確認 |  |  |
| seedデータ確認 |  |  |
| WebUI表示 |  |  |
| 再起動後の自動復旧 |  |  |

## 13. 停止・切り戻し

### 13.1 データを残して停止する

```bash
cd /home/user/standard-offline-bundle-7bf0862
sudo bash uninstall_standard.sh
```

コンテナだけを削除し、DBデータ、イメージ、導入先ディレクトリは残す。

### 13.2 StandardとDockerを完全撤去する

> [!WARNING]
> 次の操作はStandardのDBデータも削除する。必要なデータがないことを確認してから実行する。

```bash
cd /home/user/standard-offline-bundle-7bf0862
sudo bash uninstall_standard.sh --purge-data --remove-docker
```

完全に導入前へ戻す場合は、配布物も削除する。

```bash
cd /home/user
rm -rf -- standard-offline-bundle-7bf0862
rm -f -- standard-offline-bundle-7bf0862.tar.gz
rm -f -- standard-offline-bundle-7bf0862.tar.gz.sha256
```

## 14. エラー時に採取する情報

導入または確認が失敗した場合は、次の結果を保存する。

```bash
cat /etc/os-release
uname -m
dpkg --audit
sudo systemctl status docker --no-pager
sudo docker ps -a
sudo docker image ls
sudo docker volume ls
sudo journalctl -u docker -n 100 --no-pager
```

アプリケーションが起動済みの場合は、Composeログも採取する。

```bash
cd /home/user/procedure-db-mvp
sudo docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  logs --no-color --tail=200
```
