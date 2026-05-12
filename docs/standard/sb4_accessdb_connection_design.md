# SB4 AccessDB 実データ接続設計メモ

## 1. 目的

案件CS生成で使用するユニット構成、装置マスタ、共通値を、現在の seed データから実データへ切り替えるための接続方針を整理する。

対象は主に以下の値である。

- 都道府県、ビル、FSクラスタ、ブロックなどのユニット構成検索条件
- ユニット構成に紐づく装置ホスト名
- ホスト名をキーに取得する装置マスタ値
- `LOGIN_USER` などの案件CS共通値
- プレースホルダへ反映する最終解決値

## 2. 結論

Sprint4 時点では、AccessDB へ Docker コンテナから直接接続する方式は第一候補にしない。

代わりに、以下の段階構成にする。

1. AccessDB または Access由来Excel/CSV から、必要テーブルをエクスポートする
2. エクスポートファイルを `storage/standard/access_exports` 配下に配置する
3. backend 側でエクスポートファイルを読み取り、案件CS用マスタとして解決する
4. 安定後、PostgreSQL に案件CS用マスタテーブルを作り、エクスポートデータを取り込む
5. 最終的に、AccessDB からの同期処理を運用化する

この方針により、Docker / Linux / テストサーバー上でも同じ実装で動かせる。

## 3. AccessDB 直接接続を第一候補にしない理由

AccessDB (`.mdb` / `.accdb`) は、基本的に Windows の Access Database Engine / ODBC ドライバに依存する。
現在の standard API は Docker 上の Linux コンテナで動作しているため、以下の問題がある。

- Linux コンテナから AccessDB へ直接接続する構成は再現性が低い
- Access Database Engine は Windows 前提で、Docker/Linux に載せにくい
- テストサーバーでも同じ接続方式を保証しづらい
- CI や他PC引き継ぎ時に環境差分が大きくなる
- AccessDB ファイルを直接参照すると、ファイルロックや同時利用の扱いが難しくなる

そのため、MVP では「AccessDB を直接読む」のではなく、「AccessDB 由来のデータを標準化して取り込む」方式にする。

## 4. 推奨構成

### 4.1 フェーズ1: seed / エクスポートファイル読み取り

現在の `_UNIT_CONFIGS` や `_DEVICE_VALUES_BY_HOST_NAME` は seed データとして残す。
その上で、AccessDB から抽出した Excel / CSV を読み取れる層を追加する。

想定配置:

```text
storage/standard/access_exports/
  .gitignore
  unit_config.xlsx
  SBC.xlsx
  GUI.xlsx
  FS.xlsx
  HFS.xlsx
  HSS.xlsx
  MSW.xlsx
  RAID.xlsx
  SCCE.xlsx
  case_common_values.xlsx または case_common_values.csv
```

実データは環境依存・機密情報を含む可能性があるため、`storage/standard/access_exports/.gitignore` でGit管理対象外にする。

API は直接ファイル形式に依存せず、Repository 層から以下の意味データを受け取る。

- unit configs
- host assignments
- device values by host name
- common values

### 4.2 フェーズ2: PostgreSQL 取り込み

エクスポートファイル読み取りが安定したら、PostgreSQL に案件CS用マスタを持たせる。

候補テーブル:

```text
case_unit_configs
case_host_assignments
case_device_values
case_common_values
case_import_runs
case_import_errors
```

目的:

- 画面/APIの検索を高速化する
- 取り込み履歴を残す
- AccessDB 側の列名変更や欠損を検知しやすくする
- テストサーバーで同じデータを再現しやすくする

### 4.3 フェーズ3: AccessDB 同期処理

運用として AccessDB が正本になる場合、Windows 側で同期処理を用意する。

候補:

- AccessDB から Excel / CSV を出力する手順を運用化する
- Windows タスクスケジューラで定期エクスポートする
- 生成したファイルを所定フォルダへ配置する
- backend の import API または CLI で PostgreSQL に取り込む

## 5. Repository 境界

`apps/standard/backend/app/db/case_docs.py` は、将来的に以下のような境界へ分ける。

```text
case_docs.py
  public API helper

case_doc_repositories.py
  CaseDocMasterRepository interface
  SeedCaseDocMasterRepository
  ExportFileCaseDocMasterRepository
  PostgresCaseDocMasterRepository
```

切り替えは環境変数で行う。

```text
CASE_DOC_MASTER_SOURCE=seed
CASE_DOC_ACCESS_EXPORT_DIR=/app/storage/access_exports
CASE_DOC_IMPORT_STRICT=true
```

`CASE_DOC_MASTER_SOURCE` の候補:

| 値 | 意味 |
| --- | --- |
| `seed` | 現在の固定seedを使用する |
| `export_file` | Access由来Excel/CSVを読む |
| `postgres` | PostgreSQLに取り込んだ案件CS用マスタを読む |

## 6. データ解決ルール

### 6.1 ユニット構成

ユニット構成は、案件化画面で選択する以下の条件から 1 件に絞る。

- 都道府県
- ビル
- FSクラスタ名
- ブロック
- unit_config_id

ユニット構成が複数件に解決される場合は、画面で選択させる。
ユニット構成が 0 件の場合は、案件CS生成を止める。

### 6.2 ホスト名

ユニット構成から `SBC_CL1_0` などのスロットを取得し、対象スロットのホスト名を確定する。
ホスト名は後続値を解決するキーとして扱う。

### 6.3 装置マスタ値

装置マスタは `host_name` をキーに引く。

例:

| 装置種別 | キー | 取得値 |
| --- | --- | --- |
| SBC | ホスト名 | コマンド用フローティングIP、TTS情報、CL_ID など |
| GUI | ホスト名 | EMSコマンド用IP、TTS情報、AGENT_NO など |
| FS | ホスト名 | eth系アドレス、コマンド用IP など |

### 6.4 共通値

`LOGIN_USER` など、案件や装置に依存しない値は `case_common_values` として扱う。
画面で手入力させず、共通値マスタから解決する。

現在の例:

| key | source_table | source_column | value |
| --- | --- | --- | --- |
| `LOGIN_USER` | `case_common_values` | `login_user` | `cs-operator` |

## 7. 取り込み時の検証

Access由来データを取り込むときは、最低限以下を検証する。

- 必須ファイルが存在すること
- 必須列が存在すること
- ユニット構成の主キー候補が重複していないこと
- ホスト名が空でないこと
- 装置マスタ側のホスト名が重複していないこと
- ユニット構成で参照しているホスト名が装置マスタに存在すること
- `LOGIN_USER` など必須共通値が存在すること
- 文字コードが UTF-8 / Shift_JIS / Excel 内部文字列として正しく読めること

検証エラーは、案件CS生成時ではなく、取り込み時に検出する。

## 8. API / CLI 方針

### 8.1 MVP で優先するもの

まずは backend 内部の読み取り層を切り替えられるようにする。
画面からのアップロードや管理画面は後回しでよい。

### 8.2 将来候補

```text
POST /api/v1/case-docs/imports/access-export
GET  /api/v1/case-docs/imports
GET  /api/v1/case-docs/imports/{import_id}/errors
```

CLI 候補:

```powershell
python -m app.tools.import_case_doc_masters --input /app/storage/access_exports
```

## 9. 実装順序

1. `CaseDocMasterRepository` 相当の境界を作る（実装済み）
2. 現在の seed データを `SeedCaseDocMasterRepository` に移す（実装済み）
3. `CASE_DOC_MASTER_SOURCE=seed` で今と同じ動作を維持する（実装済み）
4. `storage/standard/access_exports` の配置ルールを追加する（実装済み）
5. Excel / CSV 読み取りの `ExportFileCaseDocMasterRepository` を追加する（初期実装済み: `unit_config.xlsx`, `SBC.xlsx`, `case_common_values.xlsx/csv`）
6. 必須列検証を追加する（初期実装済み: 必須列値が見つからない場合はエラー）
7. 既存の `/case-docs` 画面と生成APIを export_file で動作確認する
8. 必要になった時点で PostgreSQL 取り込みに進む

## 10. 今回の判断

次の実装では、いきなり AccessDB へ直接接続しない。
まずは repository 境界を作り、現在の seed 実装を差し替え可能な形に整理する。

これにより、AccessDB 実接続、Excel/CSV取り込み、PostgreSQL化のどれに進んでも、APIや画面側の変更を最小にできる。