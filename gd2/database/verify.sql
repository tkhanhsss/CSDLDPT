-- Read-only inspection queries, e.g. in DB Browser for SQLite.
PRAGMA foreign_keys = ON;
PRAGMA integrity_check;
PRAGMA foreign_key_check;

SELECT build_id, status, created_at, n_docs, n_terms, nnz FROM build_info;
SELECT 'build_info' AS table_name, COUNT(*) AS row_count FROM build_info
UNION ALL SELECT 'labels', COUNT(*) FROM labels
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'terms', COUNT(*) FROM terms
UNION ALL SELECT 'document_terms', COUNT(*) FROM document_terms;

-- Must return no rows: stored df versus the number of document-term rows.
SELECT t.term_id, t.term_text, t.df, COUNT(dt.doc_id) AS actual_df
FROM terms AS t LEFT JOIN document_terms AS dt ON t.term_id = dt.term_id
GROUP BY t.term_id HAVING t.df != COUNT(dt.doc_id);

SELECT MIN(df) AS min_df, MAX(df) AS max_df, MIN(idf) AS min_idf, MAX(idf) AS max_idf FROM terms;
SELECT MIN(norm_squared) AS min_norm_squared, MAX(norm_squared) AS max_norm_squared
FROM (SELECT doc_id, SUM(weight * weight) AS norm_squared FROM document_terms GROUP BY doc_id);

SELECT label_code, COUNT(*) AS n_docs FROM documents GROUP BY label_code ORDER BY label_code;
SELECT doc_id, filename, title, author_display FROM documents ORDER BY doc_id LIMIT 10;

-- Inspect the first document's weights and exact integer term counts.
SELECT d.filename, t.term_id, t.term_text, dt.term_count, t.df, t.idf, d.l2_raw, dt.weight
FROM document_terms AS dt JOIN documents AS d USING (doc_id) JOIN terms AS t USING (term_id)
WHERE dt.doc_id = 1 ORDER BY dt.weight DESC, t.term_id LIMIT 10;
