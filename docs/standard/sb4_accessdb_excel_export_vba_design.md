# SB4 AccessDB Excel抽出 VBAマクロ案 設計メモ

## 1. 目的

AccessDB に格納されている案件CS生成用マスタ情報を、MVP環境で利用できる Excel ファイル群として抽出する。

当初は Python CLI / バッチでの抽出を検討したが、AccessDB が会社のセキュアPCにあり、Python導入や外部ライブラリ導入が難しい可能性がある。
そのため、MVPでは Access 標準機能を使った VBAマクロによるExcel出力を第一候補とする。

## 2. 結論

MVPでは、会社PC上の AccessDB に VBAモジュールを追加し、対象テーブルまたはクエリを `.xlsx` として出力する。

```text
AccessDB
  ↓ VBA / DoCmd.TransferSpreadsheet
Excelファイル群
  ↓
storage/standard/access_exports
  ↓
既存 export_file 読み取り
  ↓
案件CS生成
```

Python CLI は補助案として残すが、関係者レビュー後の実運用寄せでは VBAマクロ案を優先する。

## 3. VBAマクロ案を優先する理由

- 会社PCにPythonを追加導入しなくてよい
- `pyodbc` や `openpyxl` などの外部ライブラリ導入が不要
- AccessDBを開ける環境であれば実行しやすい
- Access標準の `DoCmd.TransferSpreadsheet` でExcel出力できる
- セキュアPC上でWebサーバーやAPIを起動する必要がない
- 一般ユーザーはこれまで通りWebUIを使うだけでよい

## 4. 役割分担

### 4.1 AccessDB側

AccessDB側では、必要なテーブルまたはクエリをExcelとして出力する。

担当:

- AccessDBを管理できる担当者
- AccessDBが置かれている会社PC

### 4.2 MVP側

MVP側では、出力済みExcelを読み取る。

担当:

- standard backend
- 既存の `ExportFileCaseDocMasterRepository`

MVP側は AccessDB に直接接続しない。

## 5. 出力対象

### 5.1 初期対象

まずは現在の案件CS生成で使っているファイルに絞る。

| Access側オブジェクト | 出力ファイル | 用途 |
| --- | --- | --- |
| `ユニット構成` | `ユニット構成.xlsx` | 都道府県、ビル、ユニット構成、対象装置の選択 |
| `SBC` | `SBC.xlsx` | SBC装置に紐づくホスト名、IP、TTS系値の解決 |
| `case_common_values` | `case_common_values.xlsx` | ログインユーザーなど共通値の解決 |

AccessDB上に `case_common_values` が存在しない場合は、Access側にクエリまたはテーブルを用意する。

### 5.2 次段階対象

必要に応じて以下を追加する。

| Access側オブジェクト | 出力ファイル |
| --- | --- |
| `GUI` | `GUI.xlsx` |
| `FS` | `FS.xlsx` |
| `HFS` | `HFS.xlsx` |
| `HSS` | `HSS.xlsx` |
| `MSW` | `MSW.xlsx` |
| `RAID` | `RAID.xlsx` |
| `SCCE` | `SCCE.xlsx` |

## 6. 出力先

AccessDB本体と同じフォルダには、抽出ツールや出力ファイルを混在させない。

推奨:

```text
C:\ProcedureDbExports\access_exports\
  ユニット構成.xlsx
  SBC.xlsx
  case_common_values.xlsx
  export_manifest.json
  backup\
```

MVP環境へ反映する場合は、この出力フォルダのExcelファイルを以下へ配置する。

```text
storage/standard/access_exports/
```

## 7. バックアップ方針

同名ファイルが既に存在する場合は、上書き前にバックアップする。

例:

```text
C:\ProcedureDbExports\access_exports\backup\20260528_153000\
  ユニット構成.xlsx
  SBC.xlsx
  case_common_values.xlsx
  export_manifest.json
```

MVPでは、バックアップはローカルフォルダ内に残す。
世代管理や自動削除は次段階で検討する。

## 8. manifest

抽出後に `export_manifest.json` を出力する。

目的:

- いつ抽出したか分かるようにする
- どのAccessオブジェクトから出力したか分かるようにする
- 件数を確認できるようにする
- 後続の確認APIで読み取れる余地を残す

例:

```json
{
  "exported_at": "2026-05-28 15:30:00",
  "exports": [
    {
      "name": "unit_config",
      "source": "ユニット構成",
      "output_file": "ユニット構成.xlsx",
      "row_count": 12
    }
  ]
}
```

## 9. エラー時の扱い

以下の場合は処理を止め、メッセージを表示する。

- 出力先フォルダを作成できない
- 対象テーブルまたはクエリが存在しない
- Excel出力に失敗した
- 出力後のファイルが存在しない

1つでも失敗した場合は、担当者が気づけるように `MsgBox` でエラーを表示する。

## 10. サンプルVBA

サンプルは以下に置く。

```text
tools/access_export_vba/ExportProcedureDbAccessTables.bas
```

AccessDBのVBAエディタから標準モジュールとして取り込んで使用する。

実行入口:

```vb
ExportProcedureDbAccessTables
```

必要に応じて、出力先は以下の定数を変更する。

```vb
Private Const DEFAULT_OUTPUT_DIR As String = "C:\ProcedureDbExports\access_exports"
```

## 11. 今後の拡張

- 出力対象を画面で選択できるフォームを作る
- 出力先フォルダをファイルダイアログで選択する
- 抽出結果をAccess内のログテーブルに保存する
- Windowsタスクスケジューラで定期実行する
- MVP側に `GET /api/v1/case-docs/access-exports/status` を追加し、出力済みExcelの状態を確認できるようにする

## 12. 判断

MVPでは以下の方針で進める。

- AccessDBからExcelを出力する処理は VBAマクロで実装する
- Python CLIは補助案として残す
- MVP本体は引き続き抽出済みExcelを読み取る
- AccessDBへ直接接続するWeb APIは、会社PC側の制約確認後に検討する

