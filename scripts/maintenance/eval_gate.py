from __future__ import annotations

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

from scripts.dev.eval_route_quality import CASES, _score_case


def main() -> int:
    passed_count = 0
    group_stats: dict[str, dict[str, int]] = {}
    rows: list[dict[str, Any]] = []
    for case in CASES:
        passed, actual = _score_case(case)
        if passed:
            passed_count += 1
        bucket = group_stats.setdefault(case.group, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if passed:
            bucket["passed"] += 1
        rows.append(
            {
                "text": case.text,
                "group": case.group,
                "expected": {
                    "route_type": case.expected_route_type,
                    "domain": case.expected_domain,
                    "hint_tool": case.expected_hint_tool,
                },
                "actual": actual,
                "passed": passed,
                "note": case.note,
            }
        )

    summary = {
        "total": len(CASES),
        "passed": passed_count,
        "failed": len(CASES) - passed_count,
        "accuracy": round((passed_count / len(CASES)) * 100, 1) if CASES else 0.0,
        "by_group": {
            group: {
                "total": bucket["total"],
                "passed": bucket["passed"],
                "failed": bucket["total"] - bucket["passed"],
                "accuracy": round((bucket["passed"] / bucket["total"]) * 100, 1) if bucket["total"] else 0.0,
            }
            for group, bucket in group_stats.items()
        },
    }
    payload = {"summary": summary, "results": rows}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed_count == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
