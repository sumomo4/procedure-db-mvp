# Sprint 3 レビュー資料

## 1. Sprint 3 の到達点
Sprint 3 では、Sprint 2 で整えた参照系の上に、standard の主要データを「登録・更新できる状態」まで前進させた。

今回の主な到達点は次のとおり。

- モジュール登録 API / WebUI を実装
- 原本作成 / 更新 API / WebUI を実装
- 承認状態変更 API / WebUI を実装
- Excel 取込の最小設計と最小実装を追加
- テストサーバー上で主要導線を確認

---

## 2. レビュー対象

### 2-1. モジュール登録
- `POST /api/v1/modules`
- `/modules/register`

確認ポイント:
- 手入力でモジュールを登録できる
- 装置ブロックを追加できる
- 手順行を追加できる
- 多装置入力を保持できる
- 保存後に詳細画面へ遷移できる

---

### 2-2. 原本作成 / 更新
- `POST /api/v1/source-docs`
- `PUT /api/v1/source-docs/{source_doc_id}`
- `/documents/create`
- `/documents/create?id={source_doc_id}`

確認ポイント:
- 原本を新規作成できる
- 既存原本を更新モードで開ける
- 更新後に新しい draft 版として保持できる

---

### 2-3. 承認状態変更
- `PATCH /api/v1/statuses/{target_id}`
- `/approval`

確認ポイント:
- 一覧から対象を選べる
- `draft -> published -> archived` の最小遷移ができる
- 状態変更結果が画面上で分かる

---

### 2-4. Excel取込
- `POST /api/v1/modules/import-sheet`
- `POST /api/v1/modules/import`
- `/modules/register`

確認ポイント:
- 1シート相当の JSON を正規化できる
- `xlsx / xlsm` をアップロードできる
- 取込結果を登録画面へ反映できる
- 手修正後にそのまま保存できる

---

## 3. レビュー時の確認URL

### 3-1. テストサーバー
- `http://192.168.10.5/modules/register`
- `http://192.168.10.5/modules/1`
- `http://192.168.10.5/documents/create`
- `http://192.168.10.5/documents/create?id=1`
- `http://192.168.10.5/documents/1`
- `http://192.168.10.5/approval`

### 3-2. API
- `http://192.168.10.5/api/v1/modules/1`
- `http://192.168.10.5/api/v1/source-docs/1`
- `http://192.168.10.5/api/v1/statuses`
- `http://192.168.10.5/api/v1/health`
- `http://192.168.10.5/api/v1/health/db`

---

## 4. 今回までの確認済み項目

### 4-1. Backend
- pytest 通過
- モジュール登録 / 原本作成更新 / 承認状態変更 / Excel helper の主要正常系を確認

### 4-2. Frontend
- build 通過
- モジュール登録 / 原本作成更新 / 承認状態変更画面の主要導線を確認
- `Excelファイル取込` UI と `Excel取込プレビュー` を確認

### 4-3. Docker ローカル
- モジュール保存
- モジュール詳細表示
- 原本作成 / 更新
- 承認状態変更
- 実ファイル取込
を確認

### 4-4. テストサーバー
- `/modules/register`
- `/modules/{id}`
- `/documents/create`
- `/documents/{id}`
- `/approval`
を確認

---

## 5. 既知の留意点
- 原本詳細の多装置表示方針は、モジュール詳細と完全には揃え切れていない
- 文言は日本語化を進めたが、最終的な業務用語への寄せは今後も微調整余地がある
- deploy script は API 起動待ち改善を入れたが、再起動直後に一瞬 `curl: (7)` が見えることはある
- ローカル Docker DB は schema 差分で不整合が起こる場合があるため、必要に応じて volume 再作成が必要

---

## 6. Sprint 4 への持ち越し候補
- 原本詳細側の多装置表示統一
- Excel取込後の原本連携
- レビュー観点を踏まえた UI 微調整
- 承認操作の複数選択や一括更新の検討
