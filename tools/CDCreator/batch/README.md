# 案件CS・CDCreator連携バッチ

WebUIから保存した案件CSに対して、項番付与とCDCreator実行を連続して行うWindows向けツールです。

## 実行内容

1. 案件CS内のCSシートへ `AssignNumbersOnActiveSheet` を実行
2. `runCdCreator` を起動
3. ユーザーがCD化するCSシートと出力先を選択
4. CD用Excelが生成された場合だけ、採番済み案件CSを保存

案件CSとCD用Excelは同じフォルダへ格納します。

## 前提条件

- Windows 10またはWindows 11
- Excelデスクトップアプリ
- Windows PowerShell 5.1以降
- CDCreatorと項番付与マクロを組み込んだ案件CS (`.xlsm`)
- 案件CSが書き込み可能で、Excelで開かれていないこと

Pythonや追加ライブラリは不要です。

## 推奨作業フォルダ

```text
C:\ProcedureDB\case_docs\
```

Webブラウザから保存した案件CSは、マクロがブロックされる場合があります。社内管理された「信頼できる場所」を作業フォルダに設定する運用を推奨します。

マクロセキュリティをPC全体で無効化しないでください。

## 基本操作

1. WebUIの案件化画面で「保存先を選んで案件CSを生成」を押す
2. 作業フォルダへ案件CSを保存する
3. 案件CSを `run_case_doc_cdcreator.bat` へドラッグ＆ドロップする
4. Excel画面が開くまで待つ
5. CS選択画面が表示された場合、CD化するCSシートを1つ以上選択して「OK」を押す
6. 出力先確認で「はい（このブックと同じフォルダ）」を押す
7. CDCreatorの完了メッセージを確認して「OK」を押す
8. バッチ画面に「処理が完了しました」と表示されることを確認する

バッチをダブルクリックした場合は、案件CSのファイル選択画面が開きます。

## 出力

入力した案件CSと同じフォルダに次が残ります。

```text
案件CS.xlsm
app修正前_*_CD_yyyymmdd.xlsx
```

CDCreatorが同名候補を検出した場合、既存ファイルを上書きせず別名で保存します。

## キャンセル時

次の操作をキャンセルした場合、案件CSの採番結果は保存しません。

- 案件CSのファイル選択
- CDCreatorのCSシート選択
- CDCreatorの出力先選択

出力先として別のフォルダを選択した場合、バッチは同一フォルダへの生成を確認できないため、案件CSを保存せずキャンセル扱いにします。

## 入力検証だけ行う

Excelを起動せず、形式とVBAプロジェクトの有無だけ確認できます。

```powershell
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass `
  -File .\run_case_doc_cdcreator.ps1 `
  -CaseDocPath "C:\ProcedureDB\case_docs\case-doc-example.xlsm" `
  -ValidateOnly
```

## ログ

実行ログは次へ保存します。

```text
tools\CDCreator\batch\logs\case_doc_cdcreator_yyyyMMdd_HHmmss.log
```

ログには入力ファイル、採番対象シート、生成されたCD用Excel、エラー内容を記録します。案件固有のコマンド内容は記録しません。

## 主なエラー

### 案件CSを開けない

- Excelで同じ案件CSを開いていないか確認する
- 読み取り専用になっていないか確認する
- 同じ案件CSのバッチを複数起動していないか確認する

### マクロを実行できない

- ファイル上部に「コンテンツの有効化」が表示されていないか確認する
- 作業フォルダがExcelの「信頼できる場所」になっているか確認する
- ファイルのプロパティに「許可する」または「ブロック解除」がないか確認する

### CD用Excelが見つからない

- 出力先確認で「はい」を選んだか確認する
- CDCreatorのログシートを確認する
- シート名に `CS` が含まれているか確認する

## 終了コード

| コード | 意味 |
| --- | --- |
| `0` | 成功 |
| `1` | エラー |
| `2` | キャンセルまたは同一フォルダへの出力なし |

## 制約

- 一度に処理できる案件CSは1ファイル
- Excelフォームの操作はユーザーが行う
- WebUIからバッチを自動起動しない
- サーバー上では実行しない
