# SB4 AccessDB Excel抽出機能 設計メモ

## 1. 目的

AccessDB に格納されている案件CS生成用マスタ情報を、MVP環境で利用できる Excel ファイル群として抽出する。

現在のMVPでは、案件CS生成側は `storage/standard/access_exports` 配下の Excel ファイルを読み取る構成になっている。
そのため、本機能では AccessDB から必要テーブルを抽出し、既存の `export_file` 読み取り機能で利用できる形にそろえる。

## 2. 前提

- AccessDB は会社PC上に存在する。
- 会社PCはセキュアなPCであり、Webサーバーや FastAPI を常駐させられるかは未確定。
- AccessDB への接続は Windows の ODBC / Access Database Engine を利用する想定。
- MVP本体の standard backend は Docker / Linux 上で動作する。
- Docker / Linux コンテナから AccessDB へ直接接続する構成は採用しない。

## 3. 結論

MVPでは、最初から FastAPI の抽出APIを作らず、会社PC上で動作する CLI / バッチ を先に実装する。

```text
会社PC上のAccessDB
  ↓ ODBC
AccessDB抽出CLI / バッチ
  ↓
Excelファイル群
  ↓
storage/standard/access_exports
  ↓
既存のexport_file読み取り
  ↓
案件CS生成
```

FastAPI化は、会社PC上でWebサーバー起動が許可されること、認証・アクセス制御・運用管理の方針が固まった後に検討する。

## 4. FastAPIを最初に採用しない理由

会社PC上で FastAPI を動かす場合、以下の確認が必要になる。

- Webサーバーを起動してよいか
- ポート開放が可能か
- 社内ネットワークからアクセス可能か
- 認証・認可をどうするか
- AccessDBファイルパスを外部入力させてよいか
- 常駐プロセスやログ管理をどうするか
- セキュリティレビューが必要か

これらは実装そのものより運用・セキュリティ面の調整が大きい。

一方、CLI / バッチであれば、会社PC上で手動またはタスクスケジューラから実行できるため、MVPとして導入しやすい。

## 5. 実装方針

### 5.1 抽出方式

Python CLI と Windows バッチを用意する。

想定ファイル:

```text
tools/access_export/
  export_accessdb_to_excel.py
  export_accessdb_to_excel.bat
  access_export_config.yml
  README.md
```

CLI は以下を受け取る。

```powershell
python export_accessdb_to_excel.py ^
  --db "C:\path\to\source.accdb" ^
  --out "C:\path\to\access_exports"
```

バッチは、利用者がダブルクリックまたは固定コマンドで実行できるようにする。

### 5.2 接続方式

AccessDB への接続は ODBC を使用する。

候補ライブラリ:

- `pyodbc`
- `pandas`
- `openpyxl`

役割:

- `pyodbc`: AccessDBへの接続とSQL実行
- `pandas`: テーブルデータのDataFrame化
- `openpyxl`: Excel出力

ただし、会社PCへのライブラリ導入制約が強い場合は、`pyodbc + openpyxl` のみで実装する。

### 5.3 出力形式

出力形式は `.xlsx` とする。

出力先は既存方針に合わせる。

```text
storage/standard/access_exports/
  ユニット構成.xlsx
  SBC.xlsx
  GUI.xlsx
  FS.xlsx
  HFS.xlsx
  HSS.xlsx
  MSW.xlsx
  RAID.xlsx
  SCCE.xlsx
  case_common_values.xlsx
```

出力ファイルはGit管理しない。

## 6. 対象テーブル

最初のMVP対象は、現在の案件CS生成で実際に使っている範囲に絞る。

### 6.1 初期対象

| 出力ファイル | 用途 |
| --- | --- |
| `ユニット構成.xlsx` | 都道府県、ビル、ユニット構成、対象装置の選択 |
| `SBC.xlsx` | SBC装置に紐づくホスト名、IP、TTS系値の解決 |
| `case_common_values.xlsx` | ログインユーザーなど共通値の解決 |

### 6.2 次段階対象

| 出力ファイル | 用途 |
| --- | --- |
| `GUI.xlsx` | GUI装置向けの値解決 |
| `FS.xlsx` | FS装置向けの値解決 |
| `HFS.xlsx` | HFS装置向けの値解決 |
| `HSS.xlsx` | HSS装置向けの値解決 |
| `MSW.xlsx` | MSW装置向けの値解決 |
| `RAID.xlsx` | RAID装置向けの値解決 |
| `SCCE.xlsx` | SCCE装置向けの値解決 |

## 7. 設定ファイル

AccessDB上のテーブル名や出力ファイル名は、コード固定にしすぎず設定ファイルへ寄せる。

例:

```yaml
exports:
  - name: unit_config
    access_table: ユニット構成
    output_file: ユニット構成.xlsx
  - name: sbc
    access_table: SBC
    output_file: SBC.xlsx
  - name: common_values
    access_table: case_common_values
    output_file: case_common_values.xlsx
```

AccessDB側のテーブル名が環境によって異なる場合は、この設定で吸収する。

## 8. 抽出時の検証

CLI実行時に、最低限以下を検証する。

- AccessDBファイルが存在すること
- ODBC接続できること
- 対象テーブルが存在すること
- 抽出件数が0件でないこと
- 出力先フォルダへ書き込み可能であること
- Excelファイルを書き出せること

可能であれば、次の検証も追加する。

- 必須列が存在すること
- ホスト名が空でないこと
- ユニット構成から参照されるホスト名が、装置マスタ側に存在すること
- 同一キーの重複がないこと

## 9. 出力時の運用

### 9.1 上書き方針

MVPでは、同名ファイルは上書きする。

ただし、事故防止のため以下を検討する。

- 出力前に `backup` フォルダへ退避
- 実行日時付きフォルダにもコピーを残す
- `export_manifest.json` に抽出日時・件数を保存する

例:

```text
storage/standard/access_exports/
  ユニット構成.xlsx
  SBC.xlsx
  case_common_values.xlsx
  export_manifest.json
  backup/
    20260528_153000/
      ユニット構成.xlsx
      SBC.xlsx
```

### 9.2 ログ

抽出結果はログとして残す。

候補:

```text
logs/standard/access_export/
  access_export_20260528_153000.log
```

ログに残す内容:

- 実行日時
- AccessDBパス
- 出力先
- 対象テーブル
- 出力ファイル
- 件数
- エラー内容

## 10. MVP本体側の確認API

抽出処理自体は会社PC上のCLI / バッチで行う。

一方、MVP本体側には、抽出済みExcelが使える状態か確認するAPIを追加する。

候補:

```text
GET /api/v1/case-docs/access-exports/status
```

返却例:

```json
{
  "export_dir": "storage/standard/access_exports",
  "files": [
    {
      "name": "ユニット構成.xlsx",
      "exists": true,
      "row_count": 12,
      "updated_at": "2026-05-28T15:30:00+09:00"
    },
    {
      "name": "SBC.xlsx",
      "exists": true,
      "row_count": 48,
      "updated_at": "2026-05-28T15:30:00+09:00"
    }
  ],
  "usable": true
}
```

このAPIは、AccessDBへは接続しない。
あくまで `storage/standard/access_exports` 配下のExcelが揃っているかを確認する。

## 11. 将来のAPI化

会社PC上でWebサーバー起動が許可された場合、CLI処理を流用してAPI化できる。

候補:

```text
POST /access-db/exports
GET  /access-db/exports/latest
GET  /access-db/exports/{export_id}
```

ただし、この段階では以下の設計が必要になる。

- 認証
- 実行権限
- AccessDBパスの固定化または入力制限
- 二重実行防止
- 実行ログの保管
- エラー通知
- ネットワーク制御

## 12. 実装順序

1. 設定ファイル案を作る
2. CLIの最小実装を作る
3. `ユニット構成.xlsx` / `SBC.xlsx` / `case_common_values.xlsx` を出力する
4. 出力ファイルを `storage/standard/access_exports` に配置する
5. 既存 `/case-docs` 画面で読み取れることを確認する
6. 抽出結果のログとmanifestを追加する
7. Windowsバッチを追加する
8. MVP本体側に抽出Excel状態確認APIを追加する
9. 必要に応じて対象テーブルを増やす

## 13. 未確定事項

- 会社PCに Python を導入できるか
- `pyodbc` を導入できるか
- Access Database Engine / ODBC Driver が利用できるか
- AccessDB の正確なファイルパス
- AccessDB の対象テーブル名
- 抽出対象テーブルの主キーまたは一意キー
- 抽出ファイルをMVP環境へどう運ぶか
- 手動実行か、タスクスケジューラ実行か

## 14. 判断

MVPでは、AccessDB抽出機能は以下の形で進める。

- 抽出処理は会社PC上の CLI / バッチで実行する
- standard backend は AccessDB に直接接続しない
- standard backend は抽出済みExcelファイルを読み取る
- API化は会社PC側の制約確認後に判断する

