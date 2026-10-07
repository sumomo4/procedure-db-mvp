\set ON_ERROR_STOP on
SELECT format(
'SELECT json_build_array(%L, count(*), md5(COALESCE(string_agg(md5(row_to_json(t)::text), '''' ORDER BY md5(row_to_json(t)::text)), '''')))::text FROM %I.%I t;',
schemaname || '.' || tablename, schemaname, tablename)
FROM pg_tables
WHERE schemaname IN ('proc', 'public')
AND tablename <> 'module_similarity_signatures'
ORDER BY schemaname, tablename
\gexec
