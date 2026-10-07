-- Phase 5: accelerate semantic retrieval over knowledge_chunks.
-- Replace PROJECT_ID and DATASET_ID through the deployment pipeline.

CREATE VECTOR INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
ON `${PROJECT_ID}.${DATASET_ID}.knowledge_chunks`(embedding)
STORING(
  chunk_id,
  document_id,
  customer_id,
  equipment_type,
  document_type,
  version,
  effective_date,
  text,
  metadata
)
OPTIONS(
  index_type = 'IVF',
  distance_type = 'COSINE'
);
