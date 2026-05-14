# SB4 プレースホルダ管理 MVP設計メモ

## 目的

案件CS生成で使用するプレースホルダを、開発者だけがコードで追加する方式から、運用担当者・利用者側でも段階的に追加できる方式へ移行する。

現時点では `apps/standard/backend/app/db/case_doc_repositories.py` にプレースホルダ名、取得元Excel、取得元カラムが定義されている。これは安全でテストしやすい一方、実運用ではプレースホルダ追加のたびに開発対応が必要になる。

MVPでは、まず設定ファイル方式を導入し、その後Web画面で参照できるところまでを目標にする。

## 結論

MVPでは、いきなり完全な画面管理方式にはしない。

まずは以下の 2.5 段階を目指す。

1. プレースホルダ対応表を設定ファイルで管理する
2. 生成APIが設定ファイルを読み込んで値を解決する
3. WebUIではプレースホルダ一覧・取得元・有効/無効状態を確認できる

追加・編集までWebUIで行う機能は次段階とする。

## 方式比較

| 方式 | 概要 | 利点 | 課題 | MVP採用 |
| --- | --- | --- | --- | --- |
| コード定義方式 | 開発者がPythonコードへ追加する | 安全、テストしやすい | 利用者が追加できない | 現状のみ |
| 設定ファイル方式 | YAML/JSONでプレースホルダ対応を管理する | 利用者・運用者が追加しやすい | 入力検証が必要 | 採用 |
| DB管理方式 | DBテーブルでプレースホルダ対応を管理する | Web画面管理と相性がよい | 実装量が増える | 後続候補 |
| Web画面管理方式 | WebUIから追加・編集・無効化する | 実運用に近い | 誤入力防止、履歴、権限が必要 | MVPでは一覧から |

## MVPの到達点

### 対応すること

- `placeholder_mapping.yml` を用意する
- プレースホルダ名、取得元ファイル、取得元カラム、装置種別、キー列を設定ファイルで管理する
- 案件CS生成時に、設定ファイルを読んで値を解決する
- 既存のコード定義済みプレースホルダを設定ファイルへ移す
- APIでプレースホルダ対応表一覧を返す
- WebUIでプレースホルダ対応表を一覧表示する
- 設定ファイルの内容に対して最低限の検証を行う

### MVPでは後回しにすること

- WebUIからの自由追加・自由編集
- 変更履歴管理
- ロール別権限管理
- 承認フロー
- 複雑な条件分岐式の画面編集
- Excelテンプレート内のプレースホルダ自動検出と自動登録

## 設定ファイル案

配置案:

```text
apps/standard/backend/app/config/placeholder_mapping.yml
```

構造案:

```yaml
version: 1
placeholders:
  - name: SBC_COMMAND_FLOATING_IP
    enabled: true
    scope: device
    device_type: SBC
    source_file: SBC.xlsx
    key_column: ホスト名
    value_column: コマンド用フローティングIPアドレス
    source_column: command_floating_ip
    description: TeraTerm接続先、コマンド欄で使用するIP

  - name: SBC_CALL_PROCESS_FLOATING_IP
    enabled: true
    scope: device
    device_type: SBC
    source_file: SBC.xlsx
    key_column: ホスト名
    value_column: 呼処理用フローティングIPアドレス
    source_column: call_process_floating_ip
    description: 呼処理確認向けIP。MVP仮定義。

  - name: LOGIN_USER
    enabled: true
    scope: common
    source_file: case_common_values.xlsx
    key_column: key
    key_value: LOGIN_USER
    value_column: value
    source_column: login_user
    description: ログインユーザー名
```

## 項目定義

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `name` | 必須 | Excelテンプレートで使うプレースホルダ名。例: `SBC_COMMAND_FLOATING_IP` |
| `enabled` | 必須 | 生成時に使うかどうか |
| `scope` | 必須 | `device` または `common` |
| `device_type` | `device` の場合必須 | `SBC`, `GUI`, `HFS` など |
| `source_file` | 必須 | 値を取得するExcelファイル名 |
| `key_column` | 必須 | 行を特定するキー列。装置系では基本 `ホスト名` |
| `key_value` | 任意 | 共通値など、固定キーで引く場合に使用 |
| `value_column` | 必須 | 実際に取得する値の列名 |
| `source_column` | 任意 | 監査表示用・内部表示用の列名 |
| `description` | 任意 | 画面表示・運用メモ用の説明 |

## 値解決の考え方

### device scope

装置に紐づく値を取得する。

```text
ユニット構成.xlsx
  -> 対象スロットを選択
  -> 対象ホスト名を決定
  -> source_file の key_column = 対象ホスト名 の行を探す
  -> value_column の値を取得
```

例:

```text
対象スロット: SBC_CL2_1
対象ホスト名: sbc-demo-a-cl2-1
source_file: SBC.xlsx
key_column: ホスト名
value_column: NTP向けフローティングIPアドレス
```

### common scope

装置に依存しない共通値を取得する。

```text
source_file の key_column = key_value の行を探す
  -> value_column の値を取得
```

例:

```text
source_file: case_common_values.xlsx
key_column: key
key_value: LOGIN_USER
value_column: value
```

## API案

### 一覧取得

```http
GET /api/v1/case-docs/placeholders
```

用途:

- WebUIでプレースホルダ対応表を表示する
- 有効/無効、取得元ファイル、取得元列を確認する

レスポンス例:

```json
{
  "result": "success",
  "data": {
    "items": [
      {
        "name": "SBC_COMMAND_FLOATING_IP",
        "enabled": true,
        "scope": "device",
        "device_type": "SBC",
        "source_file": "SBC.xlsx",
        "key_column": "ホスト名",
        "value_column": "コマンド用フローティングIPアドレス",
        "description": "TeraTerm接続先、コマンド欄で使用するIP"
      }
    ]
  }
}
```

### 検証API

```http
POST /api/v1/case-docs/placeholders/validate
```

用途:

- 設定ファイルに書かれた `source_file` が存在するか確認する
- `key_column` / `value_column` が実際のExcel列に存在するか確認する
- 同じ `name` が重複していないか確認する

## WebUI案

### MVPで作る画面

サイドバーまたは案件化画面配下に、以下を追加する。

```text
プレースホルダ管理
```

最初のMVPでは、編集ではなく一覧表示を中心にする。

表示項目:

- プレースホルダ名
- 有効/無効
- scope
- 装置種別
- 取得元Excel
- キー列
- 値列
- 説明
- 検証状態

### MVP後に追加する画面操作

- 有効/無効の切り替え
- 説明の編集
- プレースホルダ追加
- 取得元Excel・列名のプルダウン選択
- 保存前検証

## 検証ルール

最低限、以下を検証する。

- `name` が空でない
- `name` が重複していない
- `name` が命名規則に合っている
- `source_file` が存在する
- `key_column` が存在する
- `value_column` が存在する
- `scope=device` の場合は `device_type` がある
- `enabled=true` のプレースホルダだけ生成に使う

命名規則:

```text
英大文字 + 数字 + アンダースコアのみ
例: SBC_NTP_FLOATING_IP
```

## 実装ステップ

### Step 1: 設定ファイルを追加する

- `placeholder_mapping.yml` を作成する
- 既存のSBC/TTS/LOGIN_USER系プレースホルダを移す
- 既存コード定義と同じ結果になるようにする

### Step 2: 設定ファイル読み込みRepositoryを作る

- `PlaceholderMappingRepository` を追加する
- YAMLを読み込む
- Pydanticまたは独自バリデーションで検証する

### Step 3: 既存の値解決処理を設定ファイル参照へ寄せる

- `SBC_PLACEHOLDER_DEFINITIONS` の固定定義を段階的に置き換える
- `source_file` ごとにExcelを読み込む
- `key_column` と対象ホスト名で行を解決する
- `value_column` から値を取得する

### Step 4: APIを追加する

- `GET /api/v1/case-docs/placeholders`
- `POST /api/v1/case-docs/placeholders/validate`

### Step 5: WebUIで一覧表示する

- 案件化画面またはサイドバーに導線を追加する
- 一覧表で設定内容を確認できるようにする
- 検証エラーがあれば画面で見えるようにする

## リスクと対策

| リスク | 対策 |
| --- | --- |
| 存在しない列名を設定してしまう | 起動時または検証APIで検出する |
| プレースホルダ名が重複する | 設定読み込み時にエラーにする |
| Excelテンプレート側の表記ゆれ | 命名規則を固定し、旧名はaliasで吸収する |
| 設定変更で生成結果が変わる | 解決値シートに取得元ファイル・列名・ホスト名を残す |
| ユーザーが壊れた設定を保存する | MVPではWeb編集を後回しにし、まず設定ファイル運用にする |

## MVPでの判断

MVPでは、プレースホルダをユーザーが完全に画面から自由編集できる状態までは狙わない。

ただし、設定ファイル方式に移すことで、開発者がPythonコードを変更しなくてもプレースホルダを追加できる土台を作る。

WebUIはまず一覧・検証結果の確認までとし、実運用で追加頻度や編集パターンが見えてから編集機能を拡張する。

## MVP採用方針: YAML編集API + 画面編集

2026-05-14時点では、プレースホルダ管理のMVP方針として「YAML編集API + 画面編集、削除なし」を採用する。

### 採用する理由

- 現在の `placeholder_mapping.yml` を活かせるため、DBテーブル化よりも実装範囲を小さくできる。
- 開発者がコードを変更しなくても、運用側でプレースホルダを追加・更新できる余地を作れる。
- 本格運用前に、どの項目が本当に必要かを画面操作を通じて検証できる。
- 物理削除を行わず、有効/無効で制御することで、テンプレート内で利用中のプレースホルダを誤って消すリスクを下げられる。

### MVPでできること

- プレースホルダを新規追加する。
- 既存プレースホルダを編集する。
- 有効/無効を切り替える。
- 一覧画面で定義内容を確認する。
- 保存前に最低限の入力検証を行う。

### MVPでやらないこと

- プレースホルダの物理削除。
- DBテーブルでの管理。
- 変更履歴管理。
- 承認フロー。
- 複数人同時編集に対する厳密な競合制御。
- Excelテンプレート内の利用箇所を自動解析しての影響範囲表示。

### 編集対象の項目

| 項目 | 編集方針 | 補足 |
| --- | --- | --- |
| `name` | 入力 | 命名規則に合うことを検証する。既存名との重複は禁止する。 |
| `enabled` | 選択 | 有効/無効の切替。削除の代替手段として使う。 |
| `scope` | 選択 | `device` または `common`。画面表示名は「値の単位」とする案が分かりやすい。 |
| `device_type` | 選択 | `scope=device` の場合に使用する。SBC/GUI/HFS/HSSなど。 |
| `source_file` | 選択または入力 | Access抽出ファイル名。将来的には配置済みファイルから選択できるようにする。 |
| `key_column` | 選択または入力 | 行を特定するための列。装置別では基本的にホスト名列を使う。 |
| `value_column` | 選択または入力 | 実際に取得する値の列。 |
| `source_column` | 入力 | 内部表示や監査用の安定した列名。 |
| `key_value` | 入力 | `scope=common` の場合に利用する固定キー。 |
| `description` | 入力 | 運用者が用途を判断するための説明。 |

### API方針

MVPでは、YAMLファイルを読み書きするAPIを追加する。

```http
GET /api/v1/case-docs/placeholders
POST /api/v1/case-docs/placeholders
PUT /api/v1/case-docs/placeholders/{name}
PATCH /api/v1/case-docs/placeholders/{name}/enabled
POST /api/v1/case-docs/placeholders/validate
```

削除APIは作らない。不要になった定義は `enabled=false` にする。

### 保存時の検証

保存時には最低限、以下を検証する。

- `name` が空ではない。
- `name` が命名規則に合っている。
- 新規追加時に `name` が重複していない。
- `scope` が `device` または `common` である。
- `scope=device` の場合、`device_type` が指定されている。
- `scope=common` の場合、必要に応じて `key_value` が指定されている。
- `source_file` が空ではない。
- `key_column` が空ではない。
- `value_column` が空ではない。
- `enabled=true` にする場合、可能であれば参照先Excelファイルと列の存在を検証する。

### WebUI方針

一覧画面に以下の操作を追加する。

- 「追加」ボタン。
- 各行の「編集」ボタン。
- 各行の「有効化/無効化」操作。

編集フォームは、最初はモーダルまたは同ページ内パネルでよい。削除ボタンは置かない。

運用者が誤って生成処理を壊さないよう、`scope`、`device_type`、`enabled` は自由入力ではなく選択式にする。

### 将来の移行先

MVPで運用パターンが見えたら、次の段階でDBテーブル管理へ移行する。

DB管理へ移行する場合は、以下を追加検討する。

- 変更履歴。
- 更新者/更新日時。
- 承認フロー。
- テンプレート内の利用箇所管理。
- ロール別権限。
- 同時編集時の競合制御。
