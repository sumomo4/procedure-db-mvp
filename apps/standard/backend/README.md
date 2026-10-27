# 手順書DB standard API

Sprint 1 / SB1-08, SB1-09, SB1-13, SB1-14 向けの FastAPI 構成です。

## 主なエンドポイント

| Method | Path | 用途 |
| --- | --- | --- |
| `GET` | `/api/v1/health` | API疎通確認 |
| `GET` | `/api/v1/health/db` | PostgreSQL接続確認 |

## ローカル起動

```powershell
cd apps\standard\backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

疎通確認:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Docker Composeで起動している場合は、Windows側のポート予約状況によって `127.0.0.1` より `localhost` のほうが安定する場合があります。

## テスト

```powershell
cd apps\standard\backend
python -m pytest
```

DB接続確認APIは `psycopg` で `SELECT 1` を実行します。Docker Compose 起動時は `infra/env/standard.env.example` の値を利用します。

## standard: AccessDBの参照元管理

管理者は `/case-docs/data-sources` で参照元DBを登録・編集します。案件化とプレースホルダ設定では、参照元DBを1つ選択します。同名のExcel・ホスト名・プレースホルダも、参照元DBごとに区別します。複数DBの同時参照は未対応です。

- 抽出ファイルはDBごとのフォルダに配置します。既存参照元は `access_exports/ssc/`、識別子 `uni` の追加DBは `access_exports/uni/` です。環境変数 `CASE_DOC_ACCESS_EXPORT_DIR` は各DBの親ディレクトリのままにしてください。
- 既存参照元の識別子は `ssc`、既定の表示名はSSCです。旧識別子 `sbc` は参照APIの互換入力としてのみ受け付け、一覧・新規案件の保存では `ssc` を使用します。`sbc` を別DBとして再登録することはできません。
- SSCのプレースホルダ設定は従来の `CASE_DOC_PLACEHOLDER_MAPPING_PATH` を維持します。設定ファイルの移動や抽出Excelのファイル名変更は不要です。
- 識別子 `uni` で登録すると、抽出先は `CASE_DOC_ACCESS_EXPORT_DIR/uni/`、設定は既存設定ファイルの親ディレクトリ配下の `placeholder_mappings/uni.yml` になります。新規設定は空で作成し、SSCの設定をコピーしません。
- 登録後、管理画面に表示される配置先へ抽出Excelを配置し、プレースホルダ設定で同じ参照元DBを選んで定義します。WebUIからのファイルアップロードはありません。
- Dockerのstandard設定では、ホスト側の `storage/standard/access_exports/uni/` と `storage/standard/config/placeholder_mappings/uni.yml` に対応します。SSCの既存設定は `storage/standard/config/placeholder_mapping.yml` を維持し、コンテナ再作成後も保持されます。
- 既定のSSC方式では `ユニット構成.xlsx` または `unit_config.xlsx` が必要です。UNI方式では不要で、targetごとのブロック・ビル・クラスタ番号と命名規則から装置候補を生成し、抽出4表と照合します。
- UNI方式の設定は `storage/standard/config/case_doc_workflows/uni.yml`（`version: 1`、`mode: uni`、`definition_file: uni.xlsx`）に配置します。命名規則Excelは同じフォルダへ配置し、参照元DBの登録・抽出4表・プレースホルダ設定と一組で管理します。詳細は [UNI案件化・テストデータ](../../../docs/lab/poc_uni_access_export_test_data.md) を参照してください。
- 案件保存時に参照元DB名・識別子・抽出データ版と置換結果を保存します。後の抽出ファイル変更や参照元の名称変更・無効化では、保存済み案件の内容を置き換えません。参照元情報がない旧案件はSSC、抽出データ版は未記録として表示します。
- 識別子は登録後変更できません。追加DBを無効化すると新規参照から外れますが、既存案件は保持します。既存APIとの互換性のためSSCは無効化できません。
- 参照元一覧の取得時に管理テーブルを初期化し、既存の `sbc` を `ssc` に移行します。旧名称がSBCの場合のみSSCへ変更し、独自の名称は保持します。案件に明示された旧識別子・既定名も同じトランザクションで移行し、置換結果・データ版・実行記録・Excelは変更しません。移行は再実行可能で、両識別子が既に存在する場合は統合せず停止します。新規環境にはSSCメタデータだけを追加します。
- 旧standard配置からの移行では、DB・抽出ファイル・設定をバックアップし、APIを停止してから `access_exports/` 直下の既存抽出ファイルを `access_exports/ssc/` へ移動してAPIを再作成します。既存の `ssc/` がある場合は上書きせず、管理画面の配置先・ファイル数・置換結果を確認してください。親ディレクトリや旧フォルダを読むフォールバック、自動移動は行いません。参照元DB指定のない既存APIも `ssc/` を参照します。labの業務データはstandardへコピーしません。
