from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LANGCHAIN_ROOT = ROOT / "langchain_core"
for path in (ROOT, LANGCHAIN_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from mia_core.config import Settings
from mia_core.learning import LearningRepository
from scripts.dev.eval_route_quality import CASES, _score_case


def _percent(value: float) -> float:
    return round(value * 100.0, 1)


def _load_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Mia learning-loop quality.")
    parser.add_argument("--days", type=int, default=30, help="How many days of events to inspect.")
    parser.add_argument("--save", type=Path, default=None, help="Save snapshot to JSON.")
    parser.add_argument("--compare", type=Path, default=None, help="Compare the current snapshot with a baseline JSON.")
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

    from psycopg_pool import ConnectionPool

    pool = ConnectionPool(conninfo=settings.postgres_uri, open=True)
    learning_repo = LearningRepository(pool=pool)
    learning_repo.setup()

    try:
        events = learning_repo.recent_events(limit=1000, days=max(1, args.days))
        feedback = learning_repo.recent_feedback(limit=1000, days=max(1, args.days))
        insights = learning_repo.list_active_insights(limit=1000)
        tool_gateway = learning_repo.runtime_summary(days=max(1, args.days), source="n8n_tool")

        route_passed = 0
        route_groups: dict[str, dict[str, int]] = {}
        for case in CASES:
            passed, _ = _score_case(case)
            if passed:
                route_passed += 1
            bucket = route_groups.setdefault(case.group, {"total": 0, "passed": 0})
            bucket["total"] += 1
            if passed:
                bucket["passed"] += 1

        total_events = len(events)
        fallback_events = sum(1 for row in events if str(row.get("issue_type") or "") == "fallback")
        document_followups = sum(1 for row in events if str(row.get("issue_type") or "") == "document_followup")
        cache_hits = sum(1 for row in events if bool(row.get("cache_hit")) or int(row.get("cached_tokens") or 0) > 0)
        direct_routes = sum(1 for row in events if str(row.get("source") or "") == "direct")
        media_events = sum(1 for row in events if str(row.get("source") or "") == "media")
        active_insight_groups: dict[str, int] = {}
        for row in insights:
            scope = str(row.get("scope") or "general")
            active_insight_groups[scope] = active_insight_groups.get(scope, 0) + 1

        snapshot: dict[str, Any] = {
            "route_eval": {
                "total": len(CASES),
                "passed": route_passed,
                "accuracy": _percent(route_passed / len(CASES)) if CASES else 0.0,
                "by_group": {
                    group: {
                        "total": bucket["total"],
                        "passed": bucket["passed"],
                        "accuracy": _percent(bucket["passed"] / bucket["total"]) if bucket["total"] else 0.0,
                    }
                    for group, bucket in route_groups.items()
                },
            },
            "learning": {
                "events": total_events,
                "feedback": len(feedback),
                "insights": len(insights),
                "cache_hit_rate": _percent(cache_hits / total_events) if total_events else 0.0,
                "fallback_rate": _percent(fallback_events / total_events) if total_events else 0.0,
                "document_followup_rate": _percent(document_followups / total_events) if total_events else 0.0,
                "direct_rate": _percent(direct_routes / total_events) if total_events else 0.0,
                "media_rate": _percent(media_events / total_events) if total_events else 0.0,
                "active_insights_by_scope": active_insight_groups,
            },
            "tool_gateway": tool_gateway,
        }

        if args.compare:
            baseline = _load_snapshot(args.compare)
            if baseline:
                snapshot["compare"] = {
                    "route_accuracy_delta": round(snapshot["route_eval"]["accuracy"] - float(baseline.get("route_eval", {}).get("accuracy", 0.0)), 1),
                    "cache_hit_rate_delta": round(snapshot["learning"]["cache_hit_rate"] - float(baseline.get("learning", {}).get("cache_hit_rate", 0.0)), 1),
                    "fallback_rate_delta": round(snapshot["learning"]["fallback_rate"] - float(baseline.get("learning", {}).get("fallback_rate", 0.0)), 1),
                    "insight_delta": int(snapshot["learning"]["insights"]) - int(baseline.get("learning", {}).get("insights", 0)),
                    "feedback_delta": int(snapshot["learning"]["feedback"]) - int(baseline.get("learning", {}).get("feedback", 0)),
                }

        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        if args.save:
            args.save.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    raise SystemExit(main())
