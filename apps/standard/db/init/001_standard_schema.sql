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
    deleted_at timestamptz,
    deleted_by text,
    delete_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proc.app_users (
    user_id bigserial PRIMARY KEY,
    username text NOT NULL,
    display_name text NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('member', 'approver', 'admin')),
    is_active boolean NOT NULL DEFAULT true,
    must_change_password boolean NOT NULL DEFAULT false,
    failed_login_count integer NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until timestamptz,
    last_login_at timestamptz,
    deleted_at timestamptz,
    deleted_by text,
    delete_reason text,
    password_changed_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE proc.app_users
    ADD COLUMN IF NOT EXISTS must_change_password boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_by text,
    ADD COLUMN IF NOT EXISTS delete_reason text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_username_lower
    ON proc.app_users (lower(username));

CREATE INDEX IF NOT EXISTS idx_app_users_deleted_at
    ON proc.app_users (deleted_at);

CREATE TABLE IF NOT EXISTS proc.auth_sessions (
    auth_session_id bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES proc.app_users (user_id) ON DELETE CASCADE,
    token_hash varchar(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id
    ON proc.auth_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
    ON proc.auth_sessions (expires_at);

ALTER TABLE proc.modules
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_by text,
    ADD COLUMN IF NOT EXISTS delete_reason text;

CREATE INDEX IF NOT EXISTS idx_modules_deleted_at
    ON proc.modules (deleted_at);

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
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    deleted_by text,
    delete_reason text
);

ALTER TABLE proc.blueprints
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

ALTER TABLE proc.blueprints
    ADD COLUMN IF NOT EXISTS deleted_by text;

ALTER TABLE proc.blueprints
    ADD COLUMN IF NOT EXISTS delete_reason text;

CREATE INDEX IF NOT EXISTS idx_blueprints_deleted_at
    ON proc.blueprints (deleted_at);

CREATE TABLE IF NOT EXISTS proc.blueprint_tag_memberships (
    blueprint_id bigint NOT NULL REFERENCES proc.blueprints (blueprint_id) ON DELETE CASCADE,
    tag_path text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (blueprint_id, tag_path)
);

CREATE INDEX IF NOT EXISTS idx_blueprint_tag_memberships_tag_path
    ON proc.blueprint_tag_memberships (tag_path);

INSERT INTO proc.blueprint_tag_memberships (blueprint_id, tag_path)
SELECT blueprint_id, '未分類'
FROM proc.blueprints
ON CONFLICT (blueprint_id, tag_path) DO NOTHING;

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

CREATE TABLE IF NOT EXISTS proc.blueprint_item_row_numbers (
    blueprint_item_row_number_id bigserial PRIMARY KEY,
    blueprint_item_id bigint NOT NULL REFERENCES proc.blueprint_items (blueprint_item_id) ON DELETE CASCADE,
    module_row_id bigint NOT NULL REFERENCES proc.module_rows (module_row_id),
    major_no text,
    middle_no text,
    minor_no text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (blueprint_item_id, module_row_id)
);

CREATE INDEX IF NOT EXISTS idx_blueprint_item_row_numbers_item
    ON proc.blueprint_item_row_numbers (blueprint_item_id);

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
    preparation_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    workbook_path text NOT NULL,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

ALTER TABLE proc.case_documents
    ADD COLUMN IF NOT EXISTS preparation_json jsonb NOT NULL DEFAULT '{}'::jsonb;

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


-- Runtime sample modules and blueprints are intentionally not inserted.
-- Automated tests create isolated fixtures; demo data must be imported explicitly.

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

