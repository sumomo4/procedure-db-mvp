# 2026-10-22 セキュリティ更新

## 対象

- 2026-10-21公開のNode.jsセキュリティ更新。
- eMudhra / emSignの中間CA証明書の問題に伴う、クライアントの信頼ストア更新。
- このPCのlab、standard、開発用Node.js・Python・cloudflaredを対象とする。
- 社内本番サーバーには接続・変更していない。侵害の有無を判断する調査でもない。

## 変更内容

| 対象 | 対応 |
| --- | --- |
| lab / standardの画面ビルド | Node.js 22.23.4-alpineを公式イメージのダイジェスト付きで指定 |
| lab / standardのAPI | OSのCA更新、公式SHA-256付きwheelでpip 26.2.2へ更新 |
| lab / standardのWeb | Nginx用イメージのCAパッケージ更新 |
| ビルド時の検査 | Node.js、APIのシステムCA、pip内蔵CAに問題のルートCAが残っていたら失敗させる |
| 自動テスト設定 | Node.js、pip、CA更新と信頼ストア検査を追加。CIサービス上の実行は未確認 |
| Windows開発PC | Node.js 24.22.1、cloudflared 2026.10.2。公式SHA-256と発行元署名を検証 |
| WindowsのPython開発環境 | 通常環境・standardの仮想環境のpipを26.2.2へ更新。仮想環境の独立したcertifiも2026.10.19へ更新 |
| QuickTunnel用Dockerイメージ | cloudflare/cloudflared:2026.10.2を取得。トンネルの公開は行わない |

信頼対象から除外されたことを検査する証明書は、`emSign ECC Root CA - G3`。
emSignのすべての証明書が侵害されたと判断して削除するものではない。
証明書検証を無効化したり、`--trusted-host`で回避したりしない。

pipはシステムCAに加え、内蔵するcertifiのCAも使用するため、OSの更新だけでは不十分。
APIには独立したcertifiパッケージを新たに追加せず、pip内蔵バンドルも検査する。
開発用仮想環境に独立したcertifiがある場合は、そのバンドルも更新・検査する。

## 検証

- lab API: 更新イメージ上で370テスト合格。
- standard API: 更新イメージ上で295テスト合格。
- lab / standardのTypeScript・Viteビルド成功。
- 更新APIでpip 26.2.2、内蔵certifi 2026.10.19を確認。
- 更新APIのシステムCA・pip内蔵CAで対象ルートCAが信頼されないことを確認。
- 更新NginxイメージのCAバンドルからも対象ルートCAが除去されていることを確認。
- Windows用Node.js 24.22.1とビルド用Node.js 22.23.4の内蔵CAも検査。
- 更新前のstandardイメージは確認用スクリプトに拒否されることも検証。
- labのブラウザ回帰テスト93項目、実稼働lab / standardのPC・スマートフォン幅のログイン画面・認証・疎通23項目に合格。業務データへの書き込みは行わない。
- lab / standardともAPI・Webコンテナの再ビルド・再作成済み。両APIのヘルスチェック成功。
- DBコンテナIDとデータボリューム名が更新前後で同一であることを確認。
- 既存のStarlette / anyioの非推奨警告が1件ある。今回のテスト失敗ではない。

確認用スクリプトは`tools/security/verify_tls_runtime.py`。
例えばUbuntuサーバーでは、実際に使っているCompose設定を指定し、次のように標準入力から実行する。

```bash
docker compose -f docker-compose.yml -f docker-compose.standard.yml exec -T standard-api python - < tools/security/verify_tls_runtime.py
```

本番で追加のComposeファイルを利用している場合は、その`-f`指定を省略しない。
スクリプトはネットワーク通信やDB更新を行わず、失敗時は終了コードを非ゼロにする。

## 本番へ反映するとき

1. 現在使用中のComposeファイル、ポート設定、マウント、イメージIDを記録し、既存のDBバックアップ手順を実施する。
2. 更新したDockerfileと確認用スクリプトを含むソースを、承認済みの配布方法でサーバーへ反映する。
3. 実際のCompose指定で、`build --pull --no-cache standard-api standard-web`を実行する。
4. 同じCompose指定で、`up -d --no-deps --no-build standard-api standard-web`を実行する。DBは再作成しない。
5. ヘルスチェック、ログイン、Excel取り込み・出力、CA確認用スクリプトを検証する。
6. QuickTunnel利用時は、サーバー側のcloudflaredも2026.10.2以上へ更新し、既存の公開手順で再起動する。

コンテナの再起動だけではイメージ内部の更新は反映されない。
`down -v`、DBボリュームの削除、DB初期化は実行しない。
オフライン配布は、更新済みイメージを含む配布物を再生成し、古いtarやキャッシュ済みイメージを再利用しない。
HTTPS終端を別のプロキシで行っている場合は、そこで使う証明書チェーンとCA更新も別途確認する。

## 別途残っている確認事項

- 既存フロントエンドの`npm audit --package-lock-only`で8件の警告（high 5、moderate 1、low 2）。
- `--omit=dev`では警告0件。今回の確認時点では画面ビルド・開発用依存の警告であり、通常稼働するNode.jsサーバーは存在しない。
- 対象はVite、PostCSS、Browserslist、nanoid、source-map-js、Babel、esbuildなど。更新は互換性確認と回帰テストを伴う別タスクとする。
- この結果はすべての脆弱性が解消したという意味ではない。OS・ブラウザなどの更新も継続する。
- 社内本番サーバーの実バージョン・証明書・配布済みイメージは未確認。

## 一次資料

- [Node.js security releases](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)
- [Python向けCA・pip更新案内](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
- [Cloudflareの影響・cloudflared更新案内](https://blog.cloudflare.com/emudhra-certificate-compromise/)
