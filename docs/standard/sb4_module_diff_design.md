# モジュールdiff機能 方針メモ

## 1. 目的

モジュールの版差分を確認し、手順として何が変わったかを利用者が把握できるようにする。

このプロジェクトでは、単純な文字列diffよりも、行・確認事項・装置別コマンド・画像の単位で差分を見られることが重要になる。

## 2. MVPで扱う範囲

まずはモジュール単位の版比較を対象にする。

```text
モジュール v1 と v2 を比較する
```

原本diffは次段階とする。

## 2.1 モジュール版の作成方針

MVPでは、モジュール作成/更新はExcel投入のみで行う。

既存モジュールの修正版を作る場合は、既存モジュールの `module_key` を持つExcelを投入し、次の版を作成する。

```text
MOD-001 v1 published
MOD-001 の修正Excelを投入
MOD-001 v2 draft
```

MVPのルール:

- `module_key` が未指定の場合は新規モジュールとして自動採番し、`v1 draft` を作る
- `module_key` が既存の場合は `version_no + 1` の新規版を作る
- 新しい版の状態は必ず `draft`
- 既に `draft` 版がある場合は、誤投入防止のためエラーにする
- 承認/差戻し/保管は最終的に `module_version` 単位で扱う

## 3. API案

```text
GET /api/v1/modules/{module_id}/diff?from_version=1&to_version=2
```

### 3.1 主なレスポンス項目

```text
module_id
module_key
module_name
from_version
to_version
summary
rows[]
```

### 3.2 summary

```text
added_count
removed_count
changed_count
unchanged_count
```

### 3.3 rows

```text
status: added / removed / changed / unchanged
row_key
before
after
changed_fields[]
```

## 4. 比較単位

MVPでは `row_order` だけに依存せず、以下の順で行を照合する。

1. 空行は追加 / 削除として扱う
2. 非空行は fingerprint 完全一致で照合する
3. 残った非空行は `row_order` の前後5行を候補にして類似度で照合する
4. 類似度が `0.75` 以上なら同じ行の変更として扱う
5. 照合できない行は追加 / 削除として扱う

理由:

- 現在のDBでは行の永続的な業務キーを持っていない
- Excel上の手順は表示順が重要
- 空行や数行の追加で後続行がすべて変更扱いになることを避けたい
- まずは実装と利用者確認を優先する

将来的には、行ごとの安定IDや技術資料名 + 大中小番号などを使った比較へ広げる。

### 4.1 fingerprint

fingerprint は、以下を正規化して作る。

- `row_type`
- `tech_doc_text`
- `work_text`
- `expected_result`
- `time_text`
- `window_text`
- `p_text`
- `command_text`
- `device_entries`

正規化では、前後空白、全角/半角、連続空白、改行差を吸収する。

### 4.2 類似度

完全一致しなかった行について、Python標準の `difflib.SequenceMatcher` 相当の文字列類似度で照合する。

MVPのしきい値:

```text
0.75以上: 同じ行の変更
0.75未満: 追加 / 削除
```

候補範囲は `row_order` の前後5行に絞る。

## 5. 差分ステータス

| status | 意味 |
| --- | --- |
| `added` | 比較先にだけ存在する行 |
| `removed` | 比較元にだけ存在する行 |
| `changed` | 両方に存在するが内容が変わった行 |
| `unchanged` | 差分がない行 |

## 6. 比較対象フィールド

MVPでは以下を比較対象にする。

| フィールド | 内容 |
| --- | --- |
| `row_type` | 行種別 |
| `major_no` | 大番号 |
| `middle_no` | 中番号 |
| `minor_no` | 小番号 |
| `tech_doc_text` | 技術資料名 |
| `work_text` | 作業内容 |
| `indent_level` | インデント |
| `expected_result` | 確認事項 / 項目 |
| `time_text` | 共通の時刻 |
| `window_text` | 共通のwindow |
| `p_text` | 共通のP |
| `command_text` | 共通のコマンド |
| `device_entries` | 装置別の時刻/window/P/コマンド |
| `images` | 画像メタデータ |

## 7. 画像diffの扱い

MVPでは画像バイナリの差分比較までは行わない。

以下のメタデータを比較する。

- `image_key`
- `anchor_cell`
- `width_px`
- `height_px`
- `image_order`

画像の追加・削除・差し替えを検知できればMVPでは十分とする。

## 8. UI案

まずは差分一覧画面を作る。

表示方針:

- 追加行: 緑
- 削除行: 赤
- 変更行: 黄
- 変更なし: 通常表示

各行には以下を表示する。

- 行番号
- 差分ステータス
- 作業内容
- 確認事項
- 変更されたフィールド

Excel風プレビューへの色付けは次段階で行う。

## 9. 注意点

類似度照合を入れているため、途中に空行や数行が挿入されても、後続行がすべて変更扱いになることはある程度避けられる。

ただし、似た作業行が大量にある場合は誤マッチする可能性がある。

この問題はMVP後に、行の安定IDや業務キーを導入して改善する。
