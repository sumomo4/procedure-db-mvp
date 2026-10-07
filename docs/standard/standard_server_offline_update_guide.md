# Standard本番サーバー オフライン更新手順書

作成日: 2026-10-07

本番データを保持して、StandardのWebUIとAPIを最新版へ更新する手順です。初回導入や再インストールではありません。作業は本番へSSH接続できる作業PCから実施します。

## 1. 対象

| 項目 | 値 |
| --- | --- |
| 本番サーバー | `10.58.134.28` |
| SSHユーザー | `cnw` |
| WebUI | `http://10.58.134.28/` |
| 導入先 | `/home/cnw/procedure-db-mvp` |
| Docker Composeプロジェクト | `procedure-db-mvp` |
| 更新元 | `7ecf683-http80-20261001` |
| 更新先 | `4c4fe7b-routerfix-http80-20261007` |
| 基準ソース | `4c4fe7b30bc7ec548fbba1e3e16fa2717d439bb3` + React Router修正差分 |
| 配布物 | `standard-update-4c4fe7b-routerfix-http80-20261007.tar.gz` |

旧資料にある `10.58.143.28` や `user` は今回使用しません。HTTPSへの変更も行いません。HTTPは会社で承認された社内ネットワークでの暫定利用とします。

以前の `standard-update-4c4fe7b-http80-20261007.tar.gz` ではなく、`routerfix` 付きの今回の配布物を使用してください。以前の更新版をすでに適用した場合は、この手順の更新元とは異なるため実行せず、現行版に合わせた手順を再確認してください。

## 2. 更新内容と保持するもの

- Standardに反映済みのモジュール・原本管理UI、検索、類似度処理などを更新します。Lab限定の機能は持ち込みません。
- WebUIとAPIの2イメージを、バージョンを固定した名前で持ち込みます。
- StandardのReact Routerを7.14.1から7.18.4へ更新しています。対応ソースの `package.json` と `package-lock.json` は基準コミットへの未コミット差分として収録し、`RELEASE.json` と更新後の `.deploy-version` にその旨を記録します。
- PostgreSQL、Docker本体、OS、EDRの設定は更新しません。
- ユーザー・ロール、モジュール、原本、案件CS・実行記録は同じDBを継続使用します。
- 画像、Access抽出Excel、プレースホルダ設定は `storage/standard` に残します。logsも削除しません。
- 本番の環境変数、ポート設定、既存Composeファイルを上書きしません。
- `proc.module_similarity_signatures` に `algorithm_version` を追加し、既定値を3にします。既存の計算結果は1として保持し、必要時に新方式で再計算します。

## 3. 前提と禁止事項

1. 社内の変更承認を得て、利用者へ停止時間を周知してください。作業完了までログイン・登録・案件実行などの操作を止めます。
2. Ubuntu 24.04 / amd64、Python 3.11以上、既存Docker Engine・Compose v2が必要です。サーバーでAPT・npm・PyPI・Docker Hubには接続しません。
3. 既存WebUI・API・DBが正常稼働し、管理者でログインできることを確認します。
4. バックアップと新旧イメージを保持できる空き容量を確保します。容量はデータ量次第ですが、少なくとも数GBの余裕を用意してください。スクリプトも概算チェックを行います。
5. `install_standard.sh`、`uninstall_standard.sh`、`docker compose down -v`、`docker volume prune`、`docker system prune` は実行しません。
6. 初回導入用の `verify_standard.sh` は空DBを前提としているため使いません。今回は `verify_update.sh` を使用します。
7. 2026-10-07の `npm audit --omit=dev` で本番用npm依存関係の警告は0件です。開発用を含む全体監査には8件が残ります。OS・コンテナ・Pythonを含むシステム全体の安全性を保証するものではありません。[検証記録](standard_update_verification_routerfix_20261007.md) を確認してください。

SSH接続後に確認します。

```bash
ssh cnw@10.58.134.28
```

```bash
python3 --version
sudo docker compose version
cat "$HOME/procedure-db-mvp/.deploy-version"
sudo docker ps
df -h "$HOME" /var/lib/docker
```

Dockerの保存先を変更している場合は `sudo docker info --format '{{.DockerRootDir}}'` で確認し、そのパスの空き容量も確認してください。導入元の版が表と違う場合は更新せず、差分を再確認します。

## 4. 作業PCから転送

作業PCのPowerShellで実行します。ダウンロードフォルダ以外に置いた場合は転送元のパスを変更してください。

```powershell
ssh cnw@10.58.134.28 "mkdir -p ~/mvp-update"
scp "$env:USERPROFILE\Downloads\standard-update-4c4fe7b-routerfix-http80-20261007.tar.gz" cnw@10.58.134.28:mvp-update/
scp "$env:USERPROFILE\Downloads\standard-update-4c4fe7b-routerfix-http80-20261007.tar.gz.sha256" cnw@10.58.134.28:mvp-update/
```

## 5. 照合と展開

SSH接続先のサーバーで実行します。

```bash
cd "$HOME/mvp-update"
sha256sum -c standard-update-4c4fe7b-routerfix-http80-20261007.tar.gz.sha256
```

`OK` を確認してから展開します。同名の展開先がある場合は混在させず、別の空ディレクトリで作業してください。

```bash
tar -xzf standard-update-4c4fe7b-routerfix-http80-20261007.tar.gz
cd standard-update-4c4fe7b-routerfix-http80-20261007
sha256sum -c SHA256SUMS
```

すべて `OK` であることを確認します。エラーがあれば実行せず再転送してください。以下のコマンドは、この展開先から実行します。

## 6. 事前チェック

```bash
sudo bash update_standard.sh --check
```

`PREFLIGHT_OK` を確認します。DBやコンテナへの変更は行いません。同時実行防止用のロックファイルだけが作成されます。

確認項目は、配布物の整合性、更新元の版と実イメージ、Standardだけの構成、HTTP80・API8000・DB5432のポート、API/DBのlocalhost限定公開、既存storageのマウント先、PostgreSQL 16、バックアップ容量の概算です。

## 7. 更新実行

利用者の操作停止を確認してから実行します。

```bash
sudo bash update_standard.sh
```

対象プロジェクトと導入先を確認し、`Type UPDATE to continue:` に対して `UPDATE` と入力します。

実行順序:

1. WebUI・APIを停止し、DBへのアプリ書込みを止める。
2. DBを `pg_dump` で保存し、アーカイブの目次を読み取れることを確認する。
3. storage、既存設定、旧WebUI/APIイメージを保存し、チェックサムを作成する。
4. 新しいイメージを `docker load` で読み込む。
5. DB列追加をトランザクション内で適用する。
6. イメージ指定用 `docker-compose.standard.update.yml` を追加する。
7. APIを起動し、類似度キャッシュ以外の業務テーブルの行数・内容のダイジェストが更新前と一致することを確認する。
8. WebUIを起動し、health・DB接続・画面配信を確認する。
9. 配布バージョンとバックアップ先を記録する。

途中で表示される `BACKUP_READY=/home/cnw/procedure-db-backups/standard/...` を記録してください。バックアップ内は機密情報を含み、rootのみアクセス可能にしています。

最後に `UPDATE_OK` が表示されることを確認します。DBコンテナとDBボリュームは更新前と同じものを使用します。

## 8. 動作確認

```bash
sudo bash verify_update.sh
```

`VERIFY_OK` を確認した後、作業PCのブラウザから `http://10.58.134.28/` を開きます。

- [ ] 既存アカウントでログインでき、管理者のユーザー管理が使える。
- [ ] 既存モジュール・原本・案件CSが残っている。
- [ ] 画像、Access抽出データ、プレースホルダ設定が維持されている。
- [ ] 変更したUI・検索が使える。
- [ ] 管理されたテストデータで類似度チェックが使える。
- [ ] 既存の完了案件の証跡Excelをダウンロードできる。
- [ ] 未完了案件の表示と再開位置が維持されている。実案件のチェック・完了操作は確認目的で行わない。

初回の類似度チェックでは旧計算結果の再作成に時間がかかる場合があります。旧画面が残る場合は再読み込みし、必要に応じてCtrl+F5を1回実行してください。

問題がなければ利用者へ再開を案内します。所要時間はデータ量とディスク性能次第なので固定値ではありません。バックアップは社内の保管期間に従って保持します。

## 9. 失敗時

- バックアップ作成中など、DB変更前の失敗: 元のアプリコンテナを再起動します。表示されたエラーを確認し、自動的に更新をやり直さないでください。
- DB変更開始後の失敗: WebUI・APIを停止したままにします。`BACKUP_READY` のフォルダを指定して [復旧手順書](standard_server_update_recovery_guide.md) に進みます。
- `PREFLIGHT_OK` が出ない、想定外の版、バックアップ不完全: 初回導入スクリプトで回避しないでください。エラー内容を確認します。

## 10. 更新後の起動コマンド

以後、手動でComposeを操作するときは追加ファイルも指定してください。古い3ファイルだけで `up` すると旧イメージへ戻るおそれがあります。

```bash
cd "$HOME/procedure-db-mvp"
sudo docker compose -p procedure-db-mvp -f docker-compose.yml -f docker-compose.standard.yml -f docker-compose.standard.server.yml -f docker-compose.standard.update.yml ps
```

対応ソースは配布物の `payload/standard-source-4c4fe7b-routerfix-http80-20261007.tar.gz` に含みます。サーバー上の既存 `apps/standard` は上書きしません。本番では `build` や `pull` を行わず、検証したイメージを使います。

## 参考

- [Docker Compose up](https://docs.docker.com/reference/cli/docker/compose/up/)
- [Docker image load](https://docs.docker.com/reference/cli/docker/image/load/)
- [PostgreSQL 16 pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html)
