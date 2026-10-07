-- Parameterized query used by a future BigQuery runtime adapter.
-- Parameters: query_embedding ARRAY<FLOAT64>, customer_id STRING,
-- equipment_type STRING, document_type STRING, effective_on DATE, top_k INT64.

SELECT
  base.* EXCEPT (embedding),
  1 - distance AS score
FROM VECTOR_SEARCH(
  (
    SELECT *
    FROM `${PROJECT_ID}.${DATASET_ID}.knowledge_chunks`
    WHERE (@customer_id IS NULL OR customer_id = @customer_id)
      AND (@equipment_type IS NULL OR equipment_type = @equipment_type)
      AND (@document_type IS NULL OR document_type = @document_type)
      AND (
        @effective_on IS NULL
        OR effective_date IS NULL
        OR effective_date <= @effective_on
      )
  ),
  'embedding',
  query_value => @query_embedding,
  top_k => @top_k,
  distance_type => 'COSINE'
)
ORDER BY distance, base.document_id, base.chunk_id;
