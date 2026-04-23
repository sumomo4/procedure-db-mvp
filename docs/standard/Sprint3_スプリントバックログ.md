# Sprint 3 スプリントバックログ（たたき台）

## 1. Sprint 3 の目的
Sprint 3 では、Sprint 2 で整えた参照系の土台をもとに、standard の主要データを「登録・更新できる状態」まで進めます。
対象は standard のみとし、lab は今回のスコープに含めません。

主な到達目標は次のとおりです。
- モジュール登録 API / WebUI を実装する
- 原本作成・更新 API / WebUI を実装する
- 承認状態変更 API / WebUI の入口を整える
- Excel 取込に向けた最小設計を前進させる
- テストサーバーで関係者確認できる状態を継続する

---

## 2. バックログ一覧
| SB-ID | 分類 | タスク | 優先度 | 状態 | 受入条件 | 依存 |
|---|---|---|---|---|---|---|
| SB3-01 | API | モジュール登録APIの最小実装 | High | [済] | `POST /api/v1/modules` で module / version / rows を保存できる | Sprint 2 成果物 |
| SB3-02 | Test | モジュール登録APIの pytest 追加 | High | [済] | 正常系・入力不正・DB異常系を含む pytest が通る | SB3-01 |
| SB3-03 | WebUI | モジュール登録画面を実API接続へ切り替える | High | [済] | `/modules/register` から登録APIを呼んで保存できる | SB3-01, SB3-02 |
| SB3-04 | 設計 | 原本作成 / 更新の最小項目整理 | High | [済] | 原本の key / name / items / change note の最小構成が整理されている | Sprint 2 成果物 |
| SB3-05 | API | 原本作成APIの最小実装 | High | [済] | `POST /api/v1/source-docs` で blueprint / version / items を保存できる | SB3-04 |
| SB3-06 | API | 原本更新APIの最小実装 | Medium | [済] | `PUT /api/v1/source-docs/{source_doc_id}` で更新版を保存できる | SB3-05 |
| SB3-07 | WebUI | 原本作成 / 更新画面を実API接続へ切り替える | High | [済] | `/documents/create` で新規作成、`/documents/create?id={source_doc_id}` で更新できる | SB3-05, SB3-06 |
| SB3-08 | 設計 | 承認状態変更ルールを整理する | Medium | [済] | `draft -> published -> archived` の最小遷移ルールが整理されている | Sprint 2 成果物 |
| SB3-09 | API | 承認状態変更APIを実装する | Medium | [済] | `PATCH /api/v1/statuses/{target_id}` で状態変更できる | SB3-08 |
| SB3-10 | WebUI | 承認状態変更操作を画面から実行できるようにする | Medium | [済] | 承認状態確認画面から状態変更APIを呼べる | SB3-09 |
| SB3-11 | 設計 | Excel取込の最小入力設計を整理する | Medium | [進行中] | `excel_import.py` と整合する最小入力仕様が整理されている | SB3-01 |
| SB3-12 | API | Excel取込の最小実装を行う | Medium | [未] | Excel取込の入口を API / helper で確認できる | SB3-11 |
| SB3-13 | CI | 追加API / 画面変更に合わせた確認を整理する | Medium | [未] | pytest / build / deploy script check の観点が揃っている | SB3-02, SB3-05, SB3-09 |
| SB3-14 | Deploy | Sprint 3 の中間成果をテストサーバーで確認する | Medium | [進行中] | 実装済み機能がテストサーバーで確認できる | SB3-03, SB3-07, SB3-10 |
| SB3-15 | Review | Sprint 3 レビュー観点を整理する | Medium | [未] | レビュー時に確認すべき項目がまとまっている | SB3-14 |

---

## 3. 今回までの反映内容
Sprint 3 で今回までに反映できている内容は次のとおりです。

- SB3-01 / SB3-02
  - モジュール登録 API 実装
  - pytest 追加
- SB3-03
  - モジュール登録画面の API 接続
  - 装置ブロック追加 UI
  - 装置ごとの手順コマンド入力 UI
  - 多装置対応（最大20台）
  - 装置ブロックのアコーディオン表示
  - 日本語ラベル整備
- SB3-04 / SB3-05
  - 原本作成の最小設計
  - 原本作成 API 実装
- SB3-06 / SB3-07
  - 原本更新 API 実装
  - 原本作成 / 更新画面の API 接続
- SB3-08 / SB3-09
  - 承認状態変更ルールの整理
  - `PATCH /api/v1/statuses/{target_id}` 実装
  - `draft -> published -> archived` の最小遷移を反映
- SB3-10
  - 承認状態確認画面から状態変更APIを実行
  - 一覧 / 詳細 / 状態変更結果を画面上で確認
  - 原本詳細への導線を追加
- 詳細画面改善
  - モジュール詳細の Excel 風表示
  - 作業内容段落の DB 保持 (`indent_level`)
  - 装置コマンド欄のアコーディオン表示
- テストサーバー反映
  - `/modules/register`
  - `/modules/{id}`
  - `/documents/create`
  - `/documents/{id}`

---

## 4. 多装置対応メモ
今回の多装置 UI 対応で反映したポイントです。

- 1モジュールで最大20台までの可変装置列を扱う
- モジュール登録画面では、装置単位で次をまとめて入力する
  - `時刻 / target / P / 対象装置`
  - `時刻 / window / P / コマンド`
- モジュール詳細画面では、共通列は固定表示し、装置ごとのコマンド欄だけをアコーディオン表示する
- API / DB は MVP として JSONB ベースで複数装置を保持する
- 将来の完全正規化は別スプリントで再検討する

---

## 5. 現時点の管理メモ
- standard を主対象とし、lab は触らない
- `docs/standard/未経験者向け学習ロードマップ.md` は Git 管理対象外のまま扱う
- テストサーバー反映は、ファイル転送後に `finish_standard_server.sh` を実行して確認する
- UI 文言は日本語を基本とし、必要に応じて業務用語に寄せて調整する
- 承認状態の最小運用は、会議メモの `01_版管理ルール` / `02_承認ルール` を踏まえて次の形とする
  - `draft`: 承認前
  - `published`: 承認済み
  - `archived`: 過去版保管
  - 遷移は `draft -> published -> archived` のみ

---

## 6. 次の候補
次に進める候補はこのあたりです。

1. SB3-11 / SB3-12 の Excel 取込入口を具体化する
2. 原本詳細側も多装置表示方針をそろえる
3. Sprint 3 レビュー観点を整理する
4. 承認状態変更の利用手順を確認する
