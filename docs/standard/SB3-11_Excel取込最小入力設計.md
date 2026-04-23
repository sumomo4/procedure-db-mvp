# SB3-11 Excel取込の最小入力設計

## 1. 目的
Sprint 3 では、Excel からモジュールを取り込むための「最小入力」を整理する。

ここでいう最小入力とは、既存の `POST /api/v1/modules` に無理なく変換できる粒度を指す。
つまり、Excel 取込は新しい保存形式を作るのではなく、最終的に `ModuleCreateRequest` へ正規化して登録 API を呼ぶ前提とする。

本メモは standard のみを対象とし、lab は含めない。

---

## 2. 前提

- 既存の登録APIは次の構造を受け取れる
  - モジュール本体
    - `module_key`
    - `module_name`
    - `description`
    - `change_note`
    - `source_xlsx_path`
    - `source_sha256`
    - `created_by`
  - 装置ヘッダ
    - `device_headers[]`
  - 手順行
    - `rows[]`
  - 各手順行の装置別コマンド
    - `rows[].device_entries[]`

- 既存 helper
  - [excel_import.py](C:/Users/clove/OneDrive/ドキュメント/mvp-root/apps/standard/backend/app/core/excel_import.py:1)
  - `E / F / G / H` 列のどこに作業内容が置かれているかで `indent_level` を決める

- 多装置対応は MVP として JSONB で保持している
  - `module_versions.device_headers_json`
  - `module_rows.device_entries_json`

---

## 3. スコープ

### 3.1 Sprint 3 で対象にするもの

- モジュール Excel 1ファイルを 1モジュールとして取り込む
- 1シート単位で取り込む
- 取り込んだ結果を `ModuleCreateRequest` に変換する
- 将来の upload API / import API 実装で使える入力仕様を整理する

### 3.2 Sprint 3 で対象外にするもの

- 原本の Excel 取込
- 複数シートを一度にまとめて原本化する処理
- Excel の見た目完全再現
  - 色
  - 罫線
  - 結合セル情報そのもの
  - 列幅
  - フォント
- 数式評価やマクロ実行
- AccessDB 連携時のホルダー展開
  - `{{DEVICE_NAME}}` など

---

## 4. 最小入力の考え方

Excel 取込の最小入力は、次の2層に分けて扱う。

1. モジュール全体の入力
2. 手順行ごとの入力

さらに、手順行の中には

- 共通列
- 装置別列

の2種類がある。

### 4.1 モジュール全体の最小入力

最低限必要な値は次のとおり。

- `module_name`
- `rows[]`

Excel から直接取れない、または運用側で補う値は次の扱いとする。

- `module_key`
  - 任意入力
  - 未指定時は API 側で `MOD-xxx` 自動採番
- `description`
  - 任意
- `change_note`
  - 任意
- `created_by`
  - 取込実行者名で補完
- `source_xlsx_path`
  - 元ファイルパスを保持
- `source_sha256`
  - 余力があれば保持、最小実装では後回し可

### 4.2 装置ヘッダの最小入力

装置は `slot_no = 1..20` の可変式とする。

1装置あたりの最小入力は次の4項目。

- `header_time_text`
- `target_text`
- `p_text`
- `target_device_text`

これを `device_headers[]` に正規化する。

---

## 5. Excel から読む最小列

## 5.1 共通列

手順行として最小限読む項目は次のとおり。

| 項目 | 取込先 |
|---|---|
| 大 | `major_no` |
| 中 | `middle_no` |
| 小 | `minor_no` |
| 技術資料名 | `tech_doc_text` |
| 作業内容 | `work_text` |
| 作業内容の段落 | `indent_level` |
| 確認事項 or 項目 | `expected_result` |

補足:

- 作業内容は `E / F / G / H` のいずれかに入る前提
- 左から最初に値が入っている列を採用する
- `indent_level` は次の対応とする
  - `E -> 0`
  - `F -> 1`
  - `G -> 2`
  - `H -> 3`

これは 4段階の段差を 0始まりで保存する現在仕様と整合する。

## 5.2 装置別列

各装置の手順行側は、4列1セットの繰り返しとする。

- `time_text`
- `window_text`
- `p_text`
- `command_text`

これを装置ごとに `device_entries[]` へ変換する。

---

## 6. 取込単位

Sprint 3 の最小単位は次のとおり。

- 1ファイル
- 1シート
- 1モジュール

つまり、複数シートをまとめて 1回で複数モジュール登録する設計にはしない。

理由:

- 既存の `POST /api/v1/modules` と自然につながる
- エラー位置を特定しやすい
- 失敗時の切り戻しが簡単
- 原本側の複数モジュール構成と責務を分けやすい

---

## 7. 最小変換ルール

Excel 取込時の最小変換ルールは次のとおり。

1. 全体メタ情報を作る
   - `module_name`
   - `created_by`
   - `source_xlsx_path`
2. 装置ブロックを読む
   - 最大20台
   - 読めた装置だけ `device_headers[]` を作る
3. 手順行を上から順に読む
   - 完全空行はスキップ
   - `row_order` は採用した順で連番
   - MVP では基本 `row_type = "step"` とする
4. 共通列を抜く
   - 大 / 中 / 小 / 技術資料 / 作業内容 / 確認事項
5. 各装置のコマンド列を抜く
   - `device_entries[]`
6. `ModuleCreateRequest` に変換する
7. 既存 `create_module()` に渡す

---

## 8. row_type の最小方針

Sprint 3 の最小実装では、Excel から取り込んだ行は基本的に `row_type = "step"` とする。

理由:

- 現時点では UI / DB / 詳細表示の中心が手順行だから
- `header / meta / spacer` の厳密判定を先に入れると重くなるから

将来の拡張候補:

- 連絡事項行 -> `meta`
- 空白保持行 -> `spacer`
- 見出し専用行 -> `header`

---

## 9. バリデーションの最小ルール

Sprint 3 で最低限見るもの:

- `module_name` が空でない
- 手順行が1行以上ある
- `row_order` が重複しない
- `device_headers.slot_no` が重複しない
- `device_headers` は20台以下
- `rows[].device_entries[].slot_no` は定義済み装置にだけ紐づく
- `rows[].device_entries[]` 内で `slot_no` が重複しない

Excel取込特有の最低限ルール:

- `E / F / G / H` のうち複数列に同時入力がある場合は、最初はエラーにせず「左優先」で採用
- 装置列が途中で欠ける場合は、その装置の該当値を `None` とする
- 20台超はエラー

---

## 10. API入口の最小案

Sprint 3 の次タスク `SB3-12` に向けた最小入口は次のどちらか。

### 案A: helper 先行

- まずは backend helper で
  - `Workbook/Worksheet -> ModuleCreateRequest`
  を作れるようにする
- API なしで pytest 中心に確認する

利点:

- 実装が軽い
- エラー切り分けがしやすい

### 案B: upload API まで含める

- `POST /api/v1/modules/import`
- multipart upload で Excel を受け取る
- 内部で `ModuleCreateRequest` に変換して登録する

利点:

- WebUI とつなぎやすい

Sprint 3 の最小実装としては、**まず案Aを推奨**する。

---

## 11. 最小入力の結論

Sprint 3 の Excel 取込で最小入力とするものは、次の形に整理する。

### モジュール単位

- `module_name`
- `created_by`
- `source_xlsx_path`
- `device_headers[]`
- `rows[]`

### 行単位

- `row_order`
- `row_type = "step"`
- `major_no`
- `middle_no`
- `minor_no`
- `tech_doc_text`
- `work_text`
- `indent_level`
- `expected_result`
- `device_entries[]`

### 装置単位

- `slot_no`
- `header_time_text`
- `target_text`
- `p_text`
- `target_device_text`

### 行内装置単位

- `slot_no`
- `time_text`
- `window_text`
- `p_text`
- `command_text`

---

## 12. SB3-12 に引き渡す内容

次タスクでは、少なくとも次を実装対象にする。

1. `excel_import.py` を拡張して、Excel の1シートを `ModuleCreateRequest` に変換できるようにする
2. `E / F / G / H` から `work_text` / `indent_level` を抽出する
3. 装置ヘッダ 4項目と、行ごとの装置コマンド 4項目を可変台数で抽出する
4. pytest で
   - 1台
   - 2台
   - 20台境界
   - 空行
   - 段落
   - 欠損値
   を確認する

---

## 13. メモ

- 今回の設計は「MVPとして既存登録APIに載せる」ことを優先している
- 将来、完全正規化や原本取込まで進めるときは再整理する
- AccessDB 連携時のホルダー置換は、この段階では扱わない
