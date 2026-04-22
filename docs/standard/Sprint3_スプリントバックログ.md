# Sprint 3 スプリントバチE��ログ�E�たたき台�E�E
## 1. Sprint概要E※ 本スプリントバチE��ログは、Sprint 2 の成果を踏まえ、主要データの閲覧系から登録・更新系へ進むための作業単位を整琁E��たものである、E
- Sprint名：Sprint 3�E�登録・更新の成立！E- 目皁E��Sprint 2 で成立しぁEWebUI + API + DB の閲覧基盤を使ぁE��モジュール / 原本 / 承認状態�E入力系を�E立させる
- 期間�E�[記�E]
- 対象領域�E�standard
- 対象外：lab
- Sprintゴール�E�E  - モジュール登録APIの最小実裁E��成立してぁE��
  - 原本作�E / 更新APIの最小構�Eが整琁E��れてぁE��
  - 承認状態変更APIの方針が整琁E��れ、最小実裁E��着手できる
  - WebUIの登録 / 更新画面を実API接続へ進める前提が揃ってぁE��
  - Excel取込を後続実裁E��きる入口が整琁E��れてぁE��

---

## 2. Sprint 3 で実施する頁E��
| SB-ID | 允E��チE��ログID | 種別 | 頁E�� | 優先度 | 拁E��E| 状慁E| 完亁E��件�E�受入条件�E�E| 依孁E|
|---|---|---|---|---|---|---|---|---|
| SB3-01 | - | API | モジュール登録APIの最小実裁E��行う | High | [記�E] | [渁E | `module_name` / `rows` 忁E��、`module_key` 省略時�E `MOD-xxx` 自動採番、`draft` の version 1 を作�Eし、`module_rows` を保存して作�E結果を返せめE| Sprint 2 完亁E|
| SB3-02 | - | チE��チE| モジュール登録APIのpytestを追加する | High | [記�E] | [渁E | 正常系、�E力不備、業務バリチE�Eション、DB失敗�E主要ケースが通る | SB3-01 |
| SB3-03 | - | WebUI | モジュール登録画面を実API接続へ刁E��替える | High | [記�E] | [渁E | モジュール登録画面から登録APIを呼び、保存結果を表示できる | SB3-01, SB3-02 |
| SB3-04 | - | 仕様検訁E| 原本作�E / 更新の最小�E力頁E��を整琁E��めE| High | [記�E] | [渁E | `source_doc_name` / `items` 忁E��、`source_doc_key` 省略時�E `BP-STD-xxx` 自動採番、モジュールの並び頁E��有効/無効を保持する最小�E力が整琁E��れてぁE�� | Sprint 2 完亁E|
| SB3-05 | - | API | 原本作�EAPIの最小実裁E��行う | High | [記�E] | [渁E | `POST /api/v1/source-docs` で blueprint / version / items を保存し、作�E結果を詳細レスポンスで返せめE| SB3-04 |
| SB3-06 | - | API | ���{�X�VAPI�̍ŏ��������s�� | Medium | [�L��] | [��] | `PUT /api/v1/source-docs/{source_doc_id}` �Ō��{�X�V�ł�ۑ��ł��A�X�V��͐V���� draft �łƂ��ďڍ׃��X�|���X��Ԃ��� | SB3-05 |
| SB3-07 | - | WebUI | ���{�쐬 / �X�V��ʂ���API�ڑ��֐؂�ւ��� | High | [�L��] | [��] | `/documents/create` ���� `POST /api/v1/source-docs` ���Ă�ŕۑ��ł��A`/documents/create?id={source_doc_id}` ���� `PUT /api/v1/source-docs/{source_doc_id}` �ōX�V�ł��� | SB3-05, SB3-06 |
| SB3-08 | - | 仕様検訁E| 承認状態変更の業務ルールを整琁E��めE| Medium | [記�E] | [未着手] | 誰ぁE/ ぁE�� / どの条件で draft / published / archived に変更できるか整琁E��れてぁE�� | Sprint 2 完亁E|
| SB3-09 | - | API | 承認状態変更APIを実裁E��めE| Medium | [記�E] | [未着手] | `PATCH /api/v1/statuses/{target_id}` で状態変更できる | SB3-08 |
| SB3-10 | - | WebUI | 承認状態変更操作を画面から実行できるようにする | Medium | [記�E] | [未着手] | 承認状態画面から変更APIを呼び、結果を反映できる | SB3-09 |
| SB3-11 | - | 仕様検訁E| Excel取込の最小方針を整琁E��めE| Medium | [記�E] | [未着手] | Excel入力かめEmodule_rows 保存までの流れが整琁E��れてぁE�� | SB3-01 |
| SB3-12 | - | API | Excel取込入口の最小実裁E��行う | Medium | [記�E] | [未着手] | `excel_import.py` を利用する取込入口の骨絁E��が追加されめE| SB3-11 |
| SB3-13 | - | CI | 入力系API追加に合わせてチE��ト確認を拡張する | Medium | [記�E] | [未着手] | pytest と build が�E力系変更後も安定して通る | SB3-02, SB3-05, SB3-09 |
| SB3-14 | - | Deploy | チE��トサーバ�EへSprint 3途中成果を反映する | Medium | [記�E] | [未着手] | 登録 / 更新系の途中成果を関係老E��確認できる | SB3-03, SB3-07, SB3-10 |
| SB3-15 | - | 管琁E| Sprint 3レビュー賁E��を準備する | Medium | [記�E] | [未着手] | 登録 / 更新 / 状態変更 / Excel取込入口の進捗が整琁E��れてぁE�� | SB3-14 |

---

## 3. 最優先頁E��
Sprint 3 で特に優先して完亁E��せる頁E��は以下とする、E
- SB3-01�E�モジュール登録APIの最小実裁E��行う
- SB3-02�E�モジュール登録APIのpytestを追加する
- SB3-03�E�モジュール登録画面を実API接続へ刁E��替える
- SB3-04�E�原本作�E / 更新の最小�E力頁E��を整琁E��めE- SB3-05�E�原本作�EAPIの最小実裁E��行う
- SB3-08�E�承認状態変更の業務ルールを整琁E��めE
---

## 4. Sprint 3 完亁E��件
Sprint 3 は、以下を満たした時点で完亁E��する、E
- モジュール登録が�E立してぁE��
  - APIから module / version / rows を保存できる
  - WebUIから最小登録操作ができる
- 原本の作�E / 更新に着手できてぁE��
  - 最小�E力頁E��が整琁E��れてぁE��
  - 作�EAPIが保存できる
- 承認状態変更の入口があめE  - 状態変更ルールが整琁E��れてぁE��
  - API また�E設計が次実裁E��進める粒度になってぁE��
- Excel取込の前提があめE  - `excel_import.py` を活かす入口設計がある
- 確認できる状態になってぁE��
  - backend のpytestが通る
  - frontend のbuildが通る
  - チE��トサーバ�Eで途中成果を確認できる

---

## 5. Sprint 3 の成果物

- モジュール登録API
- モジュール登録APIチE��チE- モジュール登録画面のAPI接綁E- 原本作�E / 更新の最小�E力頁E��整琁E- 原本作�EAPI
- 原本更新API
- 承認状態変更ルール整琁E- 承認状態変更API
- Excel取込入口の最小実裁E- Sprint 3レビュー賁E��

---

## 6. レビュー観点

- Sprint 2 の閲覧系基盤を崩さずに入力系へ進めてぁE��ぁE- 登録 / 更新APIの責務�E拁E�E妥当か
- 版管琁E�E扱ぁE�E無琁E��なぁE��
- モジュール / 原本 / 承認状態変更の依存関係�E整琁E��きてぁE��ぁE- Excel取込を後続実裁E��きる形になってぁE��ぁE- 関係老E��認に忁E��な途中成果をテストサーバ�Eで見せられるか

---

## 7. 補足・未決事頁E
- Sprint 3 ではまぁEJSON ベ�Eス登録を優先し、Excel直接取込は段階的に進める
- Excelの見た目完�E再現は対象外とする
- Access 連携は Sprint 3 後半以降�E扱ぁE��し、まず�E Web / API / DB 側の入力�E立を優先すめE- migration 管琁E���Eは入力系変更量を見て判断する

### �⑫����
- ���{�쐬��ʂ� `�L��` �`�F�b�N�́A`blueprint_items.enabled` �ɕۑ����鉼�t���O�Ƃ��Ĉ����B
- `ON` �͂��̃��W���[�������{���ŗL���Ɏg���A`OFF` �͌��{�ɂ͕R�Â��邪���������ŕێ�����Ӗ��Ƃ���B
- �Ɩ���̌����ȉ^�p���[���� Sprint 3 �㔼���� Sprint 4 �ōĐ�������B
