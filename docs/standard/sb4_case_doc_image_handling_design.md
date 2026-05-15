# SB4 案件CS画像扱い設計メモ

## 1. 目的

案件CS生成時に、Excel投入で作成したモジュール内の画像を、生成後の案件CS Excelにも再現できるようにする。

MVPでは、画像はExcel投入時に抽出し、画像ファイルとして別管理する。
案件CS生成時は、DBに保存した画像キー・画像パス・貼り付け位置を使って、出力Excelへ画像そのものを埋め込む。

## 2. 基本方針

- 画像の取得元は、モジュール投入時のExcelファイルとする。
- 画像は出力Excelに画像そのものとして埋め込む。
- 出力Excelには画像パスを表示しない。
- 画像ファイルはアプリ管理領域に保存する。
- 原本行には画像情報を直接1件だけ持たせず、画像専用テーブルで管理する。
- 1つのモジュール行に複数画像があるケースを許容する。

## 3. 保存場所

MVPでは、画像ファイルを以下へ保存する。

```text
storage/standard/module_images/{module_key}/{image_key}.{ext}
```

例:

```text
storage/standard/module_images/MOD-001/MOD-001_r12_img1.png
```

Docker上では、既存の `storage/standard` を永続化領域として使う。

## 4. 画像キー

画像キーは人手入力ではなく、Excel投入時に自動生成する。

命名案:

```text
{module_key}_r{row_order}_img{image_order}
```

例:

```text
MOD-001_r12_img1
MOD-001_r12_img2
MOD-002_r31_img1
```

考え方:

- `module_key`: モジュールを識別する。
- `row_order`: 紐づくモジュール行を識別する。
- `image_order`: 同じ行に複数画像がある場合の順番を識別する。

## 5. 貼り付け位置の記録

投入元Excelと同じ場所へ戻すため、画像のアンカー情報を保存する。

最低限保存する項目:

```text
anchor_cell
offset_x_px
offset_y_px
width_px
height_px
```

例:

```text
anchor_cell = E12
offset_x_px = 4
offset_y_px = 2
width_px = 480
height_px = 260
```

MVPでは、まず `anchor_cell`, `width_px`, `height_px` を優先する。
offsetの完全再現は、必要に応じて後続で精度を上げる。

## 6. DB設計案

画像は専用テーブルで管理する。

```sql
CREATE TABLE proc.module_row_images (
    module_row_image_id bigserial PRIMARY KEY,
    module_row_id bigint NOT NULL REFERENCES proc.module_rows (module_row_id) ON DELETE CASCADE,
    image_key text NOT NULL,
    image_path text NOT NULL,
    anchor_cell text NOT NULL,
    offset_x_px integer NOT NULL DEFAULT 0,
    offset_y_px integer NOT NULL DEFAULT 0,
    width_px integer,
    height_px integer,
    image_order integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (module_row_id, image_key)
);
```

補足:

- `image_path` は `storage/standard` 配下の相対パスとして保存する。
- 絶対パスはPC差分が出るため保存しない。
- `module_row_id` に紐づけることで、行削除時に画像メタデータも削除する。

## 7. Excel投入時の処理

Excel投入時は、以下の流れで画像を取り込む。

1. Excelファイルを読み込む。
2. シート上の画像一覧を取得する。
3. 各画像のアンカーセルを特定する。
4. アンカーセルから対象のモジュール行を推定する。
5. 画像キーを自動生成する。
6. 画像ファイルを `storage/standard/module_images/{module_key}/` へ保存する。
7. `proc.module_row_images` に画像メタデータを保存する。

## 8. 案件CS生成時の処理

案件CS生成時は、以下の流れで画像を貼り戻す。

1. 原本に含まれる有効モジュール行を展開する。
2. 展開元の `module_row_id` に紐づく画像メタデータを取得する。
3. 出力先の行番号へアンカーセルを変換する。
4. `image_path` から画像ファイルを読み込む。
5. `openpyxl` で出力Excelへ画像を追加する。
6. width / height を設定する。

## 9. 画像が見つからない場合

MVPでは、画像ファイルが見つからない場合でも案件CS生成は止めない。

扱い:

- 画像なしでExcel生成を継続する。
- `解決値` または `原本展開` シートに警告を残す。
- APIレスポンスとしては通常のExcelダウンロードを返す。

将来的に本番運用へ近づける段階で、必須画像の欠落をエラーにするか検討する。

## 10. 実装順序

推奨順序:

1. `proc.module_row_images` テーブルを追加する。
2. モジュール行レスポンスに画像メタデータを含める。
3. Excel投入処理で画像抽出と保存を行う。
4. 案件CS生成処理で画像を貼り戻す。
5. 画像が見つからない場合の警告出力を追加する。
6. WebUIのモジュール詳細/原本詳細で画像有無を確認できるようにする。

## 11. MVPでやらないこと

以下はMVPでは後回しとする。

- Excel画像の完全なoffset再現
- セル内画像の厳密な再現
- 画像の画面アップロード編集
- 画像差し替えUI
- 画像の削除UI
- 画像圧縮やサムネイル生成

## 12. 注意点

- 画像ファイルはGit管理しない。
- 画像メタデータはDB管理する。
- 画像パスは相対パスで保存する。
- 生成Excelには画像そのものを埋め込む。
- 画像キーはユーザーに入力させず、自動生成する。
