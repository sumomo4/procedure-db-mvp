CREATE SCHEMA IF NOT EXISTS proc;

CREATE TABLE IF NOT EXISTS app_metadata (
    key text PRIMARY KEY,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proc.modules (
    module_id bigserial PRIMARY KEY,
    module_key text NOT NULL UNIQUE,
    name text NOT NULL,
    description text,
    folder_path text NOT NULL DEFAULT '未分類',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proc.module_versions (
    module_version_id bigserial PRIMARY KEY,
    module_id bigint NOT NULL REFERENCES proc.modules (module_id),
    version_no integer NOT NULL CHECK (version_no > 0),
    version_major integer NOT NULL DEFAULT 0 CHECK (version_major >= 0),
    version_minor integer NOT NULL DEFAULT 0 CHECK (version_minor >= 0),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review_requested', 'returned', 'published', 'archived')),
    change_note text,
    source_xlsx_path text,
    source_sha256 text,
    created_by text,
    header_time_text text,
    target_text text,
    common_p_text text,
    target_device_text text,
    device_headers_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (module_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_module_versions_status
    ON proc.module_versions (status);

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS proc.module_similarity_signatures (
    module_version_id bigint PRIMARY KEY
        REFERENCES proc.module_versions (module_version_id)
        ON DELETE CASCADE,
    normalized_name text NOT NULL,
    normalized_work_text text NOT NULL,
    normalized_expected_text text NOT NULL,
    normalized_command_text text NOT NULL,
    normalized_structure_text text NOT NULL,
    normalized_device_header_text text NOT NULL,
    normalized_image_text text NOT NULL,
    combined_text text NOT NULL,
    exact_sha256 varchar(64) NOT NULL,
    row_count integer NOT NULL,
    image_count integer NOT NULL,
    generated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_module_similarity_signatures_exact_sha256
    ON proc.module_similarity_signatures (exact_sha256);

CREATE INDEX IF NOT EXISTS idx_module_similarity_signatures_combined_text_trgm
    ON proc.module_similarity_signatures
    USING gin (combined_text gin_trgm_ops);

ALTER TABLE proc.modules
    ADD COLUMN IF NOT EXISTS folder_path text NOT NULL DEFAULT '未分類';

CREATE INDEX IF NOT EXISTS idx_modules_folder_path
    ON proc.modules (folder_path);

CREATE TABLE IF NOT EXISTS proc.module_folder_memberships (
    module_id bigint NOT NULL REFERENCES proc.modules (module_id) ON DELETE CASCADE,
    folder_path text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (module_id, folder_path)
);

CREATE INDEX IF NOT EXISTS idx_module_folder_memberships_folder_path
    ON proc.module_folder_memberships (folder_path);

INSERT INTO proc.module_folder_memberships (module_id, folder_path)
SELECT
    module_id,
    COALESCE(NULLIF(folder_path, ''), '未分類')
FROM proc.modules
ON CONFLICT (module_id, folder_path) DO NOTHING;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS version_major integer NOT NULL DEFAULT 0;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS version_minor integer NOT NULL DEFAULT 0;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS header_time_text text;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS target_text text;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS common_p_text text;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS target_device_text text;

ALTER TABLE proc.module_versions
    ADD COLUMN IF NOT EXISTS device_headers_json jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS proc.module_rows (
    module_row_id bigserial PRIMARY KEY,
    module_version_id bigint NOT NULL REFERENCES proc.module_versions (module_version_id) ON DELETE CASCADE,
    row_order integer NOT NULL CHECK (row_order > 0),
    row_type text NOT NULL CHECK (row_type IN ('header', 'step', 'meta', 'spacer')),
    major_no text,
    middle_no text,
    minor_no text,
    tech_doc_text text,
    work_text text,
    indent_level integer CHECK (indent_level BETWEEN 0 AND 3),
    check_text_default text,
    time_text text,
    window_template_default text,
    p_template_default text,
    command_template_default text,
    device_entries_json jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (module_version_id, row_order)
);

CREATE INDEX IF NOT EXISTS idx_module_rows_module_version_id
    ON proc.module_rows (module_version_id);

CREATE TABLE IF NOT EXISTS proc.module_row_images (
    module_row_image_id bigserial PRIMARY KEY,
    module_row_id bigint NOT NULL REFERENCES proc.module_rows (module_row_id) ON DELETE CASCADE,
    image_key text NOT NULL,
    image_path text NOT NULL,
    anchor_cell text NOT NULL,
    offset_x_px integer NOT NULL DEFAULT 0,
    offset_y_px integer NOT NULL DEFAULT 0,
    width_px integer,
    height_px integer,
    image_order integer NOT NULL DEFAULT 1 CHECK (image_order > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (module_row_id, image_key)
);

CREATE INDEX IF NOT EXISTS idx_module_row_images_module_row_id
    ON proc.module_row_images (module_row_id);

ALTER TABLE proc.module_rows
    ADD COLUMN IF NOT EXISTS time_text text;

ALTER TABLE proc.module_rows
    ADD COLUMN IF NOT EXISTS indent_level integer;

ALTER TABLE proc.module_rows
    ADD COLUMN IF NOT EXISTS device_entries_json jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS proc.blueprints (
    blueprint_id bigserial PRIMARY KEY,
    blueprint_key text NOT NULL UNIQUE,
    name text NOT NULL,
    description text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proc.blueprint_versions (
    blueprint_version_id bigserial PRIMARY KEY,
    blueprint_id bigint NOT NULL REFERENCES proc.blueprints (blueprint_id),
    version_no integer NOT NULL CHECK (version_no > 0),
    version_major integer NOT NULL DEFAULT 0 CHECK (version_major >= 0),
    version_minor integer NOT NULL DEFAULT 0 CHECK (version_minor >= 0),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review_requested', 'returned', 'published', 'archived')),
    change_note text,
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (blueprint_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_blueprint_versions_status
    ON proc.blueprint_versions (status);

ALTER TABLE proc.blueprint_versions
    ADD COLUMN IF NOT EXISTS version_major integer NOT NULL DEFAULT 0;

ALTER TABLE proc.blueprint_versions
    ADD COLUMN IF NOT EXISTS version_minor integer NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS proc.approval_status_histories (
    approval_status_history_id bigserial PRIMARY KEY,
    target_type text NOT NULL CHECK (target_type IN ('source-doc')),
    target_id bigint NOT NULL,
    target_version_id bigint NOT NULL REFERENCES proc.blueprint_versions (blueprint_version_id) ON DELETE CASCADE,
    from_status text CHECK (from_status IN ('draft', 'review_requested', 'returned', 'published', 'archived')),
    to_status text NOT NULL CHECK (to_status IN ('draft', 'review_requested', 'returned', 'published', 'archived')),
    action_label text NOT NULL,
    changed_by text,
    changed_at timestamptz NOT NULL DEFAULT now(),
    note text
);

CREATE INDEX IF NOT EXISTS idx_approval_status_histories_target
    ON proc.approval_status_histories (target_type, target_id, changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_approval_status_histories_version
    ON proc.approval_status_histories (target_version_id);

CREATE TABLE IF NOT EXISTS proc.module_approval_status_histories (
    module_approval_status_history_id bigserial PRIMARY KEY,
    module_id bigint NOT NULL REFERENCES proc.modules (module_id) ON DELETE CASCADE,
    module_version_id bigint NOT NULL REFERENCES proc.module_versions (module_version_id) ON DELETE CASCADE,
    from_status text CHECK (from_status IN ('draft', 'review_requested', 'returned', 'published', 'archived')),
    to_status text NOT NULL CHECK (to_status IN ('draft', 'review_requested', 'returned', 'published', 'archived')),
    action_label text NOT NULL,
    changed_by text,
    changed_at timestamptz NOT NULL DEFAULT now(),
    note text
);

CREATE INDEX IF NOT EXISTS idx_module_approval_status_histories_module
    ON proc.module_approval_status_histories (module_id, changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_module_approval_status_histories_version
    ON proc.module_approval_status_histories (module_version_id);

CREATE TABLE IF NOT EXISTS proc.blueprint_items (
    blueprint_item_id bigserial PRIMARY KEY,
    blueprint_version_id bigint NOT NULL REFERENCES proc.blueprint_versions (blueprint_version_id) ON DELETE CASCADE,
    item_order integer NOT NULL CHECK (item_order > 0),
    module_version_id bigint NOT NULL REFERENCES proc.module_versions (module_version_id),
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (blueprint_version_id, item_order)
);

CREATE INDEX IF NOT EXISTS idx_blueprint_items_blueprint_version_id
    ON proc.blueprint_items (blueprint_version_id);

CREATE INDEX IF NOT EXISTS idx_blueprint_items_module_version_id
    ON proc.blueprint_items (module_version_id);

CREATE TABLE IF NOT EXISTS proc.case_documents (
    case_document_id bigserial PRIMARY KEY,
    case_document_key text NOT NULL UNIQUE,
    source_doc_id bigint NOT NULL,
    source_doc_version_id bigint NOT NULL,
    source_doc_key text NOT NULL,
    source_doc_name text NOT NULL,
    unit_config_id text NOT NULL,
    prefecture text NOT NULL,
    building text NOT NULL,
    context_json jsonb NOT NULL,
    workbook_path text NOT NULL,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS proc.case_document_targets (
    case_document_target_id bigserial PRIMARY KEY,
    case_document_id bigint NOT NULL REFERENCES proc.case_documents (case_document_id) ON DELETE CASCADE,
    target_no integer NOT NULL CHECK (target_no BETWEEN 1 AND 20),
    slot_key text NOT NULL,
    device_type text NOT NULL,
    system text,
    host_name text NOT NULL,
    UNIQUE (case_document_id, target_no)
);

CREATE TABLE IF NOT EXISTS proc.case_document_execution_items (
    execution_item_id bigserial PRIMARY KEY,
    case_document_id bigint NOT NULL REFERENCES proc.case_documents (case_document_id) ON DELETE CASCADE,
    module_row_id bigint,
    row_order integer NOT NULL CHECK (row_order > 0),
    target_no integer NOT NULL CHECK (target_no BETWEEN 1 AND 20),
    excel_cell text NOT NULL,
    major_no text,
    middle_no text,
    minor_no text,
    tech_doc_text text,
    work_text text,
    check_text text,
    window_text text,
    p_text text,
    command_text text,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'checked', 'skipped')),
    performed_at timestamptz,
    performed_by text,
    skip_reason text,
    lock_version integer NOT NULL DEFAULT 0 CHECK (lock_version >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_document_id, row_order, target_no)
);

ALTER TABLE proc.case_document_execution_items
    ADD COLUMN IF NOT EXISTS tech_doc_text text;
ALTER TABLE proc.case_document_execution_items
    ADD COLUMN IF NOT EXISTS window_text text;
ALTER TABLE proc.case_document_execution_items
    ADD COLUMN IF NOT EXISTS p_text text;

CREATE INDEX IF NOT EXISTS idx_case_document_execution_items_case_document
    ON proc.case_document_execution_items (case_document_id, row_order, target_no);

CREATE TABLE IF NOT EXISTS proc.case_document_execution_histories (
    history_id bigserial PRIMARY KEY,
    execution_item_id bigint NOT NULL REFERENCES proc.case_document_execution_items (execution_item_id) ON DELETE CASCADE,
    from_status text NOT NULL CHECK (from_status IN ('pending', 'checked', 'skipped')),
    to_status text NOT NULL CHECK (to_status IN ('pending', 'checked', 'skipped')),
    changed_at timestamptz NOT NULL DEFAULT now(),
    changed_by text,
    note text
);

CREATE INDEX IF NOT EXISTS idx_case_document_execution_histories_item
    ON proc.case_document_execution_histories (execution_item_id, changed_at);

INSERT INTO proc.modules (module_key, name, description)
VALUES
    ('MOD-001', '初期点検手順', '作業開始前の確認を行うモジュール'),
    ('MOD-002', '部品交換手順', '部品交換作業を行うモジュール'),
    ('MOD-003', '復旧確認手順', '作業後の復旧確認を行うモジュール')
ON CONFLICT (module_key)
DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    updated_at = now();

INSERT INTO proc.module_versions (
    module_id,
    version_no,
    status,
    change_note,
    source_xlsx_path,
    source_sha256,
    created_by
)
SELECT
    m.module_id,
    seed.version_no,
    seed.status,
    seed.change_note,
    seed.source_xlsx_path,
    seed.source_sha256,
    seed.created_by
FROM (
    VALUES
        ('MOD-001', 1, 'draft', 'Sprint 2 seed', NULL, NULL, 'seed'),
        ('MOD-002', 1, 'published', 'Sprint 2 seed', NULL, NULL, 'seed'),
        ('MOD-003', 1, 'archived', 'Sprint 2 seed', NULL, NULL, 'seed')
) AS seed(module_key, version_no, status, change_note, source_xlsx_path, source_sha256, created_by)
JOIN proc.modules m
    ON m.module_key = seed.module_key
ON CONFLICT (module_id, version_no)
DO UPDATE SET
    status = EXCLUDED.status,
    change_note = EXCLUDED.change_note,
    source_xlsx_path = EXCLUDED.source_xlsx_path,
    source_sha256 = EXCLUDED.source_sha256,
    created_by = EXCLUDED.created_by,
    updated_at = now();

INSERT INTO proc.module_rows (
    module_version_id,
    row_order,
    row_type,
    major_no,
    middle_no,
    minor_no,
    tech_doc_text,
    work_text,
    check_text_default,
    window_template_default,
    p_template_default,
    command_template_default
)
SELECT
    mv.module_version_id,
    seed.row_order,
    seed.row_type,
    seed.major_no,
    seed.middle_no,
    seed.minor_no,
    seed.tech_doc_text,
    seed.work_text,
    seed.check_text_default,
    seed.window_template_default,
    seed.p_template_default,
    seed.command_template_default
FROM (
    VALUES
        ('MOD-001', 1, 'header', '大', '中', '小', '技術資料名', '作業内容', '確認事項', 'window', 'P', 'コマンド'),
        ('MOD-001', 2, 'step', '1', '', '', '初期点検資料', '作業開始前の状態を確認する', '対象装置が作業可能な状態であること', '{{TARGET_DEVICE_HOSTNAME}}', '{{LOGIN_USER}}', 'show status'),
        ('MOD-001', 3, 'step', '1', '1', '', '初期点検資料', '作業開始前のログを取得する', 'ログ取得が完了していること', '{{TARGET_DEVICE_HOSTNAME}}', '{{LOGIN_USER}}', 'show log'),
        ('MOD-002', 1, 'header', '大', '中', '小', '技術資料名', '作業内容', '確認事項', 'window', 'P', 'コマンド'),
        ('MOD-002', 2, 'step', '2', '', '', '部品交換資料', '交換対象部品を確認する', '交換対象が一致していること', '{{TARGET_DEVICE_HOSTNAME}}', '{{LOGIN_USER}}', 'show inventory'),
        ('MOD-002', 3, 'step', '2', '1', '', '部品交換資料', '部品交換後の状態を確認する', '異常がないこと', '{{TARGET_DEVICE_HOSTNAME}}', '{{LOGIN_USER}}', 'show hardware'),
        ('MOD-003', 1, 'header', '大', '中', '小', '技術資料名', '作業内容', '確認事項', 'window', 'P', 'コマンド'),
        ('MOD-003', 2, 'step', '3', '', '', '復旧確認資料', '通信状態を確認する', '疎通が正常であること', '{{SBC_COMMAND_FLOATING_IP}}', '{{LOGIN_USER}}', 'ping {{SBC_COMMAND_FLOATING_IP}}'),
        ('MOD-003', 3, 'step', '3', '1', '', '復旧確認資料', '復旧後のサービス状態を確認する', 'サービスが正常であること', '{{TARGET_DEVICE_HOSTNAME}}', '{{LOGIN_USER}}', 'show service')
) AS seed(
    module_key,
    row_order,
    row_type,
    major_no,
    middle_no,
    minor_no,
    tech_doc_text,
    work_text,
    check_text_default,
    window_template_default,
    p_template_default,
    command_template_default
)
JOIN proc.modules m
    ON m.module_key = seed.module_key
JOIN proc.module_versions mv
    ON mv.module_id = m.module_id
    AND mv.version_no = 1
ON CONFLICT (module_version_id, row_order)
DO UPDATE SET
    row_type = EXCLUDED.row_type,
    major_no = EXCLUDED.major_no,
    middle_no = EXCLUDED.middle_no,
    minor_no = EXCLUDED.minor_no,
    tech_doc_text = EXCLUDED.tech_doc_text,
    work_text = EXCLUDED.work_text,
    check_text_default = EXCLUDED.check_text_default,
    window_template_default = EXCLUDED.window_template_default,
    p_template_default = EXCLUDED.p_template_default,
    command_template_default = EXCLUDED.command_template_default,
    updated_at = now();

-- Temporary module seeds based on the three Excel prototype files.
-- These rows intentionally keep the Excel-like A:M column structure so the
-- WebUI can preview modules in a familiar work sheet layout.
INSERT INTO proc.modules (module_key, name, description)
VALUES
    ('MOD-001', '01.ボーレート確認・修正_CS モジュール1', '添付Excel「モジュール1」を元にした事前準備用の仮モジュール'),
    ('MOD-002', '01.ボーレート確認・修正_CS モジュール2', '添付Excel「モジュール2」を元にした接続・確認・設定用の仮モジュール'),
    ('MOD-003', '01.ボーレート確認・修正_CS モジュール3', '添付Excel「モジュール3」を元にした完了連絡用の仮モジュール')
ON CONFLICT (module_key)
DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    updated_at = now();

INSERT INTO proc.module_versions (
    module_id,
    version_no,
    status,
    change_note,
    source_xlsx_path,
    source_sha256,
    created_by
)
SELECT
    m.module_id,
    seed.version_no,
    seed.status,
    seed.change_note,
    seed.source_xlsx_path,
    NULL,
    'excel-seed'
FROM (
    VALUES
        ('MOD-001', 1, 'draft', 'Excel prototype seed', '【TEST】01_ログイン確認_作業CS_モジュール1.xlsm'),
        ('MOD-002', 1, 'draft', 'Excel prototype seed', '【TEST】01_ログイン確認_作業CS_モジュール2.xlsm'),
        ('MOD-003', 1, 'draft', 'Excel prototype seed', '【TEST】01_ログイン確認_作業CS_モジュール3.xlsm')
) AS seed(module_key, version_no, status, change_note, source_xlsx_path)
JOIN proc.modules m
    ON m.module_key = seed.module_key
ON CONFLICT (module_id, version_no)
DO UPDATE SET
    status = EXCLUDED.status,
    change_note = EXCLUDED.change_note,
    source_xlsx_path = EXCLUDED.source_xlsx_path,
    source_sha256 = EXCLUDED.source_sha256,
    created_by = EXCLUDED.created_by,
    updated_at = now();

DELETE FROM proc.module_rows r
USING proc.module_versions mv
JOIN proc.modules m
    ON m.module_id = mv.module_id
WHERE r.module_version_id = mv.module_version_id
  AND mv.version_no = 1
  AND m.module_key IN ('MOD-001', 'MOD-002', 'MOD-003');

INSERT INTO proc.module_rows (
    module_version_id,
    row_order,
    row_type,
    major_no,
    middle_no,
    minor_no,
    tech_doc_text,
    work_text,
    check_text_default,
    time_text,
    window_template_default,
    p_template_default,
    command_template_default
)
SELECT
    mv.module_version_id,
    seed.row_order,
    seed.row_type,
    seed.major_no,
    seed.middle_no,
    seed.minor_no,
    seed.tech_doc_text,
    seed.work_text,
    seed.check_text_default,
    seed.time_text,
    seed.window_template_default,
    seed.p_template_default,
    seed.command_template_default
FROM (
    VALUES
        ('MOD-001', 6, 'header', '0', '0', '0', NULL, '大項番作業名', NULL, NULL, NULL, NULL, NULL),
        ('MOD-001', 7, 'step', '0', '1', '1', NULL, '作業で使用するPCのTeraTerm設定を下記の通り変更する。', NULL, NULL, NULL, NULL, NULL),
        ('MOD-001', 8, 'step', '0', '1', '2', NULL, '①TeraTermを起動し、「設定」→「その他の設定」→「ログ」を開く', 'ログ画面が開くこと', '□', NULL, 'TT', NULL),
        ('MOD-001', 9, 'step', '0', '1', '3', NULL, '②その他の設定画面で以下の通り設定する', '設定が完了すること', NULL, NULL, NULL, NULL),
        ('MOD-001', 10, 'step', NULL, NULL, NULL, NULL, '標準ログ・ファイル名', NULL, '□', NULL, 'TT', '{{TERATERM_LOG_FILE_NAME}}'),
        ('MOD-001', 11, 'step', NULL, NULL, NULL, NULL, '標準ログのログ保存先フォルダ', NULL, '□', NULL, 'TT', '{{TERATERM_LOG_FOLDER_NOTE}}'),
        ('MOD-001', 12, 'step', NULL, NULL, NULL, NULL, '自動的にログ採取を開始する', NULL, '□', NULL, 'TT', 'チェックを入れる'),
        ('MOD-001', 13, 'step', NULL, NULL, NULL, NULL, 'オプション-追記', NULL, '□', NULL, 'TT', 'チェックを入れる'),
        ('MOD-001', 14, 'step', NULL, NULL, NULL, NULL, 'オプション-プレーンテキスト', NULL, '□', NULL, 'TT', 'チェックを入れる'),
        ('MOD-001', 15, 'step', NULL, NULL, NULL, NULL, 'オプション-タイムスタンプ', NULL, '□', NULL, 'TT', 'チェックを入れる→ローカルタイム'),
        ('MOD-001', 16, 'step', '0', '1', '4', NULL, '③OKを押し、「設定」→「設定の保存」を実施する。', '設定が保存できること', '□', NULL, 'TT', NULL),
        ('MOD-001', 18, 'step', '0', '2', '1', NULL, '作業端末(Windows)の時刻設定を実施する。(ずれている場合のみでOK)', NULL, NULL, NULL, NULL, NULL),
        ('MOD-001', 19, 'step', '0', '2', '2', NULL, '①タスクバーの時計を右クリックし「日付と時刻の調整」を選択する。', '日付と時刻の調整が開くこと', '□', NULL, 'WIN', NULL),
        ('MOD-001', 20, 'step', '0', '2', '3', NULL, '②右記サーバと時刻同期を行う', '同期が成功すること', '□', NULL, 'WIN', '{{SBC_COMMAND_FLOATING_IP}}'),
        ('MOD-001', 22, 'step', '0', '3', '1', NULL, '装置が同一TTSに接続されていることを確認する', '工事情報入力シートを確認してTTSホスト名がすべて同一であること', '□', NULL, 'chk', NULL),
        ('MOD-001', 24, 'step', '0', '4', '1', NULL, 'XXX番号を伝えて工事開始連絡を行う　※対象TTSが商用INしている場合', '正常に工事開始連絡できること', '□', NULL, 'chk', NULL),
        ('MOD-001', 25, 'step', '0', '4', '2', NULL, '連絡先：{{WORK_CONTACT_PHONE}}', NULL, NULL, NULL, NULL, NULL),
        ('MOD-001', 38, 'meta', NULL, NULL, NULL, NULL, '連絡事項', NULL, NULL, NULL, NULL, NULL),
        ('MOD-002', 6, 'header', '1', '0', '0', NULL, '大項番作業名', NULL, NULL, NULL, NULL, NULL),
        ('MOD-002', 7, 'step', '1', '1', '1', NULL, 'TeraTermを起動し、TTSに右記設定で接続する', 'ホスト：', '□', NULL, 'TT', '{{SBC_COMMAND_FLOATING_IP}}'),
        ('MOD-002', 8, 'step', NULL, NULL, NULL, NULL, NULL, 'サービス：', '□', NULL, 'TT', '{{TTS_SERVICE}}'),
        ('MOD-002', 9, 'step', NULL, NULL, NULL, NULL, NULL, 'TCPポート：', '□', NULL, 'TT', '{{TTS_PORT}}'),
        ('MOD-002', 10, 'step', NULL, NULL, NULL, NULL, NULL, 'ユーザ名：', '□', NULL, 'TT', '{{LOGIN_USER}}'),
        ('MOD-002', 11, 'step', NULL, NULL, NULL, NULL, NULL, 'パスフレーズ：', '□', NULL, 'TT', '{{LOGIN_PASSWORD}}'),
        ('MOD-002', 12, 'step', NULL, NULL, NULL, NULL, NULL, 'メニューに表示されるホスト名が{{TTS_MENU_HOSTNAME}}であること', '□', NULL, 'chk', NULL),
        ('MOD-002', 14, 'step', '1', '2', '1', NULL, '特権モードに変更する', 'コマンドエラーないこと', '□', NULL, '>', 'su'),
        ('MOD-002', 15, 'step', NULL, NULL, NULL, NULL, NULL, 'Password：', '□', NULL, ':', '{{PRIVILEGED_PASSWORD}}'),
        ('MOD-002', 17, 'step', '1', '3', '1', NULL, 'コマンドの表示形式を変更する', 'コマンドエラーないこと', '□', NULL, '#', '{{CONFIG_OUTPUT_FORMAT_COMMAND}}'),
        ('MOD-002', 19, 'step', '1', '4', '1', NULL, 'コンフィグを確認する', '各装置向けポートのボーレート値が想定通りであること', '□', NULL, '#', '{{TTS_SHOW_TTY_COMMAND}}'),
        ('MOD-002', 20, 'step', NULL, NULL, NULL, NULL, NULL, '{{TTS_TARGET_PORT_PRIMARY}}', '□', NULL, 'Eck', '{{TTS_EXPECTED_BAUD_PRIMARY}}'),
        ('MOD-002', 21, 'step', NULL, NULL, NULL, NULL, NULL, '{{TTS_TARGET_PORT_SECONDARY}}', '□', NULL, 'Eck', '{{TTS_EXPECTED_BAUD_SECONDARY}}'),
        ('MOD-002', 23, 'step', NULL, NULL, NULL, NULL, NULL, '各装置向けポートのボーレート値が想定通りであること', '□', NULL, '#', '{{CONFIG_SHOW_COMMAND}}'),
        ('MOD-002', 24, 'step', NULL, NULL, NULL, NULL, NULL, '※xxxxの場合表示されない', NULL, NULL, NULL, NULL),
        ('MOD-002', 25, 'step', NULL, NULL, NULL, NULL, NULL, '{{TTS_TARGET_PORT_PRIMARY}}', '□', NULL, 'Eck', '{{TTS_EXPECTED_BAUD_PRIMARY}}'),
        ('MOD-002', 27, 'step', '1', '5', '1', NULL, 'ボーレート値が想定と異なる場合、エスカレの上実施', NULL, NULL, NULL, NULL, NULL),
        ('MOD-002', 28, 'step', '1', '5', '2', NULL, 'ボーレート値の設定変更　※対象ポートに対して実施', 'コマンドエラーないこと', '□', NULL, '#', '{{TTS_SET_TTY_BAUD_COMMAND}}'),
        ('MOD-002', 30, 'step', '1', '5', '3', NULL, '設定後コンフィグを確認する', '各装置向けポートのボーレート値が想定通りであること', '□', NULL, '#', '{{TTS_SHOW_TTY_COMMAND}}'),
        ('MOD-002', 31, 'step', NULL, NULL, NULL, NULL, NULL, '{{TTS_TARGET_PORT_PRIMARY}}', '□', NULL, 'Eck', '{{TTS_EXPECTED_BAUD_PRIMARY}}'),
        ('MOD-002', 33, 'step', NULL, NULL, NULL, NULL, NULL, '各装置向けポートのボーレート値が想定通りであること', '□', NULL, '#', '{{CONFIG_SHOW_COMMAND}}'),
        ('MOD-002', 34, 'step', NULL, NULL, NULL, NULL, NULL, '※9600の場合表示されない', NULL, NULL, NULL, NULL),
        ('MOD-002', 35, 'step', NULL, NULL, NULL, NULL, NULL, '{{TTS_TARGET_PORT_PRIMARY}}', '□', NULL, 'Eck', '{{TTS_EXPECTED_BAUD_PRIMARY}}'),
        ('MOD-002', 37, 'step', '1', '5', '4', NULL, 'Configを保存する', '「TEST？ 」と表示されること', '□', NULL, '#', '{{CONFIG_SAVE_COMMAND}}'),
        ('MOD-002', 38, 'step', NULL, NULL, NULL, NULL, NULL, 'エラーが発生しないこと', '□', NULL, '?', '{{CONFIRM_YES}}'),
        ('MOD-002', 39, 'step', NULL, NULL, NULL, NULL, NULL, '「TEST？ 」と表示されること', '□', NULL, '#', '{{CONFIG_SAVE_COMMAND}}'),
        ('MOD-002', 40, 'step', NULL, NULL, NULL, NULL, NULL, 'エラーが発生しないこと', '□', NULL, '?', '{{CONFIRM_YES}}'),
        ('MOD-002', 41, 'step', NULL, NULL, NULL, NULL, NULL, 'エラーが発生しないこと', '□', NULL, '#', '{{STARTUP_CONFIG_SHOW_COMMAND}}'),
        ('MOD-002', 42, 'step', NULL, NULL, NULL, NULL, NULL, 'ツールで比較して「{{CONFIG_SHOW_COMMAND}}」と差分ないこと', '□', NULL, 'DF', NULL),
        ('MOD-002', 46, 'step', '1', '6', '1', NULL, 'ログアウトする', NULL, '□', NULL, '#', 'exit'),
        ('MOD-002', 47, 'step', NULL, NULL, NULL, NULL, NULL, '正常にログアウトできること', '□', NULL, '>', 'exit'),
        ('MOD-002', 53, 'meta', NULL, NULL, NULL, NULL, '連絡事項', NULL, NULL, NULL, NULL, NULL),
        ('MOD-003', 6, 'header', '2', '0', '0', NULL, NULL, NULL, NULL, NULL, NULL, NULL),
        ('MOD-003', 7, 'step', '2', '1', '1', NULL, '番号を伝えて工事完了連絡を行う　※対象TTSが商用INしている場合', '正常に工事完了連絡できること', '□', NULL, 'chk', NULL),
        ('MOD-003', 8, 'step', '2', '1', '2', NULL, '連絡先：{{WORK_CONTACT_PHONE}}', NULL, NULL, NULL, NULL, NULL),
        ('MOD-003', 13, 'meta', NULL, NULL, NULL, NULL, '連絡事項', NULL, NULL, NULL, NULL, NULL)
) AS seed(
    module_key,
    row_order,
    row_type,
    major_no,
    middle_no,
    minor_no,
    tech_doc_text,
    work_text,
    check_text_default,
    time_text,
    window_template_default,
    p_template_default,
    command_template_default
)
JOIN proc.modules m
    ON m.module_key = seed.module_key
JOIN proc.module_versions mv
    ON mv.module_id = m.module_id
    AND mv.version_no = 1;

UPDATE proc.module_rows AS r
SET indent_level = updates.indent_level
FROM proc.module_versions AS mv
JOIN proc.modules AS m
    ON m.module_id = mv.module_id
JOIN (
    VALUES
        ('MOD-001', 6, 0),
        ('MOD-001', 7, 0),
        ('MOD-001', 8, 1),
        ('MOD-001', 9, 1),
        ('MOD-001', 10, 2),
        ('MOD-001', 11, 2),
        ('MOD-001', 12, 2),
        ('MOD-001', 13, 2),
        ('MOD-001', 14, 2),
        ('MOD-001', 15, 2),
        ('MOD-001', 16, 1),
        ('MOD-001', 18, 0),
        ('MOD-001', 19, 1),
        ('MOD-001', 20, 1),
        ('MOD-001', 22, 0),
        ('MOD-001', 24, 0),
        ('MOD-001', 25, 1),
        ('MOD-001', 38, 0),
        ('MOD-002', 6, 0),
        ('MOD-002', 7, 0),
        ('MOD-002', 14, 0),
        ('MOD-002', 17, 0),
        ('MOD-002', 19, 0),
        ('MOD-002', 27, 0),
        ('MOD-002', 28, 1),
        ('MOD-002', 30, 1),
        ('MOD-002', 37, 1),
        ('MOD-002', 46, 0),
        ('MOD-002', 53, 0),
        ('MOD-003', 7, 0),
        ('MOD-003', 8, 1),
        ('MOD-003', 13, 0)
) AS updates(module_key, row_order, indent_level)
    ON updates.module_key = m.module_key
WHERE r.module_version_id = mv.module_version_id
  AND r.row_order = updates.row_order;

INSERT INTO proc.blueprints (blueprint_key, name, description)
VALUES
    ('BP-STD-001', 'M1確認用 原本A', '初期点検と部品交換を組み合わせた確認用原本'),
    ('BP-STD-002', 'M1確認用 原本B', '復旧確認を中心にした確認用原本')
ON CONFLICT (blueprint_key)
DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    updated_at = now();

INSERT INTO proc.blueprint_versions (
    blueprint_id,
    version_no,
    status,
    change_note,
    created_by
)
SELECT
    b.blueprint_id,
    seed.version_no,
    seed.status,
    seed.change_note,
    seed.created_by
FROM (
    VALUES
        ('BP-STD-001', 1, 'draft', 'Sprint 2 seed', 'seed'),
        ('BP-STD-002', 1, 'published', 'Sprint 2 seed', 'seed')
) AS seed(blueprint_key, version_no, status, change_note, created_by)
JOIN proc.blueprints b
    ON b.blueprint_key = seed.blueprint_key
ON CONFLICT (blueprint_id, version_no)
DO UPDATE SET
    status = EXCLUDED.status,
    change_note = EXCLUDED.change_note,
    created_by = EXCLUDED.created_by,
    updated_at = now();

INSERT INTO proc.blueprint_items (
    blueprint_version_id,
    item_order,
    module_version_id,
    enabled
)
SELECT
    bv.blueprint_version_id,
    seed.item_order,
    mv.module_version_id,
    seed.enabled
FROM (
    VALUES
        ('BP-STD-001', 1, 'MOD-001', true),
        ('BP-STD-001', 2, 'MOD-002', true),
        ('BP-STD-002', 1, 'MOD-003', true)
) AS seed(blueprint_key, item_order, module_key, enabled)
JOIN proc.blueprints b
    ON b.blueprint_key = seed.blueprint_key
JOIN proc.blueprint_versions bv
    ON bv.blueprint_id = b.blueprint_id
    AND bv.version_no = 1
JOIN proc.modules m
    ON m.module_key = seed.module_key
JOIN proc.module_versions mv
    ON mv.module_id = m.module_id
    AND mv.version_no = 1
ON CONFLICT (blueprint_version_id, item_order)
DO UPDATE SET
    module_version_id = EXCLUDED.module_version_id,
    enabled = EXCLUDED.enabled,
    updated_at = now();

UPDATE proc.module_versions
SET device_headers_json = jsonb_build_array(
    jsonb_build_object(
        'slot_no', 1,
        'header_time_text', header_time_text,
        'target_text', target_text,
        'p_text', common_p_text,
        'target_device_text', target_device_text
    )
)
WHERE device_headers_json = '[]'::jsonb;

UPDATE proc.module_rows
SET device_entries_json = jsonb_build_array(
    jsonb_build_object(
        'slot_no', 1,
        'time_text', time_text,
        'window_text', window_template_default,
        'p_text', p_template_default,
        'command_text', command_template_default
    )
)
WHERE device_entries_json = '[]'::jsonb;

INSERT INTO app_metadata (key, value)
VALUES ('schema_version', '0.5.0')
ON CONFLICT (key)
DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = now();

