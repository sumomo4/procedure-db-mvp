# standard環境 Docker CLIサーバー導入手順書（オフライン版）

## 1. 目的

本書は、Procedure DB MVPの`standard`環境を、インターネットへ接続できない社内Ubuntu ServerへDocker CLIで新規導入する手順を示す。

導入先は、OS、IPアドレス、ホスト名、SSH接続用ユーザーだけが設定された初期状態を想定する。サーバーではAPTの外部取得、Dockerイメージのpull、npm、PyPIを使用しない。

## 2. 方式

インターネット接続可能な準備環境で、次を完成させてから社内へ持ち込む。

1. Docker EngineとCompose CLIの`.deb`一式
2. Git管理対象のソースアーカイブ
3. ビルド済みWeb、API、PostgreSQLイメージ
4. SHA-256チェックサム

オフラインサーバーでは`.deb`をローカル導入し、`docker load`後に`--no-build --pull never`で起動する。

## 3. 構成

### 3.1 導入先

| 項目 | 値 |
| --- | --- |
| サーバー | `10.58.143.28` |
| ホスト名 | 現地設定値を使用 |
| OS | Ubuntu Server 24.04 LTS |
| CPU | `amd64` / `x86_64` |
| SSHユーザー | `user` |
| 配置先 | `/home/user/procedure-db-mvp` |
| 対象環境 | `standard`のみ |
| インターネット | 接続不可 |

パスワードや秘密情報は本書に記載しない。

### 3.2 初期状態

- Ubuntu Serverが起動している
- 固定IPアドレスとホスト名が設定されている
- 承認された社内経路でSSHまたはファイル転送ができる
- `user`が`sudo`を実行できる
- Docker Engine、Docker Compose、Procedure DBは未導入
- ホスト版PostgreSQLは未導入
- `3000`、`8000`、`5432`が未使用

### 3.3 導入後

| サービス | ホスト側ポート | 公開範囲 | 用途 |
| --- | --- | --- | --- |
| WebUI / Nginx | `3000` | 社内LAN | 利用者の接続先 |
| FastAPI | `8000` | `127.0.0.1`のみ | 保守・疎通確認 |
| PostgreSQL | `5432` | `127.0.0.1`のみ | 保守用。APIはDocker内部で接続 |

## 4. 前提条件

### 4.1 オンライン準備環境

- 導入先と同じUbuntu 24.04 `amd64`のクリーンなVMを用意できる
- 最新ソースを取得済みの作業PCがある
- Linux `amd64`イメージをビルドできるDocker DesktopまたはDocker Engineがある
- APT、Docker Hub、npm、PyPIへ接続できる
- 大容量tarを保存できる

Docker用`.deb`は、導入先と同じOS・CPU・初期パッケージ構成のクリーンVMで収集する。異なるUbuntu版から持ち込まない。

### 4.2 オフラインサーバー

- 10 GB以上の空き容量を推奨
- 社内LANからTCP `3000`へ接続可能
- USB、社内共有、SCPなど承認された持込み経路がある
- API `8000`とDB `5432`を社内LANへ直接公開しない

### 4.3 作業PC上のリポジトリ

```text
C:\Users\clove\OneDrive\ドキュメント\mvp-root
```

### 4.4 注意事項

- 本番前にMVP用認証情報を変更する。
- `docker compose down -v`はDBを削除するため、初期化時以外は実行しない。
- 更新時に`storage/standard`、`logs/standard`、Docker volumeを削除しない。
- Quick Tunnelなどの外部公開は本書の対象外とする。

## 5. サーバー初期状態の確認

```powershell
ssh user@10.58.143.28
```

```bash
hostname
hostname -I
cat /etc/os-release
uname -m
id
df -h /
free -h
getent hosts "$(hostname)"
cat /etc/hosts
```

確認基準:

- Ubuntu 24.04 LTS、`x86_64`
- IPアドレスとホスト名が申請値どおり
- `user`が`sudo`を利用可能

```bash
sudo ss -ltnp | grep -E ':(3000|8000|5432)[[:space:]]' || true
command -v docker || true
test ! -e /home/user/procedure-db-mvp && echo 'project directory: absent'
```

## 6. 必要な配布物

| ファイル | 内容 |
| --- | --- |
| `docker-offline-debs-ubuntu24-amd64.tar.gz` | Docker、Composeと依存`.deb` |
| `procedure-db-mvp-standard-<commit>.tar.gz` | ソース |
| `procedure-db-standard-images-<commit>.tar` | Web、API、PostgreSQLイメージ |
| `SHA256SUMS` | 上記3ファイルのチェックサム |

### 6.1 自動導入用の単一配布物

事前検証済みの配布物は、次の形式にまとめる。

```text
standard-offline-bundle-<commit>.tar.gz
standard-offline-bundle-<commit>.tar.gz.sha256
```

展開後にはDocker用`.deb`、ソース、3イメージ、サーバー設定に加え、次のスクリプトが含まれる。

| ファイル | 用途 |
| --- | --- |
| `install_standard.sh` | チェックサム確認、Docker導入、イメージ読込み、Standard起動 |
| `verify_standard.sh` | health、ポート、seedデータ、再起動設定の確認 |
| `uninstall_standard.sh` | 停止または完全撤去 |

社内サーバーへ持ち込んだ後は、次の操作で導入できる。

```bash
cd /home/user
sha256sum -c standard-offline-bundle-<commit>.tar.gz.sha256
tar -xzf standard-offline-bundle-<commit>.tar.gz
cd standard-offline-bundle-<commit>
sudo bash install_standard.sh
sudo bash verify_standard.sh
```

自動導入スクリプトは`dpkg -i`、`docker load`、`--no-build --pull never`を使用し、外部からパッケージやイメージを取得しない。

## 7. Docker用`.deb`一式の準備

> [!WARNING]
> この章は導入先の`10.58.143.28`では実行しないこと。
> インターネットへ接続できる、導入先とは別のUbuntu 24.04 `amd64`準備用VMで実行する。

導入先と同じUbuntu 24.04 `amd64`のクリーンなオンラインVMで実行する。

```bash
cat /etc/os-release
uname -m
sudo apt-get update
sudo rm -f /var/cache/apt/archives/*.deb
sudo apt-get install -y --download-only \
  ca-certificates curl docker.io docker-compose-v2

mkdir -p ~/docker-offline-debs
sudo cp /var/cache/apt/archives/*.deb ~/docker-offline-debs/
sudo chown -R "$USER:$USER" ~/docker-offline-debs
cd ~/docker-offline-debs
sha256sum *.deb > SHA256SUMS
cd ~
tar -czf docker-offline-debs-ubuntu24-amd64.tar.gz docker-offline-debs
```

この処理はクリーンVMで行う。既にDockerや依存パッケージが入った端末では、必要な`.deb`がすべてキャッシュされない場合がある。

## 8. ソースとDockerイメージの準備

作業PCのPowerShellで実行する。

### 8.1 コミット確認とソース作成

```powershell
cd "C:\Users\clove\OneDrive\ドキュメント\mvp-root"

git branch --show-current
git log -1 --oneline
git status --short

$sha = git rev-parse --short HEAD
$fullSha = git rev-parse HEAD
$archive = "$env:USERPROFILE\Downloads\procedure-db-mvp-standard-$sha.tar.gz"

git archive --format=tar.gz --output $archive HEAD
```

未コミット・未追跡・`.gitignore`対象ファイルは含まれない。

### 8.2 `linux/amd64`イメージの作成

Docker DesktopはLinuxコンテナモードで使用する。

```powershell
docker build --platform linux/amd64 `
  -t procedure-db-mvp-standard-web:latest `
  .\apps\standard\frontend

docker build --platform linux/amd64 `
  -t procedure-db-mvp-standard-api:latest `
  .\apps\standard\backend

docker pull --platform linux/amd64 postgres:16-alpine
```

```powershell
docker image inspect `
  --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}' `
  procedure-db-mvp-standard-web:latest `
  procedure-db-mvp-standard-api:latest `
  postgres:16-alpine
```

すべて`linux/amd64`であること。

### 8.3 イメージtar作成

```powershell
$images = "$env:USERPROFILE\Downloads\procedure-db-standard-images-$sha.tar"

docker save -o $images `
  procedure-db-mvp-standard-web:latest `
  procedure-db-mvp-standard-api:latest `
  postgres:16-alpine
```

### 8.4 配布物とチェックサム

オンラインVMで作成したDocker用`.deb`アーカイブをDownloadsへ置いてから実行する。

```powershell
$debs = "$env:USERPROFILE\Downloads\docker-offline-debs-ubuntu24-amd64.tar.gz"
$manifest = "$env:USERPROFILE\Downloads\SHA256SUMS"

@($archive, $images, $debs) |
  ForEach-Object {
    $hash = Get-FileHash $_ -Algorithm SHA256
    "$($hash.Hash.ToLower())  $(Split-Path $hash.Path -Leaf)"
  } | Set-Content $manifest -Encoding ascii

Get-Content $manifest
```

## 9. 持込みとチェックサム確認

承認された方法で4ファイルをサーバーの`/home/user/`へ配置する。

LAN内SCPを利用できる場合:

```powershell
scp $archive $images $debs $manifest user@10.58.143.28:/home/user/
```

サーバーで実行する。

```bash
cd /home/user
sha256sum -c SHA256SUMS
```

3ファイルすべて`OK`になること。失敗したファイルは使用しない。

## 10. Docker EngineとCompose CLIのオフライン導入

```bash
cd /home/user
tar -xzf docker-offline-debs-ubuntu24-amd64.tar.gz
cd docker-offline-debs
sha256sum -c SHA256SUMS

sudo dpkg -i ./*.deb
sudo dpkg --audit
sudo systemctl enable --now docker
sudo usermod -aG docker user
```

`dpkg --audit`が何も表示しなければ、依存関係と設定は正常である。

依存不足や未設定パッケージが表示された場合、オフラインサーバー上で解決しようとせず、不足`.deb`を同一構成のオンラインVMで追加してバンドルを作り直す。

再接続する。

```bash
exit
```

```powershell
ssh user@10.58.143.28
```

```bash
docker --version
docker compose version
systemctl is-enabled docker
systemctl is-active docker
id
docker ps
```

## 11. ソース展開

```bash
mkdir -p /home/user/procedure-db-mvp
tar -xzf /home/user/procedure-db-mvp-standard-<commit>.tar.gz \
  -C /home/user/procedure-db-mvp
cd /home/user/procedure-db-mvp

printf 'DEPLOY_SHA=%s\n' '<full-commit-id>' > .deploy-version
cat .deploy-version
```

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  config --services
```

`standard-db`、`standard-api`、`standard-web`が表示されること。

## 12. サーバー専用Compose設定

```bash
cd /home/user/procedure-db-mvp

cat > docker-compose.standard.server.yml <<'EOF'
services:
  standard-web:
    restart: unless-stopped

  standard-api:
    restart: unless-stopped
    ports: !override
      - "127.0.0.1:8000:8000"

  standard-db:
    restart: unless-stopped
    ports: !override
      - "127.0.0.1:5432:5432"
EOF
```

```bash
docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  config > /tmp/standard-compose-config.yml
```

## 13. ファイアウォール確認

```bash
sudo ufw status verbose
```

`Status: active`の場合だけ、実際の社内CIDRへ置き換えて許可する。

```bash
ALLOWED_NETWORK="<allowed-network-cidr>"
sudo ufw allow from "$ALLOWED_NETWORK" to any port 3000 proto tcp
sudo ufw status numbered
```

TCP `8000`と`5432`は許可しない。

## 14. イメージ読込みとオフライン起動

```bash
docker load -i /home/user/procedure-db-standard-images-<commit>.tar

docker image inspect \
  --format '{{.RepoTags}} {{.Os}}/{{.Architecture}}' \
  procedure-db-mvp-standard-web:latest \
  procedure-db-mvp-standard-api:latest \
  postgres:16-alpine
```

```bash
cd /home/user/procedure-db-mvp

docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  up -d --no-build --pull never
```

`--no-build`と`--pull never`は必須。外部取得を要求せず、持込み済みイメージだけで起動する。

## 15. 導入確認

### 15.1 コンテナ

```bash
docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  ps
```

`standard-db`と`standard-api`が`healthy`、`standard-web`が`Up`であること。

### 15.2 ポート

```bash
sudo ss -ltnp | grep -E ':(3000|8000|5432)[[:space:]]'
```

- `3000`は社内LANから接続可能
- `8000`と`5432`は`127.0.0.1`限定

### 15.3 サーバー内部の疎通

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/health/db
curl -fsS http://127.0.0.1:3000/api/v1/health
curl -fsS http://127.0.0.1:3000/api/v1/health/db
```

### 15.4 seedデータ

```bash
docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  exec -T standard-db \
  psql -U standard_user -d mvp_standard -Atc \
  "SELECT 'modules=' || count(*) FROM proc.modules; SELECT 'blueprints=' || count(*) FROM proc.blueprints;"
```

期待値:

```text
modules=0
blueprints=0
```

### 15.5 作業PCとブラウザ

```powershell
Invoke-WebRequest http://10.58.143.28:3000/ -UseBasicParsing
Invoke-RestMethod http://10.58.143.28:3000/api/v1/health
Invoke-RestMethod http://10.58.143.28:3000/api/v1/health/db
```

ブラウザで`http://10.58.143.28:3000/`を開く。

## 16. 再起動復旧確認

```bash
sudo reboot
```

再接続後:

```bash
cd /home/user/procedure-db-mvp
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml ps
docker inspect -f '{{.Name}} restart={{.HostConfig.RestartPolicy.Name}}' \
  procedure-db-mvp-standard-web-1 \
  procedure-db-mvp-standard-api-1 \
  procedure-db-mvp-standard-db-1
```

## 17. AccessDB抽出ファイル

案件化用ExcelはGit管理対象外のため、承認された方法で別途配置する。

```text
/home/user/procedure-db-mvp/storage/standard/access_exports
```

## 18. 日常運用

```bash
cd /home/user/procedure-db-mvp

# 状態
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml ps

# ログ
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml logs --tail=200

# 停止・起動
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml stop
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml start

# 配布済みイメージだけで再作成
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml up -d --no-build --pull never
```

## 19. バックアップ

```bash
cd /home/user/procedure-db-mvp
mkdir -p backups

docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml \
  exec -T standard-db pg_dump -U standard_user -d mvp_standard \
  > "backups/mvp_standard_$(date +%Y%m%d_%H%M%S).sql"

tar -czf "backups/standard_storage_$(date +%Y%m%d_%H%M%S).tar.gz" storage/standard
```

## 20. トラブルシューティング

### `.deb`導入時に依存不足

不足パッケージ名を記録し、同一構成のオンラインVMでバンドルを再作成する。オフラインサーバーで`apt-get -f install`を実行しても外部取得できない。

### `image not found`またはpull要求

```bash
docker images --format '{{.Repository}}:{{.Tag}}'
```

3イメージの名前を確認し、起動時に`--no-build --pull never`を付ける。

### `exec format error`

持込みイメージが`linux/amd64`ではない。オンライン環境で`--platform linux/amd64`を指定して再作成する。

### ポート競合

```bash
sudo ss -ltnp | grep -E ':(3000|8000|5432)[[:space:]]'
```

既存用途を確認し、無断で停止しない。

### WebUIからAPIへ接続できない

```bash
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml ps
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml logs --tail=100 standard-api standard-web
```

## 21. 完了チェックリスト

- [ ] IPアドレス、ホスト名、OS、CPUを確認した
- [ ] 同一OS・CPUのクリーンVMでDocker用`.deb`を収集した
- [ ] Web、API、PostgreSQLの3イメージを`linux/amd64`で作成した
- [ ] 全配布物のSHA-256が一致した
- [ ] 外部接続なしでDockerとComposeを導入できた
- [ ] `docker load`後に3イメージを確認した
- [ ] `--no-build --pull never`で起動した
- [ ] APIとDBがlocalhost限定になった
- [ ] `standard-db`と`standard-api`が`healthy`
- [ ] `standard-web`が`Up`
- [ ] WebUIを社内LANから表示できる
- [ ] API health、DB healthが成功する
- [ ] seedモジュール3件、seed原本2件を確認した
- [ ] サーバー再起動後に自動復旧した
- [ ] AccessDB抽出Excelの配置要否を確認した
