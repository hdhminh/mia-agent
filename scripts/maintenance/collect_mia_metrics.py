from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "docker-compose.yml"


def _run_container_snapshot(days: int, source: str) -> dict:
    python_code = dedent(
        f"""
        from __future__ import annotations

        import json
        import os
        import statistics
        import sys
        from pathlib import Path

        ROOT = Path("/app")
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        from psycopg_pool import ConnectionPool
        from agent.learning.repository import LearningRepository

        postgres_uri = os.environ.get("MIA_POSTGRES_URI", "").strip()
        if not postgres_uri:
            raise RuntimeError("MIA_POSTGRES_URI is missing inside the mia-core container.")

        pool = ConnectionPool(conninfo=postgres_uri, open=True)
        repo = LearningRepository(pool=pool)
        repo.setup()
        try:
            all_events = repo.recent_events(days={days}, limit=5000)
            feedback = repo.recent_feedback(days={days}, source="" if {source!r} == "all" else {source!r}, limit=5000)
            insights = repo.list_active_insights(limit=1000)
            runtime = repo.runtime_summary(days={days}, source={source!r}) if {source!r} != "all" else repo.runtime_summary(days={days}, source="n8n_tool")

            if {source!r} == "all":
                events = all_events
            else:
                events = [row for row in all_events if str(row.get("source") or "") == {source!r}]

            total_tokens = sum(int(row.get("total_tokens") or 0) for row in events)
            prompt_tokens = sum(int(row.get("prompt_tokens") or 0) for row in events)
            completion_tokens = sum(int(row.get("completion_tokens") or 0) for row in events)
            cached_tokens = sum(int(row.get("cached_tokens") or 0) for row in events)
            cache_hits = sum(1 for row in events if bool(row.get("cache_hit")) or int(row.get("cached_tokens") or 0) > 0)
            latency_values = []
            for row in events:
                metadata = row.get("metadata") or {{}}
                if not isinstance(metadata, dict):
                    metadata = {{}}
                latency_ms = metadata.get("latency_ms")
                try:
                    latency = float(latency_ms)
                except (TypeError, ValueError):
                    latency = 0.0
                if latency > 0:
                    latency_values.append(latency)

            source_summary = {{}}
            for row in all_events:
                src = str(row.get("source") or "unknown") or "unknown"
                bucket = source_summary.setdefault(
                    src,
                    {{
                        "count": 0,
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "cached_tokens": 0,
                        "cache_hits": 0,
                        "latencies": [],
                    }},
                )
                bucket["count"] += 1
                bucket["total_tokens"] += int(row.get("total_tokens") or 0)
                bucket["prompt_tokens"] += int(row.get("prompt_tokens") or 0)
                bucket["completion_tokens"] += int(row.get("completion_tokens") or 0)
                bucket["cached_tokens"] += int(row.get("cached_tokens") or 0)
                if bool(row.get("cache_hit")) or int(row.get("cached_tokens") or 0) > 0:
                    bucket["cache_hits"] += 1
                metadata = row.get("metadata") or {{}}
                if not isinstance(metadata, dict):
                    metadata = {{}}
                latency_ms = metadata.get("latency_ms")
                try:
                    latency = float(latency_ms)
                except (TypeError, ValueError):
                    latency = 0.0
                if latency > 0:
                    bucket["latencies"].append(latency)

            source_breakdown = {{
                key: {{
                    "count": bucket["count"],
                    "total_tokens": bucket["total_tokens"],
                    "prompt_tokens": bucket["prompt_tokens"],
                    "completion_tokens": bucket["completion_tokens"],
                    "cached_tokens": bucket["cached_tokens"],
                    "cache_hit_rate": round((bucket["cache_hits"] / bucket["count"]) * 100, 1) if bucket["count"] else 0.0,
                    "avg_latency_ms": round(sum(bucket["latencies"]) / len(bucket["latencies"]), 1) if bucket["latencies"] else 0.0,
                }}
                for key, bucket in sorted(source_summary.items(), key=lambda item: item[1]["count"], reverse=True)
            }}

            summary = {{
                "days": {days},
                "source": {source!r},
                "events": len(events),
                "feedback": len(feedback),
                "insights": len(insights),
                "total_tokens": total_tokens,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cached_tokens": cached_tokens,
                "cache_hit_rate": round((cache_hits / len(events)) * 100, 1) if events else 0.0,
                "avg_latency_ms": round(sum(latency_values) / len(latency_values), 1) if latency_values else 0.0,
                "median_latency_ms": round(statistics.median(latency_values), 1) if latency_values else 0.0,
                "source_breakdown": source_breakdown,
                "runtime_summary": runtime,
            }}
            print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        finally:
            pool.close()
        """
    ).strip()

    cmd = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "exec",
        "-T",
        "mia-core",
        "python",
        "-",
    ]
    proc = subprocess.run(
        cmd,
        input=python_code,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "mia-core snapshot failed:\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse mia-core output as JSON:\n{proc.stdout}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect real MIA metrics from the mia-core container.")
    parser.add_argument("--days", type=int, default=7, help="How many days of tool events to inspect.")
    parser.add_argument("--source", type=str, default="all", help="Event source to summarize, or 'all'.")
    parser.add_argument("--save", type=Path, default=None, help="Optional JSON output path.")
    args = parser.parse_args()

    snapshot = _run_container_snapshot(days=max(1, args.days), source=args.source)
    print(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))

    if args.save:
        args.save.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
