# standard環境 Docker CLIサーバー導入手順書（オンライン版）

## 1. 目的

本書は、Procedure DB MVPの`standard`環境を、インターネット接続可能な社内Ubuntu ServerへDocker CLIで新規導入する手順を示す。

導入先は、OS、IPアドレス、ホスト名、SSH接続用ユーザーだけが設定された初期状態を想定する。Docker Desktop、ホスト版PostgreSQL、Node.js、Pythonは使用しない。

## 2. 構成

### 2.1 導入先

| 項目 | 値 |
| --- | --- |
| サーバー | `192.168.10.6` |
| ホスト名 | 現地設定値を使用 |
| OS | Ubuntu Server 24.04 LTS |
| CPU | `amd64` / `x86_64` |
| SSHユーザー | `user` |
| 配置先 | `/home/user/procedure-db-mvp` |
| 対象環境 | `standard`のみ |

パスワードや秘密情報は本書に記載しない。

### 2.2 初期状態

導入前は次の状態を前提とする。

- Ubuntu Serverが起動している
- 固定IPアドレスとホスト名が設定されている
- 作業PCからSSH接続できる
- `user`が`sudo`を実行できる
- Docker Engine、Docker Compose、Procedure DBは未導入
- ホスト上にPostgreSQL、Node.js、Pythonのアプリ実行環境は不要
- `3000`、`8000`、`5432`が未使用

### 2.3 導入後

| サービス | ホスト側ポート | 公開範囲 | 用途 |
| --- | --- | --- | --- |
| WebUI / Nginx | `3000` | 社内LAN | 利用者の接続先 |
| FastAPI | `8000` | `127.0.0.1`のみ | 保守・疎通確認 |
| PostgreSQL | `5432` | `127.0.0.1`のみ | 保守用。APIはDocker内部で接続 |

通常利用は`http://192.168.10.6:3000/`へアクセスする。

## 3. 前提条件

### 3.1 作業PC

- 最新ソースを取得済み
- Git、PowerShell、`ssh`、`scp`を利用可能
- サーバーのSSH認証情報を利用可能
- `192.168.10.6`へ到達可能

本書ではリポジトリを次の場所として記載する。

```text
C:\Users\clove\OneDrive\ドキュメント\mvp-root
```

### 3.2 サーバー

- APTリポジトリへ接続可能
- Docker Hubへ接続可能
- Dockerビルド中にnpm、PyPIへ接続可能
- 10 GB以上の空き容量を推奨
- 社内LANからTCP `3000`への通信が許可されている

### 3.3 注意事項

- 本書の認証情報はMVP用であり、本番前に変更する。
- `docker compose down -v`はDBを削除するため、初期化時以外は実行しない。
- 更新時に`storage/standard`、`logs/standard`、Docker volumeを削除しない。
- API `8000`とDB `5432`は社内LANへ直接公開しない。
- Quick Tunnelなどの外部公開は本書の対象外とする。

## 4. サーバー初期状態の確認

作業PCのPowerShellから接続する。

```powershell
ssh user@192.168.10.6
```

サーバーで実行する。

```bash
hostname
hostname -I
cat /etc/os-release
uname -m
id
df -h /
free -h
```

確認基準:

- OSがUbuntu 24.04 LTS
- `uname -m`が`x86_64`
- `id`に`sudo`グループが含まれる
- IPアドレスとホスト名が申請値どおり

名前解決も確認する。

```bash
getent hosts "$(hostname)"
cat /etc/hosts
```

利用ポートと未導入状態を確認する。

```bash
sudo ss -ltnp | grep -E ':(3000|8000|5432)[[:space:]]' || true
command -v docker || true
test ! -e /home/user/procedure-db-mvp && echo 'project directory: absent'
```

ポート使用中または配置先が存在する場合は、既存用途を確認してから作業する。

## 5. インターネット疎通確認

```bash
getent hosts archive.ubuntu.com
getent hosts registry-1.docker.io
curl -I --max-time 10 https://archive.ubuntu.com/
curl -I --max-time 10 https://registry-1.docker.io/v2/
```

Docker Registryは`401 Unauthorized`でも、HTTP応答が返れば疎通できている。

社内プロキシが必要な場合は、APT、Docker daemon、ビルド時のnpm・PyPIにプロキシ設定が必要になる。設定値は社内管理者から取得する。

## 6. Docker EngineとCompose CLIの導入

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker user
```

グループ反映のため再接続する。

```bash
exit
```

```powershell
ssh user@192.168.10.6
```

```bash
docker --version
docker compose version
systemctl is-enabled docker
systemctl is-active docker
id
docker ps
```

`docker`グループが表示され、`docker ps`が権限エラーにならないことを確認する。

## 7. 配布アーカイブの作成

作業PCのPowerShellで実行する。

```powershell
cd "C:\Users\clove\OneDrive\ドキュメント\mvp-root"

git branch --show-current
git log -1 --oneline
git status --short

$sha = git rev-parse --short HEAD
$fullSha = git rev-parse HEAD
$archive = "$env:USERPROFILE\Downloads\procedure-db-mvp-standard-$sha.tar.gz"

git archive --format=tar.gz --output $archive HEAD
Get-Item $archive
Get-FileHash $archive -Algorithm SHA256
```

未コミット・未追跡・`.gitignore`対象ファイルは`git archive`に含まれない。必要なテンプレートや設定がコミット済みか確認する。

## 8. 転送、検証、展開

作業PCで実行する。

```powershell
scp $archive user@192.168.10.6:/home/user/
ssh user@192.168.10.6
```

サーバーで、作業PCに表示されたSHA-256と照合する。

```bash
sha256sum /home/user/procedure-db-mvp-standard-<commit>.tar.gz
```

`<commit>`を実際の短縮コミットIDへ置き換える。

```bash
mkdir -p /home/user/procedure-db-mvp
tar -xzf /home/user/procedure-db-mvp-standard-<commit>.tar.gz \
  -C /home/user/procedure-db-mvp
cd /home/user/procedure-db-mvp

printf 'DEPLOY_SHA=%s\n' '<full-commit-id>' > .deploy-version
cat .deploy-version
```

サービス定義を確認する。

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  config --services
```

`standard-db`、`standard-api`、`standard-web`が表示されること。

## 9. サーバー専用Compose設定

WebUIだけを社内LANへ公開し、APIとDBをlocalhostへ制限する。

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

エラーがないことを確認する。

## 10. ファイアウォール確認

```bash
sudo ufw status verbose
```

`Status: active`の場合だけ、実際の社内CIDRに置き換えてWebUIを許可する。

```bash
sudo ufw allow from 192.168.10.0/24 to any port 3000 proto tcp
sudo ufw status numbered
```

TCP `8000`と`5432`は許可しない。

## 11. ビルドと起動

```bash
cd /home/user/procedure-db-mvp

docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  up -d --build
```

初回はDocker Hub、npm、PyPIから取得するため時間がかかる。

## 12. 導入確認

### 12.1 コンテナ

```bash
docker compose \
  -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  ps
```

`standard-db`と`standard-api`が`healthy`、`standard-web`が`Up`であること。

### 12.2 ポート

```bash
sudo ss -ltnp | grep -E ':(3000|8000|5432)[[:space:]]'
```

期待値:

- `3000`は`0.0.0.0`またはサーバーIPで待受
- `8000`と`5432`は`127.0.0.1`だけで待受

### 12.3 サーバー内部の疎通

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8000/api/v1/health/db
curl -fsS http://127.0.0.1:3000/api/v1/health
curl -fsS http://127.0.0.1:3000/api/v1/health/db
```

### 12.4 seedデータ

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

### 12.5 作業PCとブラウザ

```powershell
Invoke-WebRequest http://192.168.10.6:3000/ -UseBasicParsing
Invoke-RestMethod http://192.168.10.6:3000/api/v1/health
Invoke-RestMethod http://192.168.10.6:3000/api/v1/health/db
```

ブラウザで`http://192.168.10.6:3000/`を開く。

## 13. 再起動復旧確認

```bash
sudo reboot
```

再接続後に実行する。

```bash
cd /home/user/procedure-db-mvp
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml ps
docker inspect -f '{{.Name}} restart={{.HostConfig.RestartPolicy.Name}}' \
  procedure-db-mvp-standard-web-1 \
  procedure-db-mvp-standard-api-1 \
  procedure-db-mvp-standard-db-1
```

3コンテナが復旧し、すべて`restart=unless-stopped`であること。

## 14. AccessDB抽出ファイル

案件化で使うExcelはGit管理対象外のため、別途配置する。

```text
/home/user/procedure-db-mvp/storage/standard/access_exports
```

```powershell
scp .\access_exports\*.xlsx user@192.168.10.6:/home/user/procedure-db-mvp/storage/standard/access_exports/
```

## 15. 日常運用

```bash
cd /home/user/procedure-db-mvp
```

```bash
# 状態
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml ps

# ログ
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml logs --tail=200

# 停止・起動
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml stop
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml start

# DBを残してコンテナを削除
docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml down
```

## 16. バックアップ

```bash
cd /home/user/procedure-db-mvp
mkdir -p backups

docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml \
  exec -T standard-db pg_dump -U standard_user -d mvp_standard \
  > "backups/mvp_standard_$(date +%Y%m%d_%H%M%S).sql"

tar -czf "backups/standard_storage_$(date +%Y%m%d_%H%M%S).tar.gz" storage/standard
```

## 17. トラブルシューティング

### Docker権限エラー

SSHへ再接続し、`id`に`docker`が含まれることを確認する。

### ビルド時の取得失敗

```bash
getent hosts registry-1.docker.io
docker pull postgres:16-alpine
```

npmまたはPyPIで失敗する場合は、社内プロキシ、SSL検査、許可ドメインを確認する。

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

## 18. 完了チェックリスト

- [ ] IPアドレス、ホスト名、OS、CPUを確認した
- [ ] Docker、ComposeをAPTから導入した
- [ ] `user`がDockerを操作できる
- [ ] 配布アーカイブのSHA-256が一致した
- [ ] Compose設定でAPIとDBがlocalhost限定になった
- [ ] `standard-db`と`standard-api`が`healthy`
- [ ] `standard-web`が`Up`
- [ ] WebUIを社内LANから表示できる
- [ ] API health、DB healthが成功する
- [ ] seedモジュール3件、seed原本2件を確認した
- [ ] サーバー再起動後に自動復旧した
- [ ] AccessDB抽出Excelの配置要否を確認した
