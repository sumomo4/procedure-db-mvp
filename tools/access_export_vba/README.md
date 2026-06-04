# AccessDB Excel抽出 VBAサンプル

AccessDBから案件CS生成用のExcelファイルを出力するためのVBAサンプルです。

## ファイル

- `ExportProcedureDbAccessTables.bas`

## 使い方

1. AccessDBを開く
2. `Alt + F11` でVBAエディタを開く
3. `ファイル > ファイルのインポート` から `ExportProcedureDbAccessTables.bas` を取り込む
4. 必要に応じて `DEFAULT_OUTPUT_DIR` を変更する
5. `ExportProcedureDbAccessTables` を実行する

## 初期出力対象

- `ユニット構成` -> `ユニット構成.xlsx`
- `SBC` -> `SBC.xlsx`
- `case_common_values` -> `case_common_values.xlsx`

AccessDB上のオブジェクト名が異なる場合は、VBA内の `GetExportDefinitions` を修正してください。

## 出力先

既定値:

```text
C:\ProcedureDbExports\access_exports
```

同名ファイルが存在する場合は、`backup\yyyyMMdd_HHmmss` に退避してから上書きします。

