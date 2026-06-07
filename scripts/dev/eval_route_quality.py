from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LANGCHAIN_ROOT = ROOT / "langchain_core"
for path in (ROOT, LANGCHAIN_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from mia_core.router import route_request


@dataclass(frozen=True)
class RouteCase:
    text: str
    expected_route_type: str
    expected_domain: str
    expected_hint_tool: str
    group: str
    note: str = ""
    metadata: dict[str, Any] | None = None


CASES: list[RouteCase] = [
    RouteCase("Mia đang có các tool nào nhỉ?", "agentic_domain", "general", "__capabilities_overview__", "general", "general capability overview"),
    RouteCase("anh có tool hỗ trợ calendar không?", "direct_deterministic", "calendar", "calendar_help", "google_workspace", "calendar help is intentionally direct"),
    RouteCase("cho mình xem lịch hôm nay", "direct_deterministic", "calendar", "calendar_list_today", "google_workspace", "calendar list today"),
    RouteCase("hủy lịch phòng vấn ngày mai", "agentic_domain", "calendar", "calendar_delete_event", "google_workspace", "calendar delete should not be forced direct"),
    RouteCase("kiểm tra lịch rảnh 9h-10h mai", "agentic_domain", "calendar", "calendar_check_availability", "google_workspace", "calendar availability"),
    RouteCase("tìm sự kiện họp với team tuần sau", "agentic_domain", "calendar", "calendar_find_event", "google_workspace", "calendar find event"),
    RouteCase("mở inbox giúp mình", "direct_deterministic", "gmail", "gmail_list_inbox", "google_workspace", "gmail inbox"),
    RouteCase("đọc mail từ Nintendo", "agentic_domain", "gmail", "gmail_search_by_sender", "google_workspace", "gmail read by sender"),
    RouteCase("tìm mail hóa đơn tháng 5", "agentic_domain", "gmail", "gmail_search_email", "google_workspace", "gmail search"),
    RouteCase("soạn mail gửi cho Nam về lịch họp", "agentic_domain", "gmail", "gmail_draft_email", "google_workspace", "gmail draft"),
    RouteCase("trả lời mail cho khách hàng", "agentic_domain", "gmail", "gmail_reply_email", "google_workspace", "gmail reply"),
    RouteCase("xem file drive gần đây", "agentic_domain", "workspace", "drive_list_files", "google_workspace", "drive list"),
    RouteCase("tìm file báo cáo tháng 5", "agentic_domain", "workspace", "drive_search_file", "google_workspace", "drive search"),
    RouteCase("xem thông tin file hợp đồng", "agentic_domain", "workspace", "drive_get_file_info", "google_workspace", "drive file info"),
    RouteCase("tạo folder dự án mới", "agentic_domain", "workspace", "drive_create_folder", "google_workspace", "drive create folder"),
    RouteCase("đọc doc onboarding", "agentic_domain", "workspace", "docs_read_doc", "google_workspace", "docs read"),
    RouteCase("tìm doc proposal quý 2", "agentic_domain", "workspace", "docs_search_doc", "google_workspace", "docs search"),
    RouteCase("tạo doc kế hoạch sprint", "agentic_domain", "workspace", "docs_create_doc", "google_workspace", "docs create"),
    RouteCase("thêm dòng vào sheet doanh thu", "agentic_domain", "workspace", "sheets_append_row", "google_workspace", "sheets append row"),
    RouteCase("cập nhật ô B2 thành 100", "agentic_domain", "workspace", "sheets_update_cell", "google_workspace", "sheets update cell"),
    RouteCase("xóa sheet tạm", "agentic_domain", "workspace", "sheets_delete_sheet", "google_workspace", "sheets delete"),
    RouteCase("đang có các tool gì", "agentic_domain", "general", "__capabilities_overview__", "general", "overview phrasing variant"),
    RouteCase("tin tức về Nintendo", "direct_deterministic", "general", "news_get", "general", "news topic"),
    RouteCase("tin tức về Elon Musk", "direct_deterministic", "general", "search_web", "general", "news topic fallback to web search"),
    RouteCase("giá vàng hôm nay", "direct_deterministic", "general", "gold_get_price", "general", "gold"),
    RouteCase("thời tiết Hà Nội", "direct_deterministic", "general", "weather_get", "general", "weather"),
    RouteCase("rút gọn link https://example.com", "direct_deterministic", "general", "shortlink_create", "general", "shortlink"),
    RouteCase("github help", "direct_deterministic", "github", "github_help", "github", "github help"),
    RouteCase("xem repo octocat/Hello-World", "direct_deterministic", "github", "github_get_repo", "github", "github repo metadata"),
    RouteCase("xem repo của mình trên GitHub", "direct_deterministic", "github", "github_list_user_repos", "github", "list repos in my account"),
    RouteCase("liệt kê repo trong account của tôi", "direct_deterministic", "github", "github_list_user_repos", "github", "list repos in account variant"),
    RouteCase("tìm repo theo topic paddleocr", "direct_deterministic", "github", "github_search_repos", "github", "search repos by topic"),
    RouteCase("hãy tìm kiếm các repo về video translation nhiều sao nhất trên github", "direct_deterministic", "github", "github_search_repos", "github", "search repos phrasing variant"),
    RouteCase("tìm repo theo topic ai bằng python sort most stars", "direct_deterministic", "github", "github_search_repos", "github", "search repos by topic and filters"),
    RouteCase("xem branch octocat/Hello-World", "direct_deterministic", "github", "github_list_branches", "github", "github branch listing"),
    RouteCase("xem commit octocat/Hello-World", "direct_deterministic", "github", "github_list_commits", "github", "github commit listing"),
    RouteCase("xem chi tiết commit 7fd1a60b01f91b314f59955a4e4d4e80d8edf11d trong octocat/Hello-World", "direct_deterministic", "github", "github_get_commit", "github", "github commit detail"),
    RouteCase("doc file README trong repo octocat/Hello-World", "agentic_domain", "github", "github_get_file", "github", "github file read"),
    RouteCase(
        "tóm tắt README repo này",
        "agentic_domain",
        "github",
        "github_get_file",
        "github",
        "github follow-up readme summary",
        {"repo": "Huanshere/VideoLingo", "owner": "Huanshere", "repoName": "VideoLingo", "repoUrl": "https://github.com/Huanshere/VideoLingo"},
    ),
    RouteCase(
        "repo này đã dùng kĩ thuật gì",
        "direct_deterministic",
        "github",
        "github_get_repo",
        "github",
        "github technical follow-up",
        {"repo": "Huanshere/VideoLingo", "owner": "Huanshere", "repoName": "VideoLingo", "repoUrl": "https://github.com/Huanshere/VideoLingo"},
    ),
    RouteCase(
        "xem cấu trúc repo",
        "direct_deterministic",
        "github",
        "github_get_repo_tree",
        "github",
        "github structure follow-up",
        {"repo": "Huanshere/VideoLingo", "owner": "Huanshere", "repoName": "VideoLingo", "repoUrl": "https://github.com/Huanshere/VideoLingo"},
    ),
    RouteCase("tìm code Session trong repo psf/requests", "direct_deterministic", "github", "github_search_code", "github", "github code search"),
    RouteCase("xem diff octocat/Hello-World master...octocat-patch-1", "direct_deterministic", "github", "github_get_diff", "github", "github diff"),
    RouteCase("https://example.com/article-1", "direct_deterministic", "general", "read_url", "general", "plain URL should read directly"),
    RouteCase("tóm tắt link này https://example.com/article-2", "direct_deterministic", "general", "summarize_url", "general", "explicit URL summary"),
    RouteCase("https://example.com/article-3 link này nói gì về học phí?", "agentic_domain", "general", "ask_url", "general", "explicit URL question"),
    RouteCase("trong link này có nhắc gì về học phí không?", "agentic_domain", "general", "ask_url", "general", "url follow-up question without explicit URL"),
    RouteCase("Mia còn nhớ gì gần đây?", "direct_deterministic", "general", "memory_recent", "general", "memory recent"),
    RouteCase("hãy tìm kiếm giúp mình thông tin về OpenAI", "direct_deterministic", "general", "search_web", "general", "web search"),
    RouteCase("xem lịch mai rồi gửi mail nhắc", "agentic_multistep", "gmail", "gmail_send_email", "multi_intent", "calendar plus gmail follow-up"),
    RouteCase("xem lịch hôm nay và soạn mail nhắc họp", "agentic_domain", "google_full", "", "multi_intent", "calendar plus gmail mixed-intent"),
    RouteCase("soạn mail cho Nam về lịch họp mai", "agentic_domain", "gmail", "gmail_draft_email", "multi_intent", "mail intent with calendar context"),
    RouteCase("xem inbox và nếu có mail quan trọng thì tóm tắt ngắn", "direct_deterministic", "gmail", "gmail_list_inbox", "multi_intent", "inbox with soft follow-up"),
    RouteCase("tìm doc proposal và xem file drive gần đây", "agentic_domain", "google_full", "", "multi_intent", "docs plus drive mixed-intent"),
    RouteCase("đọc doc onboarding và cập nhật sheet doanh thu", "agentic_multistep", "google_full", "", "multi_intent", "docs plus sheets multi-step"),
    RouteCase("xem mail, lịch và file hôm nay", "agentic_domain", "google_full", "", "multi_intent", "three-way google overview"),
    RouteCase("tìm file hợp đồng, mở doc onboarding và thêm dòng sheet doanh thu", "agentic_domain", "google_full", "", "multi_intent", "three-way google mixed request"),
    RouteCase("mở inbox rồi xem lịch hôm nay", "direct_deterministic", "gmail", "gmail_list_inbox", "multi_intent", "gmail inbox wins with follow-up"),
    RouteCase("đọc mail từ Nintendo rồi xem file drive gần đây", "agentic_multistep", "gmail", "gmail_search_by_sender", "multi_intent", "gmail plus drive multi-step"),
    RouteCase("tìm file báo cáo và đọc doc proposal", "agentic_domain", "google_full", "", "multi_intent", "drive plus docs mixed-intent"),
    RouteCase("tìm mail hóa đơn rồi cập nhật sheet doanh thu", "agentic_multistep", "gmail", "gmail_search_email", "multi_intent", "gmail plus sheets multi-step"),
    RouteCase("xem file drive gần đây rồi xóa sheet tạm", "agentic_multistep", "workspace", "drive_delete_file", "multi_intent", "drive plus sheets multi-step"),
    RouteCase("anh có thể xem giúp mình email và calendar hôm nay không", "agentic_domain", "google_full", "", "multi_intent", "explicit google mixed request"),
    RouteCase("xem lịch hôm nay rồi hủy lịch mai", "agentic_multistep", "calendar", "calendar_delete_event", "multi_intent", "calendar multi-step"),
    RouteCase("đọc mail từ Nintendo rồi xem lịch mai", "agentic_multistep", "gmail", "gmail_search_by_sender", "multi_intent", "gmail plus calendar multi-step"),
    RouteCase("tìm file hợp đồng rồi tạo folder mới", "agentic_multistep", "workspace", "drive_create_folder", "multi_intent", "workspace multi-step"),
    RouteCase("mở inbox rồi trả lời mail", "agentic_multistep", "gmail", "gmail_reply_email", "multi_intent", "gmail reply after inbox"),
    RouteCase("tìm mail hóa đơn tháng 5 rồi mở inbox", "agentic_multistep", "gmail", "gmail_search_email", "multi_intent", "gmail search then inbox"),
    RouteCase("xem file drive gần đây và đọc doc onboarding", "agentic_domain", "google_full", "", "multi_intent", "drive plus docs with connector"),
    RouteCase("xem file drive gần đây rồi thêm dòng vào sheet doanh thu", "agentic_multistep", "workspace", "drive_create_file", "multi_intent", "workspace multi-step"),
    RouteCase("Mia có thể xem mail, lịch và file giúp mình không?", "agentic_domain", "google_full", "", "multi_intent", "three-way help request"),
    RouteCase("tìm kiếm giúp mình mail hóa đơn hoặc file hợp đồng", "agentic_domain", "google_full", "", "multi_intent", "mail or file search"),
    RouteCase("tìm file báo cáo, đọc doc proposal, và gửi mail tóm tắt", "agentic_multistep", "google_full", "", "multi_intent", "three-step mixed workflow"),
    RouteCase("xem lịch hôm nay và hủy lịch mai", "agentic_domain", "calendar", "calendar_delete_event", "multi_intent", "same-domain multi-intent"),
    RouteCase("đọc ảnh này", "direct_deterministic", "media", "image_ocr", "media", "photo ocr", {"hasAttachment": True, "attachmentKind": "photo", "fileId": "photo-1"}),
    RouteCase("mô tả ảnh này", "direct_deterministic", "media", "image_describe", "media", "photo describe", {"hasAttachment": True, "attachmentKind": "photo", "fileId": "photo-2"}),
    RouteCase("xem cái này", "direct_deterministic", "media", "image_describe", "media", "photo ambiguous describe", {"hasAttachment": True, "attachmentKind": "photo", "fileId": "photo-3"}),
    RouteCase("trích thông tin từ ảnh này", "direct_deterministic", "media", "image_extract_fields", "media", "photo extract fields", {"hasAttachment": True, "attachmentKind": "photo", "fileId": "photo-4"}),
    RouteCase("tóm tắt file này", "direct_deterministic", "media", "document_summarize", "media", "document summarize", {"hasAttachment": True, "attachmentKind": "document", "fileId": "doc-1"}),
    RouteCase("chép lời audio này", "direct_deterministic", "media", "audio_transcribe", "media", "audio transcribe", {"hasAttachment": True, "attachmentKind": "audio", "fileId": "audio-1"}),
    RouteCase("đọc thành giọng nói câu này", "direct_deterministic", "media", "tts_speak", "media", "tts speak", {}),
]


def _score_case(case: RouteCase) -> tuple[bool, dict[str, Any]]:
    decision = route_request(case.text, case.metadata)
    actual = {
        "route_type": decision.route_type,
        "domain": decision.domain,
        "hint_tool": decision.hint_tool,
        "agent_key": decision.agent_key,
        "reason": decision.reason,
    }
    passed = (
        decision.route_type == case.expected_route_type
        and decision.domain == case.expected_domain
        and decision.hint_tool == case.expected_hint_tool
    )
    return passed, actual


def main() -> int:
    rows: list[dict[str, Any]] = []
    passed_count = 0
    group_stats: dict[str, dict[str, int]] = {}
    for case in CASES:
        passed, actual = _score_case(case)
        if passed:
            passed_count += 1
        group_bucket = group_stats.setdefault(case.group, {"total": 0, "passed": 0})
        group_bucket["total"] += 1
        if passed:
            group_bucket["passed"] += 1
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
        "accuracy": round((passed_count / len(CASES)) * 100, 1) if CASES else 0.0,
        "failed": len(CASES) - passed_count,
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

    print(json.dumps({"summary": summary, "results": rows}, ensure_ascii=False, indent=2))
    return 0 if passed_count == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
