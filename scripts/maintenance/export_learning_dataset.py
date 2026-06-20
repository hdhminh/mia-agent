from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import Settings
from agent.learning.repository import LearningRepository


def _event_to_example(row: dict[str, Any]) -> dict[str, Any] | None:
    user_text = str(row.get("user_text") or "").strip()
    final_text = str(row.get("final_text") or "").strip()
    if not user_text or not final_text:
        return None
    scope = str(row.get("scope") or "general").strip()
    topic = str(row.get("topic") or "").strip()
    tools_called = row.get("tools_called") or []
    metadata = row.get("metadata") or {}
    issue_type = str(row.get("issue_type") or "").strip()
    prompt = [
        "Bạn là Mia, trợ lý AI của hệ thống.",
        f"Scope: {scope}",
    ]
    if topic:
        prompt.append(f"Topic: {topic}")
    if tools_called:
        prompt.append(f"Tools: {', '.join(str(item) for item in tools_called)}")
    if issue_type:
        prompt.append(f"Issue: {issue_type}")
    prompt.append("Hãy trả lời tự nhiên bằng tiếng Việt, đúng ngữ cảnh.")
    return {
        "messages": [
            {"role": "system", "content": "\n".join(prompt)},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": final_text},
        ],
        "metadata": {
            "source": row.get("source") or "chat",
            "scope": scope,
            "topic": topic,
            "tools_called": tools_called,
            "issue_type": issue_type,
            "cache_hit": bool(row.get("cache_hit")),
            "cached_tokens": int(row.get("cached_tokens") or 0),
            "prompt_tokens": int(row.get("prompt_tokens") or 0),
            "completion_tokens": int(row.get("completion_tokens") or 0),
            "total_tokens": int(row.get("total_tokens") or 0),
            "metadata": metadata,
        },
    }


def _feedback_to_example(row: dict[str, Any]) -> dict[str, Any] | None:
    comment = str(row.get("comment") or "").strip()
    correction = str(row.get("correction_text") or "").strip()
    current = str(row.get("current_text") or "").strip()
    verdict = str(row.get("verdict") or "").strip()
    if not (comment or correction or current):
        return None
    prompt = [
        "Bạn là Mia, trợ lý AI của hệ thống.",
        "Hãy học từ phản hồi người dùng để sửa cách trả lời trong tương lai.",
    ]
    if verdict:
        prompt.append(f"Verdict: {verdict}")
    if comment:
        prompt.append(f"Comment: {comment}")
    user_text = correction or comment or current
    assistant_text = correction or current or comment
    return {
        "messages": [
            {"role": "system", "content": "\n".join(prompt)},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        "metadata": {
            "source": row.get("source") or "chat",
            "scope": row.get("scope") or "general",
            "topic": row.get("topic") or "",
            "verdict": verdict,
            "rating": int(row.get("rating") or 0),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Mia learning examples for future fine-tuning.")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL path.")
    parser.add_argument("--days", type=int, default=30, help="How many days of history to export.")
    parser.add_argument("--include-feedback", action="store_true", help="Also export feedback examples.")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of rows to inspect.")
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(conninfo=settings.postgres_uri, open=True)
    learning_repo = LearningRepository(pool=pool)
    learning_repo.setup()

    try:
        rows = learning_repo.recent_events(limit=max(1, args.limit), days=max(1, args.days))
        examples: list[dict[str, Any]] = []
        for row in rows:
            example = _event_to_example(row)
            if example:
                examples.append(example)
        if args.include_feedback:
            feedback_rows = learning_repo.recent_feedback(limit=max(1, args.limit), days=max(1, args.days))
            for row in feedback_rows:
                example = _feedback_to_example(row)
                if example:
                    examples.append(example)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as handle:
            for example in examples:
                handle.write(json.dumps(example, ensure_ascii=False) + "\n")
        print(f"Exported {len(examples)} examples to {args.output}")
        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    raise SystemExit(main())
