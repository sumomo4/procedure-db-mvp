# Sprint 3 候補整理

## 1. 方針

Sprint 3 は、Sprint 2 で整った閲覧系の土台を使って、入力系と外部連携へ進める。

優先度は以下の順で考える。

1. 登録 / 更新の業務成立
2. Excel 取込 / 出力の成立
3. Access 連携の整理
4. 運用と保守性の強化

## 2. 優先候補

### P1: モジュール登録 / 更新

- モジュール登録 API
- モジュール更新 API
- WebUI の登録画面を実API接続へ切替
- 入力バリデーション方針整理

期待成果:

- 仮seedではなく、利用者がモジュールを登録 / 更新できる

### P1: 原本作成 / 更新

- 原本作成 API
- 原本更新 API
- モジュール組み合わせ保存
- WebUI の原本作成 / 更新画面を実API接続へ切替

期待成果:

- 原本を業務単位で組み立てて保存できる

### P1: 承認状態変更

- `PATCH /api/v1/statuses/{target_id}` 実装
- 状態遷移ルールの適用
- 更新後の表示反映

期待成果:

- draft / published / archived を操作できる

## 3. Excel 関連候補

### P2: Excel取込

- Excel 読み取り入口の追加
- `excel_import.py` を使った `work_text` / `indent_level` 抽出
- 他列の読み取り方針整理
- 取込結果を DB へ保存

期待成果:

- 手打ちseedではなく、Excel からモジュールを生成できる

### P2: Excel出力

- module / source-doc から Excel を生成
- まずは業務データ中心で出力
- 見た目完全再現は段階的に判断

期待成果:

- WebUI / DB の内容を Excel へ戻せる

## 4. Access 連携候補

### P2: Access責務整理

- Access が持つ責務の棚卸し
- Web / API / DB へ寄せる範囲の確定
- 連携I/Fの最小設計

候補:

- 直接置き換え
- CSV / Excel 中継
- API 連携

## 5. 保守性強化候補

### P3: DB migration 管理

- 初期化SQL中心から migration 管理へ移行するか判断
- Alembic 導入是非の整理

### P3: CI/CD 拡張

- GitHub Actions の成果確認整理
- 手動トリガー型 CD 方針
- テストサーバー反映の半自動化

### P3: 認証 / 権限

- ログイン仮実装の整理
- 利用者 / 権限区分の最小設計

## 6. 後回しでよい論点

- Excel の罫線 / 色 / 結合セルの完全再現
- 採番ルールの細部確定
- 高度な履歴比較UI
- 本番運用前提の監査機能

## 7. 推奨する着手順

1. モジュール登録 / 更新 API
2. 原本作成 / 更新 API
3. 承認状態変更 API
4. Excel 取込
5. Excel 出力
6. Access 連携整理
7. CI/CD / migration / 認証
