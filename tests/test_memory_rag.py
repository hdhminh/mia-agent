from __future__ import annotations

import unittest

from agent.graph.nodes.memory_retriever import should_retrieve_memory
from agent.memory.repository import build_memory_context, looks_like_durable_memory


class MemoryRagHeuristicTests(unittest.TestCase):
    def test_retrieval_skips_low_signal_messages(self) -> None:
        for text in ("hi", "ok", "ừ", "test"):
            self.assertFalse(should_retrieve_memory(text), text)
        self.assertTrue(should_retrieve_memory("thêm section about vào demo-coffee"))

    def test_memory_context_has_budget_and_metadata(self) -> None:
        rows = [
            {
                "memory_type": "preference",
                "memory_kind": "semantic",
                "title": "Code workspace",
                "chunk_text": "User prefers continuing on the active code project without asking again.",
            },
            {
                "memory_type": "project",
                "memory_kind": "episodic",
                "title": "demo-coffee",
                "chunk_text": "demo-coffee is the current landing page project.",
            },
        ]
        context = build_memory_context(rows, token_budget=120)
        self.assertIn("retrieve tự động", context)
        self.assertIn("[semantic/preference]", context)
        self.assertLessEqual(len(context), 500)

    def test_proposal_prefilter_keeps_stable_preferences_and_rejects_secrets(self) -> None:
        self.assertTrue(looks_like_durable_memory("từ giờ ưu tiên trả lời thuần tiếng Việt cho mình nhé"))
        self.assertFalse(looks_like_durable_memory("api key của mình là sk-abc123456789012345678901234567890"))


class MemorySchemaContractTests(unittest.TestCase):
    def test_memory_schema_contains_rag_tables_and_owner_scope(self) -> None:
        from pathlib import Path

        schema = Path("infra/sql/memory_schema.sql").read_text(encoding="utf-8")
        for marker in (
            "owner_id TEXT NOT NULL",
            "mia_memory_relations",
            "mia_memory_proposals",
            "pg_textsearch",
            "idx_mia_memory_chunks_embedding_hnsw",
        ):
            self.assertIn(marker, schema)

    def test_offline_memory_rag_eval_meets_acceptance_floor(self) -> None:
        from pathlib import Path

        from scripts.maintenance.eval_memory_rag import evaluate

        result = evaluate(Path("tests/fixtures/memory_rag_golden.json"), k=5)
        self.assertGreaterEqual(float(result["recall_at_5"]), 0.9)
        self.assertGreaterEqual(float(result["mrr"]), 0.7)


class MemoryToolSelectionTests(unittest.TestCase):
    def test_memory_proposal_tools_are_selected_for_approval_language(self) -> None:
        from agent.brain.capability_broker import CapabilityBroker
        from agent.tool_specs import ToolCatalog

        broker = CapabilityBroker(ToolCatalog.load())
        selected = broker.select_tool_names(
            query="duyệt memory #12",
            domain="general",
            available=[
                "memory_search",
                "memory_recent",
                "memory_write",
                "memory_pending_proposals",
                "memory_accept_proposal",
                "memory_reject_proposal",
                "weather_get",
            ],
            limit=6,
        )
        self.assertIn("memory_accept_proposal", selected)


if __name__ == "__main__":
    unittest.main()
