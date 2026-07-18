from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


BAD_RESPONSE_CUES = (
    "connection error",
    "error connecting",
    "dịch vụ bên ngoài đang gặp sự cố",
    "chưa phản hồi ổn định",
    "xin lỗi, mia chưa tạo được phản hồi rõ ràng",
)


@dataclass(frozen=True)
class SmokeCase:
    name: str
    text: str
    expect_any_tools: tuple[str, ...] = ()
    forbidden_tool_prefixes: tuple[str, ...] = ()
    expect_text_any: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    needs_cancel_after: bool = False


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _post_chat(
    *,
    base_url: str,
    token: str,
    chat_id: str,
    user_id: str,
    thread_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
    timeout: float = 90,
) -> tuple[dict[str, Any], float]:
    payload = json.dumps(
        {
            "chat_id": chat_id,
            "user_id": user_id,
            "thread_id": thread_id,
            "text": text,
            "metadata": metadata or {},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/mia/chat",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Mia-Core-Token": token,
            "X-Mia-User-Id": user_id,
        },
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return json.loads(body), latency_ms


def _health(base_url: str, timeout: float = 10) -> dict[str, Any]:
    request = urllib.request.Request(base_url.rstrip("/") + "/health", method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _case_passed(case: SmokeCase, response: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    final_text = str(response.get("final_text") or "").strip()
    tools_called = [str(tool) for tool in response.get("tools_called") or [] if str(tool).strip()]
    lower_text = final_text.lower()

    if not final_text:
        reasons.append("empty final_text")
    if any(cue in lower_text for cue in BAD_RESPONSE_CUES):
        reasons.append("response contains operational error cue")
    if case.expect_any_tools and not any(tool in tools_called for tool in case.expect_any_tools):
        reasons.append(f"missing expected tool among {list(case.expect_any_tools)}")
    for prefix in case.forbidden_tool_prefixes:
        blocked = [tool for tool in tools_called if tool.startswith(prefix)]
        if blocked:
            reasons.append(f"forbidden tool prefix {prefix!r}: {blocked}")
    if case.expect_text_any and not any(text.lower() in lower_text for text in case.expect_text_any):
        reasons.append(f"missing expected text among {list(case.expect_text_any)}")

    return not reasons, reasons


def _cleanup_smoke_owner(owner_id: str) -> None:
    sql = (
        f"DELETE FROM mia_memory_proposals WHERE owner_id = '{owner_id}'; "
        f"DELETE FROM mia_memory_items WHERE owner_id = '{owner_id}'; "
        f"DELETE FROM mia_pending_actions WHERE user_id = '{owner_id}' OR chat_id = '{owner_id}';"
    )
    subprocess.run(
        ["docker", "exec", "postgres", "psql", "-U", "n8n", "-d", "vectordb", "-c", sql],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _default_cases(run_id: str) -> list[SmokeCase]:
    code_name = f"Sao Băng Xanh {run_id[-6:]}"
    return [
        SmokeCase(
            name="basic_chat",
            text="Mia trả lời ngắn: hệ thống còn chạy ổn không?",
        ),
        SmokeCase(
            name="memory_write",
            text=f"hãy nhớ là trong live smoke này, mật danh dự án là {code_name}",
            expect_any_tools=("memory_write",),
        ),
        SmokeCase(
            name="memory_recall",
            text="mật danh dự án trong live smoke này là gì?",
            expect_text_any=(code_name,),
            forbidden_tool_prefixes=("code_",),
        ),
        SmokeCase(
            name="calendar_today",
            text="xem lịch hôm nay",
            expect_any_tools=("calendar_list_today",),
        ),
        SmokeCase(
            name="calendar_tomorrow",
            text="xem lịch ngày mai",
            expect_any_tools=("calendar_list_tomorrow",),
        ),
        SmokeCase(
            name="smarthome_bedroom_status",
            text="xem trạng thái phòng ngủ",
            expect_any_tools=("smarthome_room_status",),
        ),
        SmokeCase(
            name="code_project_status",
            text="kiểm tra workspace code hiện có",
            expect_any_tools=("code_project_status",),
        ),
        SmokeCase(
            name="github_write_approval",
            text=(
                "tạo issue test smoke trong repo hdhminh/mia-agent, "
                f"tiêu đề Smoke approval {run_id[-6:]}, nội dung chỉ là test approval không thực thi nếu chưa xác nhận"
            ),
            expect_text_any=("xác nhận", "confirm", "cần xác nhận", "requires confirmation"),
            needs_cancel_after=True,
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real Mia /mia/chat smoke tests against a running mia-core service.")
    parser.add_argument("--base-url", default=os.getenv("MIA_LIVE_SMOKE_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--only", default="", help="Comma-separated case names to run.")
    parser.add_argument("--skip", default="", help="Comma-separated case names to skip.")
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--no-cleanup", action="store_true", help="Do not try to remove smoke DB rows after the run.")
    parser.add_argument("--json", action="store_true", help="Print only JSON output.")
    args = parser.parse_args()

    env = _load_env(args.env_file)
    token = os.getenv("MIA_CORE_API_TOKEN") or env.get("MIA_CORE_API_TOKEN", "")
    if not token:
        print("MIA_CORE_API_TOKEN is missing.", file=sys.stderr)
        return 2

    run_id = f"{int(time.time())}"
    owner_id = f"smoke-live-{run_id}"
    chat_id = owner_id
    thread_id = f"{owner_id}-thread"
    only = {item.strip() for item in args.only.split(",") if item.strip()}
    skip = {item.strip() for item in args.skip.split(",") if item.strip()}
    cases = [
        case
        for case in _default_cases(run_id)
        if (not only or case.name in only) and case.name not in skip
    ]

    report: dict[str, Any] = {
        "ok": False,
        "base_url": args.base_url,
        "chat_id": chat_id,
        "user_id": owner_id,
        "health": {},
        "cases": [],
        "summary": {},
    }

    try:
        report["health"] = _health(args.base_url)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        report["summary"] = {"passed": 0, "failed": len(cases), "error": f"health failed: {exc}"}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    passed_count = 0
    for case in cases:
        case_result: dict[str, Any] = {
            "name": case.name,
            "text": case.text,
            "passed": False,
            "reasons": [],
            "tools_called": [],
            "final_text": "",
            "client_latency_ms": 0,
            "trace": {},
        }
        try:
            response, latency_ms = _post_chat(
                base_url=args.base_url,
                token=token,
                chat_id=chat_id,
                user_id=owner_id,
                thread_id=thread_id,
                text=case.text,
                metadata=case.metadata,
                timeout=args.timeout,
            )
            passed, reasons = _case_passed(case, response)
            case_result.update(
                {
                    "passed": passed,
                    "reasons": reasons,
                    "tools_called": response.get("tools_called") or [],
                    "final_text": response.get("final_text") or "",
                    "client_latency_ms": latency_ms,
                    "trace": response.get("trace") or {},
                }
            )
            if passed:
                passed_count += 1
            if case.needs_cancel_after:
                _post_chat(
                    base_url=args.base_url,
                    token=token,
                    chat_id=chat_id,
                    user_id=owner_id,
                    thread_id=thread_id,
                    text="hủy",
                    timeout=args.timeout,
                )
        except Exception as exc:  # noqa: BLE001 - smoke script should record operational failures.
            case_result["reasons"] = [f"{type(exc).__name__}: {exc}"]
        report["cases"].append(case_result)

    failed_count = len(cases) - passed_count
    report["ok"] = failed_count == 0
    report["summary"] = {
        "total": len(cases),
        "passed": passed_count,
        "failed": failed_count,
        "accuracy": round((passed_count / len(cases)) * 100, 1) if cases else 100.0,
    }

    if not args.no_cleanup:
        _cleanup_smoke_owner(owner_id)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Live smoke: {passed_count}/{len(cases)} passed")
        for case_result in report["cases"]:
            status = "PASS" if case_result["passed"] else "FAIL"
            print(f"- {status} {case_result['name']}: tools={case_result['tools_called']} latency={case_result['client_latency_ms']}ms")
            if case_result["reasons"]:
                print(f"  reasons: {case_result['reasons']}")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
