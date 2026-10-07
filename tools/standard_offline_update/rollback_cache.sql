\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
-- The old application cannot distinguish the new normalization algorithm.
-- Only derived signatures are removed; module rows and images are untouched.
ALTER TABLE proc.module_similarity_signatures
ADD COLUMN IF NOT EXISTS algorithm_version integer NOT NULL DEFAULT 1;
ALTER TABLE proc.module_similarity_signatures
ALTER COLUMN algorithm_version SET DEFAULT 1;
DELETE FROM proc.module_similarity_signatures;
COMMIT;
