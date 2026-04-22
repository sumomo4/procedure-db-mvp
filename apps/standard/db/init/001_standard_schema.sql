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
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proc.module_versions (
    module_version_id bigserial PRIMARY KEY,
    module_id bigint NOT NULL REFERENCES proc.modules (module_id),
    version_no integer NOT NULL CHECK (version_no > 0),
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    change_note text,
    source_xlsx_path text,
    source_sha256 text,
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (module_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_module_versions_status
    ON proc.module_versions (status);

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
    check_text_default text,
    window_template_default text,
    p_template_default text,
    command_template_default text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (module_version_id, row_order)
);

CREATE INDEX IF NOT EXISTS idx_module_rows_module_version_id
    ON proc.module_rows (module_version_id);

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
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    change_note text,
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (blueprint_id, version_no)
);

CREATE INDEX IF NOT EXISTS idx_blueprint_versions_status
    ON proc.blueprint_versions (status);

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
        ('MOD-001', 2, 'step', '1', '', '', '初期点検資料', '作業開始前の状態を確認する', '対象装置が作業可能な状態であること', '{{HOST}}', '{{USER}}', 'show status'),
        ('MOD-001', 3, 'step', '1', '1', '', '初期点検資料', '作業開始前のログを取得する', 'ログ取得が完了していること', '{{HOST}}', '{{USER}}', 'show log'),
        ('MOD-002', 1, 'header', '大', '中', '小', '技術資料名', '作業内容', '確認事項', 'window', 'P', 'コマンド'),
        ('MOD-002', 2, 'step', '2', '', '', '部品交換資料', '交換対象部品を確認する', '交換対象が一致していること', '{{DEVICE_NAME}}', '{{USER}}', 'show inventory'),
        ('MOD-002', 3, 'step', '2', '1', '', '部品交換資料', '部品交換後の状態を確認する', '異常がないこと', '{{DEVICE_NAME}}', '{{USER}}', 'show hardware'),
        ('MOD-003', 1, 'header', '大', '中', '小', '技術資料名', '作業内容', '確認事項', 'window', 'P', 'コマンド'),
        ('MOD-003', 2, 'step', '3', '', '', '復旧確認資料', '通信状態を確認する', '疎通が正常であること', '{{NW_ADDRESS}}', '{{USER}}', 'ping {{NW_ADDRESS}}'),
        ('MOD-003', 3, 'step', '3', '1', '', '復旧確認資料', '復旧後のサービス状態を確認する', 'サービスが正常であること', '{{HOST}}', '{{USER}}', 'show service')
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

INSERT INTO app_metadata (key, value)
VALUES ('schema_version', '0.2.0')
ON CONFLICT (key)
DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = now();
