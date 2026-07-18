# Mia Memory RAG Upgrade

This upgrade keeps PostgreSQL as the source of truth and turns Mia memory into retrieval-augmented memory instead of a tool the model may or may not call.

## What Changed

- Owner-scoped memory retrieval uses `owner_id` so Telegram, web, and future channels can share memory for the same owner without leaking across users.
- Retrieval now runs before the supervisor for meaningful requests and injects a short memory context into the specialist prompt.
- Memory search combines dense pgvector ranking with lexical ranking and Reciprocal Rank Fusion.
- Memory proposals are stored separately in `mia_memory_proposals`; automatic memories require user approval before becoming official durable memory.
- The schema prepares for PostgreSQL 17 plus `pg_textsearch`, but falls back to `pg_trgm` when `pg_textsearch` is not installed.

## Recommended PostgreSQL 17 Cutover

Do not point the existing `pg_data` PostgreSQL 16 volume at PostgreSQL 17 directly. Use dump and restore.

`pg_textsearch` currently targets PostgreSQL 17/18, so the current PostgreSQL 16 container is expected to run with the `pg_trgm` fallback until a planned cutover happens.

1. Back up the current database:

```bash
docker exec postgres pg_dump -U "${POSTGRES_USER:-n8n}" -d "${POSTGRES_DB:-vectordb}" -Fc -f /tmp/mia_pg16.dump
docker cp postgres:/tmp/mia_pg16.dump ./backups/mia_pg16_$(date +%Y%m%d_%H%M%S).dump
```

2. Start a PostgreSQL 17 candidate on a new volume.

Use a separate compose override or a temporary service with a new volume such as `pg_data_17`. Install `pgvector` and `pg_textsearch` in that image when available.

3. Restore into the new database:

```bash
docker cp ./backups/mia_pg16_latest.dump postgres17:/tmp/mia_pg16.dump
docker exec postgres17 pg_restore -U "${POSTGRES_USER:-n8n}" -d "${POSTGRES_DB:-vectordb}" --clean --if-exists /tmp/mia_pg16.dump
```

4. Run Mia schema setup.

Starting `mia-core` runs `infra/sql/memory_schema.sql`. Confirm these tables/columns exist:

```sql
SELECT count(*) FROM mia_memory_items;
SELECT count(*) FROM mia_memory_chunks;
SELECT count(*) FROM mia_memory_proposals;
SELECT count(*) FROM mia_memory_relations;
SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm', 'pg_textsearch');
```

5. Smoke test retrieval:

```bash
python scripts/maintenance/eval_memory_rag.py
python -m unittest tests.test_memory_rag -v
```

6. Keep the old `pg_data` volume until Mia has passed real chat tests.

Rollback is switching `MIA_POSTGRES_URI` and compose back to the PostgreSQL 16 service/volume, then restarting `mia-core`.

## Acceptance Checks

- No cross-owner retrieval: all automatic RAG retrieval passes `owner_id`.
- No unapproved automatic memory save: auto-detected memories enter `mia_memory_proposals`.
- Explicit user memory writes still save immediately through `memory_write`.
- Offline golden evaluation passes `Recall@5 >= 0.90` and `MRR >= 0.70`.
- `python -m unittest discover -s tests -v` passes before deployment.

## References

- pgvector supports hybrid search patterns with PostgreSQL full-text search and vector indexes: https://github.com/pgvector/pgvector
- pg_textsearch provides BM25 search and supports PostgreSQL 17/18: https://github.com/timescale/pg_textsearch
- PostgreSQL announcement for pg_textsearch v1.0: https://www.postgresql.org/about/news/pg_textsearch-v10-3264/
