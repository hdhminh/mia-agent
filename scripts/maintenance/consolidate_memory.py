#!/usr/bin/env python3
"""Consolidate duplicate memory items: mark older copies as superseded.

Reads MIA_POSTGRES_URI from the environment. Safe to run periodically.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from psycopg_pool import ConnectionPool


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.memory.repository import MemoryRepository  # noqa: E402


def main() -> int:
    uri = os.getenv("MIA_POSTGRES_URI", "")
    if not uri:
        print("MIA_POSTGRES_URI is required.", file=sys.stderr)
        return 1
    owner_id = str(os.getenv("MIA_MEMORY_OWNER_ID", "") or "").strip()
    schema_path = ROOT / "infra" / "sql" / "memory_schema.sql"
    if not schema_path.exists():
        schema_path = ROOT / "sql" / "memory_schema.sql"

    pool = ConnectionPool(conninfo=uri, open=True)
    try:
        repo = MemoryRepository(pool=pool, embedder_url="http://localhost:8010/embed", timeout_seconds=30, schema_path=schema_path)
        result = repo.consolidate(owner_id=owner_id)
    finally:
        pool.close()

    print(f"Checked {result['checked']} memory items; superseded {result['superseded']} duplicates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
