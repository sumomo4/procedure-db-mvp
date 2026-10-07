# Standard本番サーバー HTTPS設定手順書

作成日: 2026-10-01

## 1. 対象と現在の状況

| 項目 | 設定・状況 |
| --- | --- |
| サーバー | Ubuntu Server 24.04 LTS / amd64 |
| 接続先 | `https://10.58.143.28/` |
| HTTPSポート | TCP `443`。開放済みと確認 |
| HTTPポート | TCP `80`。HTTPSへ転送 |
| 配置先 | `/home/user/procedure-db-mvp` |
| 証明書の発行方法 | 管理部門への確認待ち |
| 本番サーバーへの設定適用 | 未実施 |

本書は、Standardを導入済みのサーバーへHTTPS設定を追加する手順である。アプリ本体の新規導入は、`standard_docker_cli_server_installation_offline_guide.md`を参照する。

最新の`standard-offline-bundle-7ecf683-http80-20261001.tar.gz`には、本書とHTTPS用設定を含めている。今回の導入はHTTP・80番で行い、証明書の確認後に本書の手順でHTTPSへ切り替える。旧版の`standard-offline-bundle-7bf0862.tar.gz`は使用しない。

## 2. 管理部門へ確認する内容

次の内容で、社内認証局等によるサーバー証明書の発行方法を確認する。

```text
用途: 社内Webアプリ（Procedure DB / Standard）のHTTPS通信
アクセスURL: https://10.58.143.28/
対象サーバー: Ubuntu Server 24.04 LTS / Nginx
証明書のSAN: iPAddressとして10.58.143.28を含める
証明書の用途: TLSサーバー認証（serverAuth）
配置形式: PEM形式のサーバー証明書・中間証明書チェーン
確認事項:
- IPアドレスを対象とした証明書を発行できるか
- 秘密鍵とCSRをサーバー側で作成するか、指定の別手順があるか
- 発行元CAの証明書が利用者のWindows端末で信頼されているか
- 未配布の場合のCA証明書の配布方法
- 証明書の有効期限、更新手順、更新の担当者
```

IPアドレスで接続するため、CNだけでなくSANの`iPAddress`に`10.58.143.28`が必要である。DNS名として同じ文字列を登録するだけではIPアドレスの照合条件を満たさない。

参考: [RFC 9525: IPアドレスの照合](https://www.rfc-editor.org/rfc/rfc9525.html#section-6.4)

証明書が未発行の場合は、ここで発行方法を確認する。ブラウザーの証明書警告を無視する運用を前提にしない。

## 3. 配置するファイル

| ファイル | 配置先 | 内容 |
| --- | --- | --- |
| `fullchain.pem` | `/etc/procedure-db/tls/fullchain.pem` | サーバー証明書、必要な中間証明書の順で格納 |
| `privkey.pem` | `/etc/procedure-db/tls/privkey.pem` | サーバー証明書に対応した秘密鍵 |
| `ca-chain.pem` | `/etc/procedure-db/tls/ca-chain.pem` | 接続検証用の発行元CA証明書。管理部門の指定するチェーン |
| `docker-compose.standard.https.yml` | アプリ配置先直下 | HTTPS用Compose追加設定 |
| `nginx.standard.https.conf` | アプリ配置先直下 | NginxのHTTPS設定 |

Nginxを自動起動できる形式の秘密鍵を、管理部門のルールに従って用意する。秘密鍵をGitやアプリの配布物へ含めない。

Composeは次の4ファイルを組み合わせる。HTTPS追加設定には、HTTP・80番だけの公開を80番・443番に置き換える`!override`を使用するため、Docker Compose 2.24.4以上が必要である。

```text
docker-compose.yml
docker-compose.standard.yml
docker-compose.standard.server.yml
docker-compose.standard.https.yml
```

## 4. サーバーへの証明書配置

以降は、管理部門の手順で証明書・秘密鍵を用意した後に実施する。例では、配置元を`/home/user/standard-tls`としている。秘密鍵をサーバーで生成した場合は、元の鍵を使用し、別の鍵で上書きしない。

サーバーで実行する。

```bash
sudo install -d -m 700 /etc/procedure-db/tls
sudo install -m 644 /home/user/standard-tls/fullchain.pem /etc/procedure-db/tls/fullchain.pem
sudo install -m 600 /home/user/standard-tls/privkey.pem /etc/procedure-db/tls/privkey.pem
sudo install -m 644 /home/user/standard-tls/ca-chain.pem /etc/procedure-db/tls/ca-chain.pem
```

サーバー証明書の対象と期限を確認する。

```bash
sudo openssl x509 -in /etc/procedure-db/tls/fullchain.pem -noout -ext subjectAltName
sudo openssl x509 -in /etc/procedure-db/tls/fullchain.pem -noout -dates
```

`IP Address:10.58.143.28`が含まれ、有効期間内であることを確認する。

## 5. HTTPS設定の配置

アプリ配置先で実行する。

```bash
cd /home/user/procedure-db-mvp
sudo install -m 644 tools/standard_offline_bundle/config/docker-compose.standard.https.yml ./docker-compose.standard.https.yml
sudo install -m 644 tools/standard_offline_bundle/config/nginx.standard.https.conf ./nginx.standard.https.conf
sudo docker compose version
sudo ss -lntp 'sport = :80 or sport = :443'
```

80番・443番を別サービスが使用している場合は、競合するサービスを停止する前に用途を確認する。

APIとDBは、`docker-compose.standard.server.yml`によりlocalhost限定で公開する。HTTPS設定だけを指定して起動しない。

構成を検証する。

```bash
sudo docker compose -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  -f docker-compose.standard.https.yml \
  config --quiet
```

既存のStandard APIが起動している状態で、証明書とNginx設定を検証する。

```bash
sudo docker compose -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  -f docker-compose.standard.https.yml \
  run --rm --no-deps --pull never standard-web nginx -t
```

証明書がない、秘密鍵が一致しない、設定に誤りがある等のエラーが出た場合は修正してから進める。

## 6. HTTPSで起動する

```bash
sudo docker compose -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  -f docker-compose.standard.https.yml \
  up -d --no-build --pull never
```

HTTPS追加設定で次を適用する。

- WebUIは80番・443番で公開し、80番へのアクセスはHTTPSへ転送する。
- Nginxは443番でTLSを受け付け、APIへHTTPS経由であることを伝える。
- 認証Cookieに`Secure`属性を付与する。
- APIの許可Originを`https://10.58.143.28`に設定する。
- 証明書と秘密鍵はサーバー上のファイルを読み取り専用で参照する。

参考: [Nginx公式: HTTPS設定](https://nginx.org/en/docs/http/configuring_https_servers.html)

## 7. サーバー上の動作確認

```bash
sudo ss -lntp 'sport = :80 or sport = :443 or sport = :8000 or sport = :5432'
sudo curl --noproxy '*' --fail --show-error \
  --cacert /etc/procedure-db/tls/ca-chain.pem \
  https://10.58.143.28/api/v1/health
sudo curl --noproxy '*' --fail --show-error \
  --cacert /etc/procedure-db/tls/ca-chain.pem \
  https://10.58.143.28/api/v1/health/db
curl --noproxy '*' --head http://10.58.143.28/
```

確認する内容:

- 443番で待ち受けている。
- API・DBのhealthが成功する。
- HTTPは`308`で`https://10.58.143.28/`へ転送される。
- 8000番と5432番の公開先は`127.0.0.1`のままである。

証明書エラーが出た場合は、SAN、期限、CAの信頼、中間証明書チェーンを確認する。`curl -k`で検証を省略した結果を合格としない。

`verify_standard.sh`はHTTP・80番の新規導入確認用である。HTTPS切替後の接続確認は本章と次章で行う。

## 8. 作業PCから確認する

PowerShellで実行する。

```powershell
Test-NetConnection 10.58.143.28 -Port 443
Invoke-RestMethod 'https://10.58.143.28/api/v1/health'
Invoke-RestMethod 'https://10.58.143.28/api/v1/health/db'
```

`TcpTestSucceeded`が`True`になっても証明書の検証成功とは限らない。続くHTTPSの取得が成功することを確認する。

Windows端末が発行元CAを信頼していない場合は、管理部門にCA証明書の配布を依頼する。CAを信頼する設定と、Nginxが中間証明書を送信する設定は両方必要である。

ブラウザーで`https://10.58.143.28/`を開き、次を確認する。

- 証明書警告が表示されない。
- ログイン・ログアウト・モジュール取込が成功する。
- ログイン時のCookieに`Secure`属性がある。

## 9. 運用時の操作

Compose操作時には、手順6と同じ4ファイルを指定する。特に、更新時にHTTPS追加設定を外して`up`すると、公開ポートや認証設定がHTTP構成へ戻るため、指定ファイルをそろえる。

再起動後の自動復旧を確認し、証明書の期限・更新担当者を記録する。更新後はNginx設定の検証を実行し、成功した場合にWebコンテナのNginxを再読み込みする。

```bash
sudo docker compose -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  -f docker-compose.standard.https.yml \
  exec -T standard-web nginx -t
sudo docker compose -p procedure-db-mvp \
  -f docker-compose.yml \
  -f docker-compose.standard.yml \
  -f docker-compose.standard.server.yml \
  -f docker-compose.standard.https.yml \
  exec -T standard-web nginx -s reload
```

## 10. 完了条件

- [ ] 管理部門からIPアドレス対象の証明書の発行方法を確認した。
- [ ] 証明書のSANに`iPAddress:10.58.143.28`が含まれる。
- [ ] サーバー証明書と秘密鍵が一致し、Nginxの設定検証が成功した。
- [ ] 利用者端末が発行元CAを信頼する。
- [ ] 443番へのTCP接続と、証明書検証付きのHTTPS接続が成功した。
- [ ] WebUIでログイン・モジュール取込・ログアウトが成功した。
- [ ] APIとDBがlocalhost限定で公開されている。
- [ ] 証明書の更新担当者と更新手順が決まっている。
