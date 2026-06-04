# AccessDB Excel抽出CLI

AccessDBから案件CS生成用のExcelファイル群を抽出するためのWindows向けCLIです。

## 前提

- Windows PCで実行する
- Access Database Engine / Access ODBC Driver が利用できる
- Python 3.11 以降を想定

## セットアップ

```powershell
cd tools\access_export
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 実行例

```powershell
python export_accessdb_to_excel.py `
  --db "C:\path\to\source.accdb" `
  --out "C:\Users\clove\OneDrive\ドキュメント\mvp-root\storage\standard\access_exports"
```

## バッチ実行

`export_accessdb_to_excel.bat` 内の `ACCESS_DB_PATH` と `OUTPUT_DIR` を環境に合わせて変更してから実行します。

## 設定ファイル

抽出対象は `access_export_config.yml` で管理します。

```yaml
exports:
  - name: unit_config
    access_table: ユニット構成
    output_file: ユニット構成.xlsx
    sheet_name: ユニット構成
```

`access_table` にはAccessDB上のテーブル名を指定します。
`output_file` には出力するExcelファイル名を指定します。

## 出力

指定した出力先に以下を作成します。

- 抽出対象の `.xlsx`
- `export_manifest.json`

同名ファイルが存在する場合は、既定では `backup\yyyyMMdd_HHmmss` に退避してから上書きします。

