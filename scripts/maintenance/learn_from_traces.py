from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import sys

from psycopg_pool import ConnectionPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import Settings
from agent.learning.repository import LearningRepository, should_promote_candidate
from agent.memory.repository import MemoryRepository
from scripts.dev.eval_route_quality import CASES, _score_case


BASE_DIR = Path(__file__).resolve().parents[2]
_SCHEMA_CANDIDATES = [
    BASE_DIR / "infra" / "sql" / "memory_schema.sql",
    BASE_DIR / "sql" / "memory_schema.sql",
    BASE_DIR / "langchain_core" / "sql" / "memory_schema.sql",
]
MEMORY_SCHEMA_PATH = next((path for path in _SCHEMA_CANDIDATES if path.exists()), _SCHEMA_CANDIDATES[-1])


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    clean = _normalize_text(text).lower()
    return any(cue in clean for cue in cues)


def _shorten(value: str, limit: int = 220) -> str:
    text = _normalize_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


DOCUMENT_DEEP_CUES = (
    "phân tích sâu",
    "phan tich sau",
    "phân tích kỹ",
    "phan tich ky",
    "tóm tắt kỹ",
    "tom tat ky",
    "tóm tắt chi tiết",
    "tom tat chi tiet",
    "chi tiết hơn",
    "chi tiet hon",
    "nhiều trang",
    "nhieu trang",
    "nhiều page",
    "nhieu page",
    "đọc kỹ",
    "doc ky",
    "bóc tách",
    "boc tach",
)

DOCUMENT_FOLLOWUP_CUES = (
    "trong file",
    "trong tài liệu",
    "trong tai lieu",
    "file này",
    "file nay",
    "tài liệu này",
    "tai lieu nay",
    "ý gì",
    "y gi",
    "dùng thế nào",
    "dung the nao",
    "là gì",
    "la gi",
    "giải thích",
    "giai thich",
)

DOCUMENT_STYLE_DEEP_CUES = (
    "dài hơn",
    "dai hon",
    "kỹ hơn",
    "ky hon",
    "chi tiết hơn",
    "chi tiet hon",
    "nhiều trang",
    "nhieu trang",
    "nhiều page",
    "nhieu page",
)

DOCUMENT_STYLE_SHORT_CUES = (
    "ngắn hơn",
    "ngan hon",
    "gọn hơn",
    "gon hon",
    "ít chữ hơn",
    "it chu hon",
    "súc tích",
    "suc tich",
)

DOCUMENT_STYLE_READABLE_CUES = (
    "dễ nhìn hơn",
    "de nhin hon",
    "dễ đọc hơn",
    "de doc hon",
    "rõ hơn",
    "ro hon",
    "bullet",
    "gạch đầu dòng",
    "gach dau dong",
    "chia ý",
    "chia y",
    "format",
)

IMAGE_ROUTE_CUES = (
    "ảnh này",
    "anh nay",
    "xem cái này",
    "xem cai nay",
    "phân tích ảnh",
    "phan tich anh",
    "mô tả ảnh",
    "mo ta anh",
    "đọc chữ",
    "doc chu",
    "trích thông tin từ ảnh",
    "trich thong tin tu anh",
)

DOCUMENT_ROUTE_CUES = (
    "tóm tắt file",
    "tom tat file",
    "phân tích file",
    "phan tich file",
    "đọc file",
    "doc file",
    "file này",
    "file nay",
    "trích thông tin",
    "trich thong tin",
    "hỏi đáp",
    "hoi dap",
)


@dataclass
class Candidate:
    scope: str
    topic: str
    title: str
    prompt_hint: str
    memory_hint: str
    examples: list[dict[str, Any]] = field(default_factory=list)
    support_count: int = 0

    def add_example(self, event: dict[str, Any]) -> None:
        self.support_count += 1
        if len(self.examples) >= 3:
            return
        self.examples.append(
            {
                "chat_id": event.get("chat_id"),
                "request_id": event.get("request_id"),
                "user_text": _shorten(str(event.get("user_text") or "")),
                "final_text": _shorten(str(event.get("final_text") or "")),
                "issue_type": event.get("issue_type", ""),
            }
        )

    def to_payload(self) -> dict[str, Any]:
        confidence = min(0.95, 0.60 + max(0, self.support_count - 1) * 0.08)
        return {
            "scope": self.scope,
            "topic": self.topic,
            "title": self.title,
            "prompt_hint": self.prompt_hint,
            "memory_hint": self.memory_hint,
            "support_count": self.support_count,
            "confidence": confidence,
            "examples": self.examples,
        }


def _candidate_key(scope: str, topic: str, prompt_hint: str, memory_hint: str) -> str:
    return "::".join(
        [
            _normalize_text(scope).lower(),
            _normalize_text(topic).lower(),
            _normalize_text(prompt_hint).lower(),
            _normalize_text(memory_hint).lower(),
        ]
    )


def _add_candidate(store: dict[str, Candidate], *, scope: str, topic: str, title: str, prompt_hint: str, memory_hint: str, event: dict[str, Any]) -> None:
    key = _candidate_key(scope, topic, prompt_hint, memory_hint)
    candidate = store.get(key)
    if candidate is None:
        candidate = Candidate(
            scope=scope,
            topic=topic,
            title=title,
            prompt_hint=prompt_hint,
            memory_hint=memory_hint,
        )
        store[key] = candidate
    candidate.add_example(event)


def _build_candidates(events: list[dict[str, Any]]) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    for event in events:
        user_text = _normalize_text(str(event.get("user_text") or ""))
        final_text = _normalize_text(str(event.get("final_text") or ""))
        scope = _normalize_text(str(event.get("scope") or "general")) or "general"
        topic = _normalize_text(str(event.get("topic") or ""))
        source = _normalize_text(str(event.get("source") or ""))
        issue_type = _normalize_text(str(event.get("issue_type") or ""))
        attachment_kind = _normalize_text(str((event.get("metadata") or {}).get("attachment_kind") or ""))
        final_lower = final_text.lower()

        if issue_type == "document_followup" or _contains_any(user_text, DOCUMENT_FOLLOWUP_CUES):
            _add_candidate(
                candidates,
                scope="document",
                topic="followup",
                title="Document follow-up",
                prompt_hint="Khi user hỏi tiếp về tài liệu vừa xử lý, ưu tiên memory_search(document_context) và bám đúng file gần nhất trước khi suy đoán.",
                memory_hint="Remember recent document context before answering follow-up questions.",
                event=event,
            )

        if issue_type == "deep_document_request" or _contains_any(user_text, DOCUMENT_DEEP_CUES):
            _add_candidate(
                candidates,
                scope="document",
                topic="deep_summary",
                title="Document deep summary",
                prompt_hint="Khi tài liệu dài hoặc user nói phân tích sâu / chi tiết hơn / nhiều trang hơn, bật deep summary và bao quát nhiều phần quan trọng thay vì chỉ tóm tắt sơ lược.",
                memory_hint="Use deep summary mode for long documents or explicit deep-analysis requests.",
                event=event,
            )

        if _contains_any(user_text, DOCUMENT_STYLE_DEEP_CUES):
            _add_candidate(
                candidates,
                scope="document",
                topic="style_deep",
                title="Document style preference: deeper",
                prompt_hint="Khi người dùng muốn dài hơn, kỹ hơn, chi tiết hơn hoặc nhiều trang hơn, trả câu trả lời đầy đủ hơn theo bullet rõ ràng và bao quát hơn.",
                memory_hint="Prefer deeper, more complete bullets for this user.",
                event=event,
            )

        if _contains_any(user_text, DOCUMENT_STYLE_SHORT_CUES):
            _add_candidate(
                candidates,
                scope="general",
                topic="style_short",
                title="Response style preference: shorter",
                prompt_hint="Khi người dùng muốn ngắn hơn, gọn hơn hoặc ít chữ hơn, giữ câu trả lời ngắn, ít bullet, ưu tiên phần quan trọng nhất.",
                memory_hint="Keep responses shorter when the user asks for it.",
                event=event,
            )

        if _contains_any(user_text, DOCUMENT_STYLE_READABLE_CUES):
            _add_candidate(
                candidates,
                scope="document",
                topic="format_readable",
                title="Readable formatting preference",
                prompt_hint="Khi trả lời tài liệu, chia thành tiêu đề ngắn và bullet rõ ràng để dễ đọc trên Telegram; tránh viết thành một đoạn dài.",
                memory_hint="Use readable sectioned formatting for document outputs.",
                event=event,
            )

        if issue_type == "fallback" or "mia chưa" in final_lower or "không có tool" in final_lower or "chưa có tool" in final_lower:
            if scope == "image" or _contains_any(user_text, IMAGE_ROUTE_CUES):
                _add_candidate(
                    candidates,
                    scope="image",
                    topic="routing",
                    title="Image routing hint",
                    prompt_hint="Khi có ảnh đính kèm và user nói phân tích / mô tả / xem cái này / đọc chữ, ưu tiên image_describe hoặc image_ocr thay vì trả fallback chung.",
                    memory_hint="Route attached images to image_describe/image_ocr first.",
                    event=event,
                )
            if scope == "document" or _contains_any(user_text, DOCUMENT_ROUTE_CUES):
                _add_candidate(
                    candidates,
                    scope="document",
                    topic="routing",
                    title="Document routing hint",
                    prompt_hint="Khi có file đính kèm và user nói tóm tắt / phân tích / đọc file / hỏi đáp trong file, ưu tiên document_summarize, document_search_answer hoặc document_extract_fields.",
                    memory_hint="Route attached documents to document tools first.",
                    event=event,
                )

        if "vision_fallback" in issue_type or "vision_fallback_local" in final_lower:
            _add_candidate(
                candidates,
                scope="image",
                topic="vision_fallback",
                title="Image vision fallback",
                prompt_hint="Nếu vision model có sẵn thì dùng để mô tả ảnh; fallback local chỉ nên dùng khi vision lỗi hoặc không có sẵn.",
                memory_hint="Prefer vision for image description when available.",
                event=event,
            )

        if source == "media" and attachment_kind == "document" and _contains_any(user_text, DOCUMENT_DEEP_CUES):
            _add_candidate(
                candidates,
                scope="document",
                topic="deep_summary",
                title="Document deep summary",
                prompt_hint="Khi tài liệu dài và user muốn phân tích sâu, chia nội dung thành nhiều phần rồi tổng hợp lại để không bỏ sót các trang quan trọng.",
                memory_hint="Chunk long documents before summarizing.",
                event=event,
            )

    return candidates


def _build_candidates_from_feedback(feedback_rows: list[dict[str, Any]]) -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    for row in feedback_rows:
        verdict = _normalize_text(str(row.get("verdict") or "")).lower()
        comment = _normalize_text(str(row.get("comment") or ""))
        correction_text = _normalize_text(str(row.get("correction_text") or ""))
        current_text = _normalize_text(str(row.get("current_text") or ""))
        payload = {
            "chat_id": str(row.get("chat_id") or "feedback"),
            "request_id": str(row.get("request_id") or "feedback"),
            "user_text": comment or correction_text or current_text or verdict,
            "final_text": current_text,
            "issue_type": verdict or "feedback",
            "scope": str(row.get("scope") or "general"),
            "source": str(row.get("source") or "feedback"),
            "metadata": dict(row.get("metadata") or {}),
        }
        for key, candidate in _build_candidates([payload]).items():
            candidates[key] = candidate
    return candidates


def _baseline_candidates() -> dict[str, Candidate]:
    candidates: dict[str, Candidate] = {}
    seed_events = [
        {
            "chat_id": "bootstrap",
            "request_id": "bootstrap",
            "user_text": "phân tích file này",
            "final_text": "",
            "issue_type": "fallback",
            "scope": "document",
            "source": "chat",
        },
        {
            "chat_id": "bootstrap",
            "request_id": "bootstrap",
            "user_text": "phân tích ảnh này",
            "final_text": "",
            "issue_type": "fallback",
            "scope": "image",
            "source": "chat",
        },
        {
            "chat_id": "bootstrap",
            "request_id": "bootstrap",
            "user_text": "tóm tắt file này",
            "final_text": "",
            "issue_type": "deep_document_request",
            "scope": "document",
            "source": "media",
            "metadata": {"attachment_kind": "document"},
        },
        {
            "chat_id": "bootstrap",
            "request_id": "bootstrap",
            "user_text": "Mia trả lời hơi dài, cho ngắn hơn chút",
            "final_text": "",
            "issue_type": "preference_signal",
            "scope": "general",
            "source": "chat",
        },
        {
            "chat_id": "bootstrap",
            "request_id": "bootstrap",
            "user_text": "Mia đang có tool gì",
            "final_text": "",
            "issue_type": "ok",
            "scope": "general",
            "source": "chat",
        },
    ]
    for event in seed_events:
        for key, candidate in _build_candidates([event]).items():
            candidates[key] = candidate
    return candidates


def _run_eval_gate() -> dict[str, Any]:
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
    if passed_count != len(CASES):
        failed_rows = [row for row in rows if not row["passed"]]
        failing = ", ".join(f"{row['group']}:{row['text']}" for row in failed_rows[:5])
        raise RuntimeError(
            f"Eval gate failed: {passed_count}/{len(CASES)} passed. "
            f"Failed cases: {failing}"
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote learning insights from Mia traces.")
    parser.add_argument("--days", type=int, default=14, help="How many days of events to inspect.")
    parser.add_argument("--limit", type=int, default=400, help="Maximum events to fetch.")
    parser.add_argument("--apply", action="store_true", help="Write insights back to the DB.")
    parser.add_argument("--apply-memories", action="store_true", help="Also promote the insights into durable memory.")
    parser.add_argument("--seed-baseline", action="store_true", help="Also seed a small set of baseline insights.")
    parser.add_argument("--include-feedback", action="store_true", help="Also promote candidates derived from feedback rows.")
    parser.add_argument("--decay", action="store_true", help="Decay stale insights after promotion.")
    parser.add_argument("--min-support", type=int, default=2, help="Minimum repeated support required before promoting.")
    parser.add_argument("--top", type=int, default=12, help="Maximum number of insights to promote.")
    parser.add_argument("--skip-eval-gate", action="store_true", help="Skip the route eval gate before promoting insights.")
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

    pool = ConnectionPool(conninfo=settings.postgres_uri, open=True)
    learning_repo = LearningRepository(pool=pool)
    learning_repo.setup()

    memory_repo: MemoryRepository | None = None
    if args.apply_memories:
        memory_repo = MemoryRepository(
            pool=pool,
            embedder_url=settings.memory_embedder_url,
            timeout_seconds=settings.request_timeout_seconds,
            schema_path=MEMORY_SCHEMA_PATH,
        )
        memory_repo.setup()

    try:
        if (args.apply or args.apply_memories or args.seed_baseline) and not args.skip_eval_gate:
            gate_summary = _run_eval_gate()
            print(f"Eval gate passed: {gate_summary['passed']}/{gate_summary['total']} ({gate_summary['accuracy']:.1f}%).")

        events = learning_repo.recent_events(limit=max(1, args.limit), days=max(1, args.days))
        candidates = _build_candidates(events) if events else {}
        if args.include_feedback:
            feedback_rows = learning_repo.recent_feedback(limit=max(1, args.limit), days=max(1, args.days))
            feedback_candidates = _build_candidates_from_feedback(feedback_rows) if feedback_rows else {}
            for key, candidate in feedback_candidates.items():
                existing = candidates.get(key)
                if existing is None or candidate.support_count > existing.support_count:
                    candidates[key] = candidate
        if args.seed_baseline:
            for key, candidate in _baseline_candidates().items():
                existing = candidates.get(key)
                if existing is None:
                    candidates[key] = candidate
                else:
                    if candidate.support_count > existing.support_count:
                        existing.support_count = candidate.support_count
                    for example in candidate.examples:
                        if len(existing.examples) >= 3:
                            break
                        existing.examples.append(example)
        if not candidates:
            if not events:
                print("No learning events found and no baseline candidates generated.")
            else:
                print("No new learning candidates found.")
            return 0

        ranked = sorted(candidates.values(), key=lambda item: (item.support_count, item.scope, item.topic), reverse=True)
        promoted = 0
        for candidate in ranked[: max(1, args.top)]:
            payload = candidate.to_payload()
            allow_single_support = args.seed_baseline or (
                args.include_feedback
                and payload["support_count"] <= 1
                and payload["topic"] in {"style_short", "style_deep", "format_readable", "followup", "routing"}
            )
            can_promote, gate_reason = should_promote_candidate(
                support_count=payload["support_count"],
                confidence=payload["confidence"],
                has_feedback=args.include_feedback,
                allow_single_support=allow_single_support,
            )
            if not can_promote and not args.seed_baseline:
                print(
                    f"[SKIP] {payload['scope']}/{payload['topic']} {payload['title']} "
                    f"(support={payload['support_count']}, confidence={payload['confidence']:.2f}) - {gate_reason}"
                )
                continue
            if args.apply:
                learning_repo.upsert_insight(**payload)
                if memory_repo is not None:
                    memory_repo.write(
                        chat_id="learning-loop",
                        content=payload["prompt_hint"],
                        memory_type="learning_rule",
                        title=payload["title"],
                        tags=["learning", payload["scope"], payload["topic"]],
                        importance=min(5, 3 + min(candidate.support_count // 2, 2)),
                        source_text=payload["memory_hint"] or payload["prompt_hint"],
                    )
            print(
                f"[{payload['scope']}/{payload['topic']}] {payload['title']} "
                f"(support={payload['support_count']}, confidence={payload['confidence']:.2f})\n"
                f"- {payload['prompt_hint']}\n"
            )
            promoted += 1

        if args.decay:
            decayed = learning_repo.decay_stale_insights(max_age_days=max(7, args.days * 2), min_support=max(1, args.min_support - 1))
            print(f"Decayed {decayed} stale insights.")

        print(f"Processed {len(events)} events, proposed {promoted} insights.")
        return 0
    finally:
        pool.close()


if __name__ == "__main__":
    raise SystemExit(main())
