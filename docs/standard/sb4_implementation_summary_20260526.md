# Sprint4 実装まとめ（2026-05-26時点）

## 1. 目的

Sprint4 では、MVPとして実業務に近い形で以下を確認できる状態まで進めた。

- AccessDB抽出ファイルを基に案件CS生成に必要な値を解決する
- Excel投入でモジュールを登録し、画像を含めて保持する
- 案件CS生成時に画像をExcelへ配置する
- 原本・モジュールの承認状態を画面から確認、変更する
- モジュール版を比較し、差分を画面で確認する
- モジュールと原本の版番号を `ver.X.Y` 形式で扱う

## 2. 案件CS生成まわり

### 2.1 AccessDB抽出ファイル経由のマスタ参照

実運用では AccessDB へ直接接続せず、AccessDBから抽出したExcelファイル群を参照する方針にした。

- 参照先: `storage/standard/access_exports`
- 実装方式: `ExportFileCaseDocMasterRepository`
- 切替設定: `CASE_DOC_MASTER_SOURCE=export_file`
- 都道府県、ビル、ユニット構成などの選択肢を抽出ファイルから取得する

MVPでは、大阪・福岡・四国などのテストデータも抽出ファイル側へ追加し、WebUIから選択できるようにした。

### 2.2 プレースホルダ管理

プレースホルダ定義をコード固定ではなく、YAML管理へ寄せた。

- 設定ファイル: `apps/standard/backend/app/config/placeholder_mapping.yml`
- 一覧APIを追加
- WebUIにプレースホルダ一覧画面を追加
- 追加、編集、有効化、無効化の画面操作を実装
- 内部キーはユーザーに手入力させず、値列などから自動生成する形にした

削除機能、参照ファイル・列名の強い検証、値列の候補選択は今後課題。

### 2.3 案件CS生成Excel

テンプレート `case_doc_template.xlsm` を基に、案件CSを `.xlsm` として生成する。

実装済み:

- 原本行をテンプレートの作業表形式へ展開
- 複数対象装置に対応
- 対象装置列は横方向に増える構造に対応
- 行末罫線、連絡事項欄などの最低限の体裁調整
- 作業内容のインデントを E〜H 列の幅で表現
- 固定文字列だった `testpass` や `show tty` などを正式プレースホルダ化

印刷設定は、業務上の利用想定からMVPでは対象外とした。

## 3. 画像対応

### 3.1 Excel投入時の画像抽出

モジュール投入時に、Excel内の画像を抽出して保存するようにした。

- 画像保存先: `storage/standard/module_images`
- 画像メタデータ保存先: `proc.module_row_images`
- 行レスポンスに画像メタデータを含める
- 画像取得APIを追加

これにより、モジュール詳細やプレビューで画像を扱える土台を作った。

### 3.2 案件CS生成時の画像配置

案件CS生成時に、画像をExcelへ出力するようにした。

採用方針:

- Excelの「セル内画像」ではなく、MVPでは通常画像として配置する
- 画像行の高さ固定
- 画像最大サイズ制限
- 他の手順行への被り防止
- 画像がある行にも、作業内容・確認事項・コマンドなどの文字情報を残せるようにする

作業内容欄に画像がある場合は作業内容側へ配置し、確認事項欄に画像がある場合は確認事項欄側へ配置する。

今後課題:

- 画像サイズや配置位置の細かい調整
- 画像の複数枚対応時の見せ方
- Excelのセル内画像として扱う方式の検証

## 4. モジュール登録・版管理

### 4.1 Excel投入のみで作成・更新する方針

MVPでは、モジュール作成・更新はExcel投入のみとした。

方針:

- 新規Excel投入でモジュールを作成
- 既存モジュールの修正もExcel投入で行う
- 画面上の手入力によるモジュール登録欄は非表示にした
- 画像関連の手入力欄もMVPでは非表示にした

### 4.2 既存 draft 版の更新

モジュール修正登録時、既に draft 版がある場合に `draft module version already exists.` で失敗していた。

修正後:

- 既存モジュールに draft 版がある場合は、新しい版を作らず既存 draft 版を更新する
- 既存 draft の行データと画像データを入れ替える
- `review_requested` 版がある場合は更新不可のままにする

これにより、差し戻し後にExcelを修正して再投入する操作が可能になった。

## 5. 承認機能

### 5.1 原本承認

原本側に承認状態確認・変更の画面を用意した。

実装済み:

- 承認履歴表示
- ステータスフィルター
- 承認者、コメント、差戻し理由の表示
- サイドバー上では、原本系の導線として `CS案件化` より上に配置

### 5.2 モジュール承認

モジュール版単位で承認状態を扱うようにした。

状態:

- 作成中
- 承認依頼中
- 差戻し
- 承認済み
- 保管済み

実装済み:

- メンバーは draft から承認依頼できる
- 承認依頼中のものはメンバーが触れない
- 承認者は承認依頼中のものを承認または差戻しできる
- 差し戻されたものはメンバーが再編集できる
- 差戻しコメントを画面で確認できる
- 承認依頼ボタンのサブテキストを整理し、誤解しにくくした
- モジュール検索にステータスフィルターを追加

MVPではフロントエンド側でロールを切り替える方式とし、バックエンド認可はMVP後課題とした。

## 6. バージョンナンバリング

### 6.1 表記ルール

モジュール・原本ともに `ver.X.Y` 形式へ整理した。

- X: 承認済みとして確定した大きな版
- Y: draft内の修正回数、承認依頼回数に近い小さな版
- 初期値: `ver.0.0`

### 6.2 遷移時のルール

現時点のルール:

- 初回作成: `ver.0.0`
- 承認依頼: `Y` を 1 増やす
- 差戻し後に修正し、再度承認依頼: `Y` を 1 増やす
- draft から approval になったとき: `X` を 1 増やし、`Y` を 0 にする
- approval から archive へ遷移するとき: 版番号はそのまま

例:

- `ver.0.0` → 承認依頼 → `ver.0.1`
- `ver.0.1` → 差戻し → 修正 → 承認依頼 → `ver.0.2`
- `ver.0.2` → 承認 → `ver.1.0`

## 7. diff機能

### 7.1 基本方針

モジュールの版同士を比較し、作業行の差分を表示する。

当初は大・中・小番号をキーにする案もあったが、モジュール登録時に番号が必ず入るとは限らないため、`row_order + 内容類似` に寄せた。

実装済み:

- モジュール詳細からdiff表示へ遷移
- 比較元・比較先の版を選択できる
- 追加、削除、変更を表示
- 変更行にはExcelの行番号を表示
- 類似度はユーザーには見せない
- 内部版番号はユーザーには見せない

### 7.2 Excel取込文字列の修正

Excelに含まれるふりがな情報を通常文字列として拾ってしまい、カタカナが混ざる問題があった。

例:

- `画像入りモジュールガゾウイ`
- `連絡事項レンラクジコウ`

修正後:

- shared string の `rPh` を除外
- inline string の `rPh` を除外
- ふりがな文字列を取り込まないようにした

既存データに混入していた文字列も補正した。

## 8. 確認済み事項

直近の確認:

- backend 全テスト: `127 passed`
- Docker API health: OK
- GitHub `main` へ push 済み
- モジュール修正登録が既存 draft 更新として動作することを確認

## 9. 主な関連コミット

- `94ce6e7` Extract module row images from workbook imports
- `4368e5d` Handle images in case document generation
- `c8b2f9e` Show module row images in previews
- `3339a4f` Add approval status history
- `25b6ee3` Add approval return comments
- `827baf8` Add approval status filter
- `f9b9d26` Add frontend approval role control
- `84ab046` Add module versioning diff and approval flow updates
- `ddddb7f` Improve module diff display
- `f91fe60` Refine module diff row display
- `445821f` Allow selecting module diff versions
- `419be51` Refine approval request workflow
- `3bc6ae1` Add module status filter controls
- `d57d56a` Add module and source document version numbering
- `1d4eca5` Improve module diff labels and Excel text import
- `d5424f5` Hide internal version numbers in diff UI
- `7ed6ac5` Allow updating existing draft module versions

## 10. 残課題

優先度が高いもの:

- 実データでのdiff精度確認
- 画像付きプレビューの見た目調整
- 案件CS生成時の画像サイズ、行高さ、配置の最終調整
- プレースホルダ設定の検証強化
- バックエンド側の認可実装

後回しでよいもの:

- 印刷設定
- Excelセル内画像方式の検証
- プレースホルダ削除機能
- 社内公開用サーバー前提の運用設計
