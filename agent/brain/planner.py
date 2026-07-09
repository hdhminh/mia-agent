from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from agent.i18n import t

from agent.skills.registry import DETERMINISTIC_DIRECT_TOOLS, DIRECT_TOOL_DEFAULT_ARGS

from agent.brain.parsers import (
    RequestProfile,
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    looks_multi_step,
    is_soft_followup_only,
    strip_prefixes,
    strip_conversational_fillers,
    extract_sheet_range,
    _calendar_range_from_text,
    extract_github_repo_context,
    extract_news_topic,
    news_topic_to_feed_slug,
    looks_like_news_request,
    extract_shortlink_parts,
    extract_first_url,
)
from agent.brain.parsers.common import SOFT_FOLLOWUP_PATTERN, GENERAL_TOOL_OVERVIEW_CUES
from agent.brain.parsers.google import (
    _infer_google_service,
    _infer_calendar_hint,
    _infer_gmail_hint,
    _infer_workspace_hint,
)
from agent.brain.parsers.github import (
    _infer_github_hint,
    GITHUB_ACCOUNT_REPO_CUES,
    GITHUB_REPO_SEARCH_CUES,
)
from agent.brain.parsers.media import (
    _infer_media_hint,
)


def is_general_tool_overview_request(text: str) -> bool:
    normalized = normalize_query_text(text)
    if not normalized:
        return False
    if not any(cue in normalized for cue in GENERAL_TOOL_OVERVIEW_CUES):
        return False
    domain_cues = (
        "gmail",
        "mail",
        "email",
        "calendar",
        "lich",
        "lịch",
        "drive",
        "docs",
        "doc",
        "sheet",
        "sheets",
        "weather",
        "thoi tiet",
        "gia vang",
        "vang",
        "news",
        "tin tuc",
        "search",
        "shortlink",
        "memory",
    )
    return not any(keyword_matches(normalized, cue) for cue in domain_cues)

def is_current_time_request(normalized: str) -> bool:
    if not normalized:
        return False
    patterns = (
        r"\bhom nay la thu may\b",
        r"\bhom nay thu may\b",
        r"\bthu may hom nay\b",
        r"\bthu may\b",
        r"\bhom nay la ngay may\b",
        r"\bngay may hom nay\b",
        r"\bngay may\b",
        r"\bngay bao nhieu\b",
        r"\bmay gio\b",
        r"\bgio hien tai\b",
        r"\bgio bay gio\b",
        r"\bthoi gian hien tai\b",
        r"\bcurrent time\b",
        r"\bcurrent date\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def infer_request_profile(text: str, metadata: dict[str, Any] | None = None) -> RequestProfile:
    normalized = normalize_query_text(text)
    if not normalized:
        return RequestProfile(domain="general", hint_tool="", direct_confident=False, reason="empty request")

    if is_general_tool_overview_request(text):
        return RequestProfile(
            domain="general",
            hint_tool="__capabilities_overview__",
            direct_confident=False,
            reason="general capability overview",
        )

    if looks_like_news_request(text):
        news_topic = extract_news_topic(text)
        if news_topic and not news_topic_to_feed_slug(news_topic):
            return RequestProfile(domain="general", hint_tool="search_web", direct_confident=True, reason="news topic needs web search")
        return RequestProfile(domain="general", hint_tool="news_get", direct_confident=True, reason="explicit news request")

    if any_keyword_matches(normalized, ("thoi tiet", "weather", "nhiet do", "nhiệt độ", "du bao", "dự báo")):
        return RequestProfile(domain="general", hint_tool="weather_get", direct_confident=True, reason="weather request")

    if is_current_time_request(normalized):
        return RequestProfile(domain="general", hint_tool="time_now", direct_confident=True, reason="current date/time request")

    if any_keyword_matches(normalized, ("gia vang", "sjc", "gold")):
        return RequestProfile(domain="general", hint_tool="gold_get_price", direct_confident=True, reason="gold request")

    if any_keyword_matches(normalized, ("ban con nho gi", "ban còn nhớ gì", "nho gi gan day", "nhớ gì gần đây", "memory gan day", "da luu gi", "đã lưu gì")):
        return RequestProfile(domain="general", hint_tool="memory_recent", direct_confident=True, reason="memory recent request")

    if any_keyword_matches(normalized, ("shortlink", "short link", "rut gon link", "rút gọn link", "tao link ngan", "tạo link ngắn")):
        return RequestProfile(domain="general", hint_tool="shortlink_create", direct_confident=True, reason="shortlink request")

    from agent.brain.parsers.common import HELP_REQUEST_CUES
    help_request = any(keyword_matches(normalized, cue) for cue in HELP_REQUEST_CUES)

    if any_keyword_matches(normalized, ("github help", "help github", "github huong dan", "github hướng dẫn", "help repo github")):
        return RequestProfile(domain="github", hint_tool="github_help", direct_confident=True, reason="github help request")

    if any_keyword_matches(normalized, GITHUB_ACCOUNT_REPO_CUES):
        return RequestProfile(domain="github", hint_tool="github_list_user_repos", direct_confident=True, reason="github account repos request")

    if any_keyword_matches(normalized, GITHUB_REPO_SEARCH_CUES):
        return RequestProfile(domain="github", hint_tool="github_search_repos", direct_confident=True, reason="github repo search request")

    github_context = extract_github_repo_context(text, metadata)
    if github_context:
        hint_tool, direct_confident = _infer_github_hint(normalized, metadata, help_request)
        return RequestProfile(domain="github", hint_tool=hint_tool, direct_confident=direct_confident, reason="github repo request")

    explicit_url = ""
    if metadata:
        explicit_url = str(
            metadata.get("url")
            or metadata.get("link")
            or metadata.get("sourceUrl")
            or metadata.get("source_url")
            or ""
        ).strip()
    explicit_url = explicit_url or extract_first_url(text)
    if explicit_url:
        from agent.brain.parsers.web import URL_SUMMARY_CUES, URL_ASK_CUES, URL_READ_CUES
        if any_keyword_matches(normalized, URL_SUMMARY_CUES):
            return RequestProfile(domain="general", hint_tool="summarize_url", direct_confident=True, reason="specific url summary request")
        if any_keyword_matches(normalized, URL_ASK_CUES):
            return RequestProfile(domain="general", hint_tool="ask_url", direct_confident=False, reason="specific url question request")
        if any_keyword_matches(normalized, URL_READ_CUES) or normalize_query_text(text) == normalize_query_text(explicit_url):
            return RequestProfile(domain="general", hint_tool="read_url", direct_confident=True, reason="specific url read request")
        return RequestProfile(domain="general", hint_tool="read_url", direct_confident=True, reason="specific url read request")

    from agent.brain.parsers.web import URL_ASK_CUES
    if any_keyword_matches(normalized, URL_ASK_CUES):
        return RequestProfile(domain="general", hint_tool="ask_url", direct_confident=False, reason="url follow-up request")

    media_hint, media_confident = _infer_media_hint(normalized, metadata, help_request)
    if media_hint:
        if media_hint == "drive_upload_file":
            return RequestProfile(
                domain="workspace",
                hint_tool=media_hint,
                direct_confident=True,
                reason="attachment save request",
            )
        if media_hint == "tts_speak":
            return RequestProfile(
                domain="media",
                hint_tool=media_hint,
                direct_confident=media_confident,
                reason="voice output request",
            )
        return RequestProfile(
            domain="media",
            hint_tool=media_hint,
            direct_confident=media_confident,
            reason="media attachment request",
        )

    domain = _infer_google_service(normalized)

    if domain == "calendar":
        hint_tool, direct_confident = _infer_calendar_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason="calendar domain")
    if domain == "gmail":
        hint_tool, direct_confident = _infer_gmail_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason="gmail domain")
    if domain == "google_full":
        return RequestProfile(domain=domain, hint_tool="", direct_confident=False, reason="multi-google domain")
    if domain == "workspace":
        hint_tool, direct_confident = _infer_workspace_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason=f"{domain} domain")

    if any_keyword_matches(normalized, ("tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "cho toi biet", "cho tôi biết", "thong tin ve", "thông tin về")):
        if not re.search(r"\b(tin tuc|tin tức|doc bao|đọc báo|bao hom nay|báo hôm nay|bao moi|báo mới|tin moi|tin mới|news)\b", normalized):
            return RequestProfile(domain="general", hint_tool="search_web", direct_confident=True, reason="web search request")

    return RequestProfile(domain="general", hint_tool="", direct_confident=False, reason="fallback general reasoning")


def tool_hint_for_request(text: str, metadata: dict[str, Any] | None = None) -> str:
    return infer_request_profile(text, metadata).hint_tool


def should_allow_direct_route(
    hint_tool: str,
    request_text: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    normalized = normalize_query_text(request_text)
    if hint_tool == "github_get_file" and any_keyword_matches(
        normalized,
        (
            "readme",
            "tóm tắt readme",
            "tom tat readme",
            "summary readme",
            "summarize readme",
            "overview readme",
        ),
    ):
        return False
    profile = infer_request_profile(request_text, metadata)
    return bool(hint_tool) and hint_tool in DETERMINISTIC_DIRECT_TOOLS and profile.direct_confident


def build_direct_tool_args(
    tool_name: str,
    request_text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = strip_conversational_fillers(request_text)
    normalized = normalize_query_text(text)
    metadata = metadata or {}

    def strip_soft_followup(value: str) -> str:
        return " ".join(SOFT_FOLLOWUP_PATTERN.sub(" ", value or "").split()).strip()

    def has_meaningful_value(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    def with_optional_instruction(payload: dict[str, Any], *meaningful_values: Any) -> dict[str, Any]:
        result = dict(payload)
        if any(has_meaningful_value(value) for value in meaningful_values):
            return result
        result["instruction"] = text
        return result

    def normalize_url_instruction(value: str, url: str, *, fallback: str) -> str:
        cleaned = str(value or "")
        if url:
            cleaned = cleaned.replace(url, " ")
        cleaned = " ".join(cleaned.split()).strip()
        if normalize_query_text(cleaned) in {"nay", "link nay", "bai nay", "trang nay"}:
            cleaned = ""
        return cleaned or fallback

    if tool_name == "time_now":
        return {}

    if tool_name == "weather_get":
        location = strip_prefixes(
            text,
            ("thoi tiet", "thời tiết", "weather", "nhiet do", "nhiệt độ", "du bao thoi tiet", "dự báo thời tiết"),
        )
        location = re.sub(r"^(tai|tại|o|ở|cho toi|cho tôi|hom nay|hôm nay|in|at|today)\s+", "", location, flags=re.IGNORECASE)
        location = re.sub(
            r"\b(hom nay|hôm nay|bay gio|bây giờ|the nao|thế nào|ra sao|nhu the nao|như thế nào|today|now|how|how's)\b",
            "",
            location,
            flags=re.IGNORECASE,
        )
        return {"location": location.strip()}

    if tool_name == "news_get":
        topic = extract_news_topic(text)
        topic = strip_soft_followup(topic)
        feed_topic = news_topic_to_feed_slug(topic or text)
        return {"topic": (feed_topic or topic).strip()}

    if tool_name == "search_web":
        query = strip_prefixes(
            text,
            ("tim", "tìm", "tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "cho toi biet ve", "cho tôi biết về", "thong tin ve", "thông tin về", "find", "search for", "look up", "tell me about", "information about", "info on"),
        )
        query = strip_soft_followup(query)
        if query == text:
            news_topic = extract_news_topic(text)
            if news_topic:
                query = f"{news_topic} news"
        return {"query": query.strip()}

    if tool_name == "shortlink_create":
        url, ttl = extract_shortlink_parts(text)
        return {"url": url, "ttl": ttl}

    if tool_name in {"read_url", "summarize_url"}:
        url = str(
            metadata.get("url")
            or metadata.get("link")
            or metadata.get("sourceUrl")
            or metadata.get("source_url")
            or ""
        ).strip()
        if not url:
            url = extract_first_url(text)
        instruction = strip_soft_followup(
            strip_prefixes(
                text,
                (
                    "doc link",
                    "đọc link",
                    "xem link",
                    "mo link",
                    "mở link",
                    "open link",
                    "read link",
                    "tom tat link",
                    "tóm tắt link",
                    "summary link",
                    "summarize link",
                    "phan tich link",
                    "phân tích link",
                ),
            )
        )
        instruction = normalize_url_instruction(
            instruction,
            url,
            fallback=t("skills.web_scrape_fallback", default="tóm tắt link này") if tool_name == "summarize_url" else t("skills.web_read_fallback", default="đọc link này"),
        )
        max_chars_value = metadata.get("maxChars") or metadata.get("max_chars") or 0
        try:
            max_chars = max(0, int(max_chars_value))
        except (TypeError, ValueError):
            max_chars = 0
        fetch_strategy = str(metadata.get("fetchStrategy") or metadata.get("fetch_strategy") or "").strip() or "auto"
        return {
            "url": url.strip(),
            "instruction": instruction.strip() or text,
            "text": instruction.strip() or text,
            "prompt": instruction.strip() or text,
            "fetchStrategy": fetch_strategy,
            "max_chars": max_chars,
        }

    if tool_name == "ask_url":
        url = str(
            metadata.get("url")
            or metadata.get("link")
            or metadata.get("sourceUrl")
            or metadata.get("source_url")
            or ""
        ).strip()
        if not url:
            url = extract_first_url(text)
        instruction = strip_soft_followup(
            strip_prefixes(
                text,
                (
                    "hoi tiep link",
                    "hỏi tiếp link",
                    "doc link",
                    "đọc link",
                    "xem link",
                    "mo link",
                    "mở link",
                    "trong link nay",
                    "trong link này",
                    "trong bai nay",
                    "trong bài này",
                    "link nay",
                    "link này",
                    "bai nay",
                    "bài này",
                ),
            )
        )
        instruction = normalize_url_instruction(
            instruction,
            url,
            fallback=t("skills.url_followup_fallback", default="hỏi tiếp link này"),
        )
        max_chars_value = metadata.get("maxChars") or metadata.get("max_chars") or 0
        try:
            max_chars = max(0, int(max_chars_value))
        except (TypeError, ValueError):
            max_chars = 0
        fetch_strategy = str(metadata.get("fetchStrategy") or metadata.get("fetch_strategy") or "").strip() or "auto"
        return {
            "url": url.strip(),
            "instruction": instruction.strip() or text,
            "question": instruction.strip() or text,
            "text": instruction.strip() or text,
            "prompt": instruction.strip() or text,
            "fetchStrategy": fetch_strategy,
            "max_chars": max_chars,
        }

    if tool_name in {
        "github_help",
        "github_list_user_repos",
        "github_search_repos",
        "github_get_repo",
        "github_get_repo_tree",
        "github_list_branches",
        "github_list_commits",
        "github_get_commit",
        "github_list_releases",
        "github_get_release",
        "github_list_pull_requests",
        "github_get_pull_request",
        "github_list_issues",
        "github_get_issue",
        "github_get_file",
        "github_search_code",
        "github_get_diff",
    }:
        context = extract_github_repo_context(text, metadata)

        def clean_repo_value(*keys: str) -> str:
            for key in keys:
                value = str(metadata.get(key) or "").strip()
                if value:
                    return value
            return ""

        repo = context.get("repo") or clean_repo_value("repo")
        owner = context.get("owner") or clean_repo_value("owner")
        repo_name = context.get("repoName") or clean_repo_value("repoName", "repo_name")
        repo_url = context.get("repoUrl") or clean_repo_value("repoUrl", "repo_url")
        path = context.get("path") or clean_repo_value("path", "filePath", "file_path")
        ref = context.get("ref") or clean_repo_value("ref")
        base = clean_repo_value("base", "baseRef", "base_ref")
        head = clean_repo_value("head", "headRef", "head_ref")
        query = clean_repo_value("query")
        number = context.get("number") or clean_repo_value("number", "issueNumber", "issue_number", "prNumber", "pr_number", "pullRequestNumber", "pull_request_number")
        tag = context.get("tag") or clean_repo_value("tag")
        release_id = context.get("releaseId") or clean_repo_value("releaseId", "release_id")
        state = clean_repo_value("state")
        labels = clean_repo_value("labels")

        if not repo and owner and repo_name:
            repo = f"{owner}/{repo_name}"
        if not repo_url and repo:
            repo_url = f"https://github.com/{repo}"

        if tool_name == "github_help":
            return {"instruction": text}

        if tool_name == "github_list_user_repos":
            username = str(
                metadata.get("username")
                or metadata.get("user")
                or metadata.get("account")
                or metadata.get("owner")
                or ""
            ).strip()
            visibility = str(metadata.get("visibility") or "").strip()
            payload = {
                "username": username,
                "visibility": visibility,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
                "page": max(1, int(metadata.get("page") or 1)),
            }
            return with_optional_instruction(payload, payload.get("username"), payload.get("visibility"), payload.get("limit"), payload.get("page"))

        if tool_name == "github_search_repos":
            query_text = strip_prefixes(
                text,
                (
                    "tim repo",
                    "tìm repo",
                    "tim kiem repo",
                    "tìm kiếm repo",
                    "tim kiem cac repo",
                    "tìm kiếm các repo",
                    "tim cac repo",
                    "tìm các repo",
                    "tim repositories",
                    "tìm repositories",
                    "search repo",
                    "search repositories",
                    "find repo",
                    "find repositories",
                    "repo theo topic",
                    "repo theo language",
                    "repo theo ngon ngu",
                    "repo theo ngôn ngữ",
                ),
            )
            query_text = re.sub(
                r"^(hay|hãy|giup|giúp|cho toi|cho tôi)\s+",
                "",
                query_text,
                flags=re.IGNORECASE,
            ).strip()
            query_text = strip_prefixes(
                query_text,
                (
                    "tim repo",
                    "tìm repo",
                    "tim kiem repo",
                    "tìm kiếm repo",
                    "tim kiem cac repo",
                    "tìm kiếm các repo",
                    "tim cac repo",
                    "tìm các repo",
                    "tim repositories",
                    "tìm repositories",
                    "search repo",
                    "search repositories",
                    "find repo",
                    "find repositories",
                    "repo theo topic",
                    "repo theo language",
                    "repo theo ngon ngu",
                    "repo theo ngôn ngữ",
                ),
            )
            query_text = re.sub(r"^(ve|về|about)\s+", "", query_text, flags=re.IGNORECASE).strip()
            query_text = strip_soft_followup(query_text)
            raw_topic = str(metadata.get("topic") or "").strip()
            if not raw_topic:
                topic_match = re.search(
                    r"(?:topic|chu de|chủ đề)\s*[:=\-]?\s*([A-Za-z0-9_.+#-]+)",
                    text,
                    flags=re.IGNORECASE,
                )
                if topic_match:
                    raw_topic = topic_match.group(1).strip()
            language = str(metadata.get("language") or metadata.get("lang") or "").strip()
            if not language:
                lang_match = re.search(
                    r"(?:language|lang|ngon ngu|ngôn ngữ|bang|bằng)\s*[:=\-]?\s*([A-Za-z0-9_.+#-]+)",
                    text,
                    flags=re.IGNORECASE,
                )
                if lang_match:
                    language = lang_match.group(1).strip()
            sort_by = str(metadata.get("sortBy") or metadata.get("sort_by") or "").strip()
            if not sort_by:
                if any_keyword_matches(normalized, ("best match", "khop nhat", "khớp nhất", "relevance")):
                    sort_by = "best_match"
                elif any_keyword_matches(normalized, ("most stars", "nhieu sao nhat", "nhiều sao nhất", "stars nhieu nhat", "stars nhiều nhất")):
                    sort_by = "most_stars"
                elif any_keyword_matches(normalized, ("fewest stars", "it sao nhat", "ít sao nhất", "stars it nhat", "stars ít nhất")):
                    sort_by = "fewest_stars"
                elif any_keyword_matches(normalized, ("most forks", "nhieu fork nhat", "nhiều fork nhất", "forks nhieu nhat", "forks nhiều nhất")):
                    sort_by = "most_forks"
                elif any_keyword_matches(normalized, ("fewest forks", "it fork nhat", "ít fork nhất", "forks it nhat", "forks ít nhất")):
                    sort_by = "fewest_forks"
                elif any_keyword_matches(normalized, ("recently updated", "cap nhat gan day", "cập nhật gần đây", "newest update")):
                    sort_by = "recently_updated"
                elif any_keyword_matches(normalized, ("least recently updated", "cap nhat lau nhat", "cập nhật lâu nhất", "oldest update")):
                    sort_by = "least_recently_updated"
            query_value = query_text.strip() or raw_topic or text
            query_value = re.sub(
                r"\b(tren github|trên github|github|sort by|sort|order|best match|relevance|khop nhat|khớp nhất|nhiều sao nhất|nhieu sao nhat|ít sao nhất|it sao nhat|nhiều fork nhất|nhieu fork nhat|ít fork nhất|it fork nhat|cập nhật gần đây|cap nhat gan day|cập nhật lâu nhất|cap nhat lau nhat)\b",
                " ",
                query_value,
                flags=re.IGNORECASE,
            )
            query_value = " ".join(query_value.split()).strip()
            if not query_value:
                query_value = raw_topic or text
            payload = {
                "query": query_value,
                "topic": raw_topic,
                "language": language,
                "sortBy": sort_by,
                "limit": max(1, min(int(metadata.get("limit") or 10), 100)),
                "page": max(1, int(metadata.get("page") or 1)),
            }
            return with_optional_instruction(payload, payload.get("query"), payload.get("topic"), payload.get("language"), payload.get("sortBy"), payload.get("limit"), payload.get("page"))

        if tool_name == "github_get_repo_tree":
            tree_path = path or str(metadata.get("path") or metadata.get("filePath") or metadata.get("file_path") or "").strip()
            if tree_path.endswith("/"):
                tree_path = tree_path.rstrip("/")
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "path": tree_path,
                "ref": ref,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("path"), payload.get("ref"), payload.get("limit"))

        if tool_name == "github_search_code":
            query_text = strip_prefixes(
                text,
                (
                    "tim code",
                    "tìm code",
                    "tim code trong repo",
                    "tìm code trong repo",
                    "search code",
                    "tim trong repo",
                    "tìm trong repo",
                    "search in repo",
                    "find code",
                    "find in repo",
                ),
            )
            query_text = strip_soft_followup(query_text)
            if not query_text:
                query_text = query or text
            if repo and "repo:" not in query_text:
                query_text = f"{query_text} repo:{repo}".strip()
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "query": query_text.strip(),
                "limit": max(1, min(int(metadata.get("limit") or 10), 10)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("query"), payload.get("limit"))

        if tool_name == "github_get_file":
            file_path = path or str(metadata.get("path") or metadata.get("filePath") or metadata.get("file_path") or "").strip()
            if not file_path:
                file_path = strip_prefixes(
                    text,
                    (
                        "doc file",
                        "đọc file",
                        "xem file",
                        "read file",
                        "source file",
                        "file",
                    ),
                )
                file_path = re.split(r"\b(?:trong repo|trong repository|repo|repository)\b", file_path, flags=re.IGNORECASE)[0].strip()
                file_path = strip_soft_followup(file_path)
            file_path = file_path.strip().rstrip("/").strip()
            if re.search(r"\breadme\b", file_path, flags=re.IGNORECASE):
                file_path = "README.md"
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "path": file_path,
                "ref": ref,
                "maxChars": max(0, int(metadata.get("maxChars") or metadata.get("max_chars") or 4000)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("path"), payload.get("ref"), payload.get("maxChars"))

        if tool_name == "github_get_diff":
            if not base or not head:
                diff_match = re.search(r"\b([A-Za-z0-9_.:/-]+)\.\.\.([A-Za-z0-9_.:/-]+)\b", text)
                if diff_match:
                    base = base or diff_match.group(1)
                    head = head or diff_match.group(2)
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "base": base,
                "head": head,
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("base"), payload.get("head"))

        if tool_name == "github_get_commit":
            commit_ref = ref
            if not commit_ref:
                sha_match = re.search(r"\b[0-9a-f]{7,40}\b", text, flags=re.IGNORECASE)
                if sha_match:
                    commit_ref = sha_match.group(0)
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "ref": commit_ref,
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("ref"))

        if tool_name == "github_list_releases":
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "limit": max(1, min(int(metadata.get("limit") or 10), 100)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("limit"))

        if tool_name == "github_get_release":
            release_tag = str(tag or "").strip()
            release_ref = str(release_id or "").strip()
            if not release_tag and not release_ref:
                tag_match = re.search(
                    r"(?:release\s+tag|tag|version)\s*[:=#-]?\s*([A-Za-z0-9_.+-]+)",
                    text,
                    flags=re.IGNORECASE,
                )
                if tag_match:
                    release_tag = tag_match.group(1).strip()
            if not release_tag and not release_ref and any_keyword_matches(normalized, ("latest", "moi nhat", "mới nhất", "newest release", "recent release")):
                release_ref = "latest"
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "tag": release_tag,
                "releaseId": release_ref,
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("tag"), payload.get("releaseId"))

        if tool_name == "github_list_pull_requests":
            pr_state = state.strip() or ""
            if not pr_state:
                if any_keyword_matches(normalized, ("closed", "đóng", "dong", "resolved", "done")):
                    pr_state = "closed"
                elif any_keyword_matches(normalized, ("all", "tat ca", "tất cả", "mọi", "full")):
                    pr_state = "all"
                else:
                    pr_state = "open"
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "state": pr_state,
                "limit": max(1, min(int(metadata.get("limit") or 10), 100)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("state"), payload.get("limit"))

        if tool_name == "github_get_pull_request":
            pr_number = str(number or "").strip()
            if not pr_number:
                pr_match = re.search(
                    r"(?:pull request|pull|pr)\s*#?\s*(\d+)",
                    text,
                    flags=re.IGNORECASE,
                )
                if pr_match:
                    pr_number = pr_match.group(1).strip()
            if not pr_number:
                pr_match = re.search(r"\b#(\d+)\b", text)
                if pr_match:
                    pr_number = pr_match.group(1).strip()
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "number": pr_number,
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("number"))

        if tool_name == "github_list_issues":
            issue_state = state.strip() or ""
            if not issue_state:
                if any_keyword_matches(normalized, ("closed", "đóng", "dong", "resolved", "done")):
                    issue_state = "closed"
                elif any_keyword_matches(normalized, ("all", "tat ca", "tất cả", "mọi", "full")):
                    issue_state = "all"
                else:
                    issue_state = "open"
            if not labels:
                label_match = re.search(
                    r"(?:label|labels|nhan|nhãn)\s*[:=#-]?\s*([A-Za-z0-9_,.+-]+)",
                    text,
                    flags=re.IGNORECASE,
                )
                if label_match:
                    labels = label_match.group(1).strip()
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "state": issue_state,
                "labels": labels,
                "limit": max(1, min(int(metadata.get("limit") or 10), 100)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("state"), payload.get("labels"), payload.get("limit"))

        if tool_name == "github_get_issue":
            issue_number = str(number or "").strip()
            if not issue_number:
                issue_match = re.search(
                    r"(?:issue|issues)\s*#?\s*(\d+)",
                    text,
                    flags=re.IGNORECASE,
                )
                if issue_match:
                    issue_number = issue_match.group(1).strip()
            if not issue_number:
                issue_match = re.search(r"\b#(\d+)\b", text)
                if issue_match:
                    issue_number = issue_match.group(1).strip()
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "number": issue_number,
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("number"))

        if tool_name == "github_list_commits":
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "ref": ref,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("ref"), payload.get("limit"))

        if tool_name == "github_list_branches":
            payload = {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
            }
            return with_optional_instruction(payload, payload.get("repo"), payload.get("limit"))

        payload = {
            "repo": repo,
            "owner": owner,
            "repoName": repo_name,
            "repoUrl": repo_url,
        }
        return with_optional_instruction(payload, payload.get("repo"), payload.get("owner"), payload.get("repoName"), payload.get("repoUrl"))

    if tool_name in {
        "image_ocr",
        "image_describe",
        "image_extract_fields",
        "document_extract_text",
        "document_summarize",
        "document_search_answer",
        "document_extract_fields",
        "audio_transcribe",
        "audio_summarize",
        "video_transcribe",
        "video_summarize",
        "tts_speak",
    }:
        file_id = str(metadata.get("fileId") or "").strip()
        file_name = str(metadata.get("fileName") or "").strip()
        mime_type = str(metadata.get("mimeType") or "").strip()
        attachment_kind = str(metadata.get("attachmentKind") or "").strip()
        has_attachment = bool(metadata.get("hasAttachment"))
        payload = {
            "instruction": text,
            "text": text,
            "question": text,
            "prompt": text,
            "fileId": file_id,
            "telegramFileId": file_id,
            "fileName": file_name,
            "mimeType": mime_type,
            "attachmentKind": attachment_kind,
            "hasAttachment": has_attachment,
        }
        if tool_name in {"audio_transcribe", "audio_summarize", "video_transcribe", "video_summarize"}:
            payload["language"] = metadata.get("language") or ""
        if tool_name == "tts_speak":
            spoken = strip_prefixes(
                text,
                (
                    "doc thanh giong noi",
                    "đọc thành giọng nói",
                    "doc to len",
                    "đọc to lên",
                    "noi lai",
                    "nói lại",
                    "voice",
                ),
            )
            spoken = strip_soft_followup(spoken)
            payload.update(
                {
                    "text": spoken or text,
                    "prompt": spoken or text,
                    "voice": str(metadata.get("voice") or "").strip(),
                    "model": str(metadata.get("model") or "").strip(),
                }
            )
        if tool_name in {"document_search_answer"}:
            query = strip_prefixes(text, ("hoi", "hỏi", "search", "tim trong", "tìm trong", "trong file co", "trong file có", "ask", "find in", "in file"))
            query = strip_soft_followup(query)
            payload["question"] = query.strip() or text
            payload["text"] = query.strip() or text
            payload["prompt"] = query.strip() or text
        if tool_name in {"document_summarize", "audio_summarize", "video_summarize"}:
            payload["prompt"] = text
        if tool_name in {"image_ocr", "document_extract_text", "audio_transcribe", "video_transcribe"}:
            payload["prompt"] = text
        return payload

    if tool_name == "docs_search_doc":
        payload = {
            "query": str(metadata.get("query") or metadata.get("docName") or metadata.get("targetName") or "").strip(),
            "docName": str(metadata.get("docName") or metadata.get("query") or metadata.get("targetName") or "").strip(),
            "targetName": str(metadata.get("targetName") or metadata.get("docName") or metadata.get("query") or "").strip(),
            "folderId": str(metadata.get("folderId") or metadata.get("folder_id") or "").strip(),
            "limit": int(metadata.get("limit") or 3) if str(metadata.get("limit") or "").strip() else 3,
        }
        if not str(payload.get("query") or "").strip():
            query = strip_prefixes(text, ("tim doc", "tìm doc", "search doc", "tim tai lieu", "tìm tài liệu"))
            query = strip_soft_followup(query).strip()
            payload["query"] = query
            payload["docName"] = query
            payload["targetName"] = query
        payload["limit"] = max(1, min(int(payload.get("limit") or 3), 8))
        return with_optional_instruction(
            payload,
            payload.get("query"),
            payload.get("docName"),
            payload.get("targetName"),
            payload.get("folderId"),
        )

    if tool_name == "drive_search_file":
        payload = {
            "query": str(metadata.get("query") or "").strip(),
            "fileName": str(metadata.get("fileName") or metadata.get("query") or "").strip(),
            "mimeType": str(metadata.get("mimeType") or metadata.get("mime_type") or "").strip(),
            "folderId": str(metadata.get("folderId") or metadata.get("folder_id") or "").strip(),
            "limit": int(metadata.get("limit") or 3) if str(metadata.get("limit") or "").strip() else 3,
        }
        if not str(payload.get("query") or "").strip():
            query = strip_prefixes(text, ("tim file", "tìm file", "search file", "tim trong drive", "tìm trong drive", "tim tep", "tìm tệp"))
            query = strip_soft_followup(query).strip()
            payload["query"] = query
            payload["fileName"] = query
        payload["limit"] = max(1, min(int(payload.get("limit") or 3), 8))
        return with_optional_instruction(
            payload,
            payload.get("query"),
            payload.get("fileName"),
            payload.get("mimeType"),
            payload.get("folderId"),
        )

    if tool_name == "sheets_search_sheet":
        payload = {
            "query": str(metadata.get("query") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
            "sheetName": str(metadata.get("sheetName") or metadata.get("query") or metadata.get("targetName") or "").strip(),
            "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("query") or "").strip(),
            "folderId": str(metadata.get("folderId") or metadata.get("folder_id") or "").strip(),
            "limit": int(metadata.get("limit") or 3) if str(metadata.get("limit") or "").strip() else 3,
        }
        if not str(payload.get("query") or "").strip():
            query = strip_prefixes(text, ("tim sheet", "tìm sheet", "search sheet", "tim bang tinh", "tìm bảng tính"))
            query = strip_soft_followup(query).strip()
            payload["query"] = query
            payload["sheetName"] = query
            payload["targetName"] = query
        payload["limit"] = max(1, min(int(payload.get("limit") or 3), 8))
        return with_optional_instruction(
            payload,
            payload.get("query"),
            payload.get("sheetName"),
            payload.get("targetName"),
            payload.get("folderId"),
        )

    if tool_name == "sheets_read_range":
        payload = {
            "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("fileId") or metadata.get("targetId") or "").strip(),
            "sheetId": str(metadata.get("sheetId") or metadata.get("spreadsheetId") or metadata.get("fileId") or metadata.get("targetId") or "").strip(),
            "fileId": str(metadata.get("fileId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
            "targetId": str(metadata.get("targetId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("fileId") or "").strip(),
            "sheetName": str(metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
            "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
            "fileName": str(metadata.get("fileName") or metadata.get("sheetName") or metadata.get("targetName") or metadata.get("title") or metadata.get("query") or "").strip(),
            "title": str(metadata.get("title") or metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("query") or "").strip(),
            "query": str(metadata.get("query") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
            "range": str(metadata.get("range") or metadata.get("rangeName") or "").strip(),
            "rangeName": str(metadata.get("rangeName") or metadata.get("range") or "").strip(),
            "sheetTab": str(metadata.get("sheetTab") or metadata.get("sheet_tab") or "").strip(),
        }
        if not any(
            str(payload.get(key) or "").strip()
            for key in ("spreadsheetId", "sheetId", "fileId", "targetId", "sheetName", "targetName", "fileName", "title", "query")
        ):
            sheet_range = extract_sheet_range(text)
            sheet_name = strip_prefixes(
                text,
                (
                    "xem vung sheet",
                    "xem vùng sheet",
                    "xem range sheet",
                    "read range sheet",
                    "xem range",
                    "xem vung",
                    "xem vùng",
                    "read range",
                    "doc range",
                    "đọc range",
                    "xem sheet",
                    "doc sheet",
                    "đọc sheet",
                ),
            )
            if sheet_range:
                sheet_name = sheet_name.replace(sheet_range, " ")
                payload["range"] = payload.get("range") or sheet_range
                payload["rangeName"] = payload.get("rangeName") or sheet_range
            sheet_name = strip_soft_followup(" ".join(sheet_name.split())).strip()
            payload["sheetName"] = sheet_name
            payload["targetName"] = sheet_name
            payload["fileName"] = sheet_name
            payload["title"] = sheet_name
            payload["query"] = sheet_name
        return with_optional_instruction(
            payload,
            payload.get("spreadsheetId"),
            payload.get("sheetId"),
            payload.get("fileId"),
            payload.get("targetId"),
            payload.get("sheetName"),
            payload.get("targetName"),
            payload.get("fileName"),
            payload.get("title"),
            payload.get("query"),
            payload.get("range"),
            payload.get("rangeName"),
            payload.get("sheetTab"),
        )

    if tool_name == "sheets_update_range":
        sheet_range = extract_sheet_range(text)
        sheet_name = strip_prefixes(
            text,
            ("cap nhat range", "cập nhật range", "cap nhat vung", "cập nhật vùng", "update range", "cap nhat sheet", "cập nhật sheet"),
        )
        if sheet_range:
            sheet_name = sheet_name.replace(sheet_range, " ")
        sheet_name = strip_soft_followup(" ".join(sheet_name.split()))
        sheet_name = sheet_name.strip()
        spreadsheet_id = str(metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip()
        target_name = str(metadata.get("targetName") or metadata.get("sheetName") or sheet_name or "").strip()
        range_name = str(metadata.get("rangeName") or sheet_range or "").strip()
        content_value = str(metadata.get("content") or "").strip()
        values = metadata.get("values") or []
        payload = {
            "spreadsheetId": spreadsheet_id,
            "targetId": spreadsheet_id,
            "sheetName": target_name or sheet_name,
            "targetName": target_name or sheet_name,
            "fileName": target_name or sheet_name,
            "range": sheet_range,
            "rangeName": range_name or sheet_range,
            "content": content_value,
            "values": values,
        }
        return with_optional_instruction(
            payload,
            payload.get("spreadsheetId"),
            payload.get("targetId"),
            payload.get("sheetName"),
            payload.get("targetName"),
            payload.get("range"),
            payload.get("rangeName"),
            payload.get("content"),
            payload.get("values"),
        )

    if tool_name == "gmail_search_email":
        payload = {
            "query": str(metadata.get("query") or "").strip(),
            "sender": str(metadata.get("sender") or "").strip(),
            "subject": str(metadata.get("subject") or "").strip(),
            "limit": int(metadata.get("limit") or 3) if str(metadata.get("limit") or "").strip() else 3,
        }
        if not any(str(payload.get(key) or "").strip() for key in ("query", "sender", "subject")):
            query = strip_prefixes(text, ("tim mail", "tìm mail", "tim email", "tìm email", "search mail", "search email"))
            payload["query"] = strip_soft_followup(query).strip()
        payload["limit"] = max(1, min(int(payload.get("limit") or 3), 5))
        return with_optional_instruction(payload, payload.get("query"), payload.get("sender"), payload.get("subject"))

    if tool_name == "gmail_search_by_sender":
        payload = {
            "sender": str(metadata.get("sender") or "").strip(),
            "query": str(metadata.get("query") or metadata.get("sender") or "").strip(),
            "subject": str(metadata.get("subject") or "").strip(),
            "limit": int(metadata.get("limit") or 3) if str(metadata.get("limit") or "").strip() else 3,
        }
        if not str(payload.get("sender") or "").strip():
            sender = strip_prefixes(text, ("tim email tu", "tìm email từ", "tim mail tu", "tìm mail từ", "from", "sender"))
            sender = re.sub(r"^(tu|từ|from)\s+", "", sender, flags=re.IGNORECASE)
            sender = strip_soft_followup(sender).strip()
            payload["sender"] = sender
            if not str(payload.get("query") or "").strip():
                payload["query"] = sender
        payload["limit"] = max(1, min(int(payload.get("limit") or 3), 5))
        return with_optional_instruction(payload, payload.get("sender"), payload.get("query"), payload.get("subject"))

    if tool_name in {"gmail_mark_read", "gmail_archive"}:
        query = strip_prefixes(
            text,
            (
                "danh dau da doc",
                "đánh dấu đã đọc",
                "mark as read",
                "mark read",
                "luu tru",
                "lưu trữ",
                "archive",
            ),
        )
        query = strip_soft_followup(query)
        payload = {
            "messageId": str(metadata.get("messageId") or metadata.get("message_id") or "").strip(),
            "query": str(metadata.get("query") or query).strip(),
            "sender": str(metadata.get("sender") or "").strip(),
            "subject": str(metadata.get("subject") or "").strip(),
        }
        return with_optional_instruction(
            payload,
            payload.get("messageId"),
            payload.get("query"),
            payload.get("sender"),
            payload.get("subject"),
        )

    if tool_name == "gmail_read_email":
        query = strip_prefixes(
            text,
            ("doc mail", "đọc mail", "doc email", "đọc email", "read mail", "read email", "chi tiet mail", "chi tiết mail", "chi tiet email", "chi tiết email"),
        )
        query = strip_soft_followup(query)
        payload = {
            "messageId": str(metadata.get("messageId") or metadata.get("message_id") or "").strip(),
            "query": query.strip() or str(metadata.get("query") or "").strip(),
            "sender": str(metadata.get("sender") or "").strip(),
            "subject": str(metadata.get("subject") or "").strip(),
        }
        return with_optional_instruction(payload, payload.get("messageId"), payload.get("query"), payload.get("sender"), payload.get("subject"))

    if tool_name == "docs_read_doc":
        payload = {
            "docId": str(metadata.get("docId") or metadata.get("documentId") or metadata.get("fileId") or metadata.get("targetId") or "").strip(),
            "documentId": str(metadata.get("documentId") or metadata.get("docId") or metadata.get("fileId") or metadata.get("targetId") or "").strip(),
            "fileId": str(metadata.get("fileId") or metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
            "targetId": str(metadata.get("targetId") or metadata.get("documentId") or metadata.get("docId") or metadata.get("fileId") or "").strip(),
            "docName": str(metadata.get("docName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("title") or "").strip(),
            "targetName": str(metadata.get("targetName") or metadata.get("docName") or metadata.get("fileName") or metadata.get("title") or "").strip(),
            "fileName": str(metadata.get("fileName") or metadata.get("docName") or metadata.get("targetName") or metadata.get("title") or "").strip(),
            "title": str(metadata.get("title") or metadata.get("docName") or metadata.get("targetName") or metadata.get("fileName") or "").strip(),
            "maxChars": int(metadata.get("maxChars") or metadata.get("max_chars") or 1000)
            if str(metadata.get("maxChars") or metadata.get("max_chars") or "").strip()
            else 1000,
        }
        if not any(str(payload.get(key) or "").strip() for key in ("docId", "targetId", "docName", "targetName", "fileName", "title")):
            doc_name = strip_prefixes(
                text,
                ("xem doc", "doc doc", "đọc doc", "read doc", "noi dung doc", "nội dung doc", "xem tài liệu", "đọc tài liệu"),
            )
            doc_name = strip_soft_followup(doc_name).strip()
            payload["docName"] = doc_name
            payload["targetName"] = doc_name
            payload["fileName"] = doc_name
            payload["title"] = doc_name
        payload["maxChars"] = max(200, min(int(payload.get("maxChars") or 1000), 3000))
        return with_optional_instruction(
            payload,
            payload.get("docId"),
            payload.get("targetId"),
            payload.get("docName"),
            payload.get("targetName"),
            payload.get("fileName"),
            payload.get("title"),
        )

    if tool_name == "sheets_read_sheet":
        payload = {
            "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("fileId") or metadata.get("targetId") or "").strip(),
            "sheetId": str(metadata.get("sheetId") or metadata.get("spreadsheetId") or metadata.get("fileId") or metadata.get("targetId") or "").strip(),
            "fileId": str(metadata.get("fileId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
            "targetId": str(metadata.get("targetId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("fileId") or "").strip(),
            "sheetName": str(metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
            "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
            "fileName": str(metadata.get("fileName") or metadata.get("sheetName") or metadata.get("targetName") or metadata.get("title") or metadata.get("query") or "").strip(),
            "title": str(metadata.get("title") or metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("query") or "").strip(),
            "query": str(metadata.get("query") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
            "range": str(metadata.get("range") or metadata.get("rangeName") or "").strip(),
            "rangeName": str(metadata.get("rangeName") or metadata.get("range") or "").strip(),
            "sheetTab": str(metadata.get("sheetTab") or metadata.get("sheet_tab") or "").strip(),
        }
        if not any(
            str(payload.get(key) or "").strip()
            for key in ("spreadsheetId", "sheetId", "fileId", "targetId", "sheetName", "targetName", "fileName", "title", "query")
        ):
            sheet_name = strip_prefixes(
                text,
                ("xem sheet", "doc sheet", "đọc sheet", "read sheet", "xem bảng tính", "đọc bảng tính"),
            )
            sheet_range = extract_sheet_range(sheet_name)
            if sheet_range:
                sheet_name = sheet_name.replace(sheet_range, " ")
                payload["range"] = payload.get("range") or sheet_range
                payload["rangeName"] = payload.get("rangeName") or sheet_range
            sheet_name = strip_soft_followup(" ".join(sheet_name.split())).strip()
            payload["sheetName"] = sheet_name
            payload["targetName"] = sheet_name
            payload["fileName"] = sheet_name
            payload["title"] = sheet_name
            payload["query"] = sheet_name
        return with_optional_instruction(
            payload,
            payload.get("spreadsheetId"),
            payload.get("sheetId"),
            payload.get("fileId"),
            payload.get("targetId"),
            payload.get("sheetName"),
            payload.get("targetName"),
            payload.get("fileName"),
            payload.get("title"),
            payload.get("query"),
            payload.get("range"),
            payload.get("rangeName"),
            payload.get("sheetTab"),
        )

    if tool_name == "calendar_find_event":
        payload = {
            "query": str(metadata.get("query") or "").strip(),
            "calendarId": str(metadata.get("calendarId") or metadata.get("calendar_id") or "").strip(),
            "dateFrom": str(metadata.get("dateFrom") or metadata.get("date_from") or "").strip(),
            "dateTo": str(metadata.get("dateTo") or metadata.get("date_to") or "").strip(),
            "limit": int(metadata.get("limit") or 3) if str(metadata.get("limit") or "").strip() else 3,
        }
        if not str(payload.get("query") or "").strip():
            query = strip_prefixes(
                text,
                ("tim lich", "tìm lịch", "tim su kien", "tìm sự kiện", "search event", "find event", "xem lich", "xem lịch", "lich", "lịch"),
            )
            query = re.sub(
                r"\b(hom nay|hôm nay|ngay mai|ngày mai|mai|tuan sau|tuần sau|tuan nay|tuần này|cuoi tuan nay|cuối tuần này|cuoi tuan sau|cuối tuần sau|thu\s*[2-7]|thứ\s*[2-7]|chu nhat|chủ nhật|today|tomorrow|next week|this week|weekend|next weekend|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
                " ",
                query,
                flags=re.IGNORECASE,
            )
            query = strip_soft_followup(" ".join(query.split())).strip()
            payload["query"] = query
        if not str(payload.get("dateFrom") or "").strip() and not str(payload.get("dateTo") or "").strip():
            date_from, date_to = _calendar_range_from_text(text)
            payload["dateFrom"] = date_from
            payload["dateTo"] = date_to
        payload["limit"] = max(1, min(int(payload.get("limit") or 3), 10))
        return with_optional_instruction(
            payload,
            payload.get("query"),
            payload.get("calendarId"),
            payload.get("dateFrom"),
            payload.get("dateTo"),
            payload.get("limit"),
        )

    if tool_name == "calendar_find_free_slot":
        start_at, end_at = _calendar_range_from_text(text)
        duration_minutes = int(metadata.get("durationMinutes") or metadata.get("duration_minutes") or 60)
        payload = {
            "date": str(metadata.get("date") or "").strip(),
            "startAt": str(metadata.get("startAt") or metadata.get("start_at") or metadata.get("start") or start_at).strip(),
            "start": str(metadata.get("start") or metadata.get("startAt") or metadata.get("start_at") or start_at).strip(),
            "endAt": str(metadata.get("endAt") or metadata.get("end_at") or metadata.get("end") or end_at).strip(),
            "end": str(metadata.get("end") or metadata.get("endAt") or metadata.get("end_at") or end_at).strip(),
            "durationMinutes": max(15, min(duration_minutes, 1440)),
            "calendarId": str(metadata.get("calendarId") or metadata.get("calendar_id") or "").strip(),
        }
        return with_optional_instruction(
            payload,
            payload.get("date"),
            payload.get("startAt"),
            payload.get("start"),
            payload.get("endAt"),
            payload.get("end"),
            payload.get("durationMinutes"),
            payload.get("calendarId"),
        )

    if tool_name == "calendar_reschedule_event":
        start_at, end_at = _calendar_range_from_text(text)
        payload = {
            "eventId": str(metadata.get("eventId") or metadata.get("event_id") or "").strip(),
            "query": str(metadata.get("query") or "").strip(),
            "startAt": str(metadata.get("startAt") or metadata.get("start_at") or metadata.get("start") or start_at).strip(),
            "start": str(metadata.get("start") or metadata.get("startAt") or metadata.get("start_at") or start_at).strip(),
            "endAt": str(metadata.get("endAt") or metadata.get("end_at") or metadata.get("end") or end_at).strip(),
            "end": str(metadata.get("end") or metadata.get("endAt") or metadata.get("end_at") or end_at).strip(),
            "timezone": str(metadata.get("timezone") or "").strip(),
            "calendarId": str(metadata.get("calendarId") or metadata.get("calendar_id") or "").strip(),
        }
        if not str(payload.get("query") or "").strip():
            payload["query"] = strip_soft_followup(
                strip_prefixes(text, ("doi lich", "đổi lịch", "doi gio", "đổi giờ", "reschedule", "move meeting", "postpone"))
            )
        return with_optional_instruction(
            payload,
            payload.get("eventId"),
            payload.get("query"),
            payload.get("startAt"),
            payload.get("start"),
            payload.get("endAt"),
            payload.get("end"),
            payload.get("timezone"),
            payload.get("calendarId"),
        )

    if tool_name in {
        "calendar_create_event",
        "calendar_delete_event",
        "calendar_check_availability",
        "gmail_send_email",
        "gmail_draft_email",
        "gmail_reply_email",
        "drive_get_file_info",
        "drive_create_folder",
        "drive_create_file",
        "drive_download_file",
        "drive_share_file",
        "drive_move_file",
        "drive_rename_file",
        "drive_copy_file",
        "drive_delete_file",
        "drive_delete_folder",
        "drive_export_file",
        "docs_create_doc",
        "docs_append_doc",
        "docs_update_doc",
        "docs_delete_doc",
        "sheets_create_sheet",
        "sheets_append_row",
        "sheets_update_cell",
        "sheets_update_range",
        "sheets_delete_sheet",
    }:
        payload: dict[str, Any] = {}
        if tool_name == "docs_update_doc":
            payload.update(
                {
                    "documentId": str(metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
                    "docId": str(metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("documentId") or metadata.get("docId") or "").strip(),
                    "docName": str(metadata.get("docName") or metadata.get("targetName") or metadata.get("doc_name") or metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("docName") or metadata.get("doc_name") or metadata.get("fileName") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("targetName") or metadata.get("docName") or "").strip(),
                    "content": str(metadata.get("content") or metadata.get("text") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("documentId"),
                payload.get("docId"),
                payload.get("targetId"),
                payload.get("docName"),
                payload.get("targetName"),
                payload.get("fileName"),
                payload.get("content"),
            )
        if tool_name == "calendar_create_event":
            payload.update(
                {
                    "title": str(metadata.get("title") or metadata.get("summary") or "").strip(),
                    "summary": str(metadata.get("summary") or metadata.get("title") or "").strip(),
                    "startAt": str(metadata.get("startAt") or metadata.get("start_at") or metadata.get("start") or "").strip(),
                    "start": str(metadata.get("start") or metadata.get("startAt") or metadata.get("start_at") or "").strip(),
                    "endAt": str(metadata.get("endAt") or metadata.get("end_at") or metadata.get("end") or "").strip(),
                    "end": str(metadata.get("end") or metadata.get("endAt") or metadata.get("end_at") or "").strip(),
                    "timezone": str(metadata.get("timezone") or "").strip(),
                    "description": str(metadata.get("description") or "").strip(),
                    "location": str(metadata.get("location") or "").strip(),
                    "calendarId": str(metadata.get("calendarId") or metadata.get("calendar_id") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("title"),
                payload.get("summary"),
                payload.get("startAt"),
                payload.get("endAt"),
                payload.get("description"),
                payload.get("location"),
                payload.get("calendarId"),
            )
        if tool_name == "calendar_delete_event":
            payload.update(
                {
                    "eventId": str(metadata.get("eventId") or metadata.get("event_id") or "").strip(),
                    "query": str(metadata.get("query") or "").strip(),
                    "calendarId": str(metadata.get("calendarId") or metadata.get("calendar_id") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("eventId"), payload.get("query"), payload.get("calendarId"))
        if tool_name == "calendar_check_availability":
            payload.update(
                {
                    "date": str(metadata.get("date") or "").strip(),
                    "startAt": str(metadata.get("startAt") or metadata.get("start_at") or metadata.get("start") or "").strip(),
                    "start": str(metadata.get("start") or metadata.get("startAt") or metadata.get("start_at") or "").strip(),
                    "endAt": str(metadata.get("endAt") or metadata.get("end_at") or metadata.get("end") or "").strip(),
                    "end": str(metadata.get("end") or metadata.get("endAt") or metadata.get("end_at") or "").strip(),
                    "timezone": str(metadata.get("timezone") or "").strip(),
                    "calendarId": str(metadata.get("calendarId") or metadata.get("calendar_id") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("date"),
                payload.get("startAt"),
                payload.get("endAt"),
                payload.get("timezone"),
                payload.get("calendarId"),
            )
        if tool_name == "gmail_send_email":
            payload.update(
                {
                    "to": str(metadata.get("to") or metadata.get("toEmail") or "").strip(),
                    "toEmail": str(metadata.get("toEmail") or metadata.get("to") or "").strip(),
                    "subject": str(metadata.get("subject") or "").strip(),
                    "body": str(metadata.get("body") or "").strip(),
                    "cc": str(metadata.get("cc") or "").strip(),
                    "bcc": str(metadata.get("bcc") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("to"), payload.get("subject"), payload.get("body"), payload.get("cc"), payload.get("bcc"))
        if tool_name == "gmail_draft_email":
            payload.update(
                {
                    "to": str(metadata.get("to") or metadata.get("toEmail") or "").strip(),
                    "toEmail": str(metadata.get("toEmail") or metadata.get("to") or "").strip(),
                    "subject": str(metadata.get("subject") or "").strip(),
                    "body": str(metadata.get("body") or "").strip(),
                    "cc": str(metadata.get("cc") or "").strip(),
                    "bcc": str(metadata.get("bcc") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("to"), payload.get("subject"), payload.get("body"), payload.get("cc"), payload.get("bcc"))
        if tool_name == "gmail_reply_email":
            payload.update(
                {
                    "messageId": str(metadata.get("messageId") or metadata.get("message_id") or "").strip(),
                    "searchQuery": str(metadata.get("searchQuery") or metadata.get("search_query") or metadata.get("query") or "").strip(),
                    "body": str(metadata.get("body") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("messageId"), payload.get("searchQuery"), payload.get("body"))
        if tool_name == "drive_get_file_info":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileId"), payload.get("fileName"), payload.get("targetName"))
        if tool_name == "drive_create_folder":
            payload.update(
                {
                    "name": str(metadata.get("name") or metadata.get("folderName") or metadata.get("targetName") or "").strip(),
                    "folderName": str(metadata.get("folderName") or metadata.get("targetName") or metadata.get("name") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("folderName") or metadata.get("name") or "").strip(),
                    "folderId": str(metadata.get("folderId") or metadata.get("parentId") or metadata.get("targetFolderId") or "").strip(),
                    "targetFolderId": str(metadata.get("targetFolderId") or metadata.get("parentId") or metadata.get("folderId") or "").strip(),
                    "parentId": str(metadata.get("parentId") or metadata.get("targetFolderId") or metadata.get("folderId") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("name"), payload.get("targetName"), payload.get("folderName"), payload.get("folderId"), payload.get("targetFolderId"), payload.get("parentId"))
        if tool_name == "drive_create_file":
            payload.update(
                {
                    "fileName": str(metadata.get("fileName") or metadata.get("name") or metadata.get("targetName") or "").strip(),
                    "name": str(metadata.get("name") or metadata.get("fileName") or metadata.get("targetName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or metadata.get("name") or "").strip(),
                    "content": str(metadata.get("content") or "").strip(),
                    "mimeType": str(metadata.get("mimeType") or metadata.get("mime_type") or "").strip(),
                    "folderId": str(metadata.get("folderId") or metadata.get("parentId") or metadata.get("targetFolderId") or "").strip(),
                    "targetFolderId": str(metadata.get("targetFolderId") or metadata.get("parentId") or metadata.get("folderId") or "").strip(),
                    "parentId": str(metadata.get("parentId") or metadata.get("targetFolderId") or metadata.get("folderId") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileName"), payload.get("targetName"), payload.get("name"), payload.get("content"), payload.get("mimeType"), payload.get("folderId"), payload.get("targetFolderId"))
        if tool_name == "drive_download_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileId"), payload.get("fileName"), payload.get("targetName"))
        if tool_name == "drive_share_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("targetName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "email": str(metadata.get("email") or "").strip(),
                    "role": str(metadata.get("role") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("fileId"),
                payload.get("fileName"),
                payload.get("targetName"),
                payload.get("email"),
                payload.get("role"),
            )
        if tool_name == "drive_move_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or "").strip(),
                    "targetFolderId": str(metadata.get("targetFolderId") or metadata.get("folderId") or "").strip(),
                    "folderId": str(metadata.get("folderId") or metadata.get("targetFolderId") or "").strip(),
                    "targetFolderName": str(metadata.get("targetFolderName") or metadata.get("folderName") or "").strip(),
                    "folderName": str(metadata.get("folderName") or metadata.get("targetFolderName") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileId"), payload.get("fileName"), payload.get("targetFolderId"), payload.get("folderName"))
        if tool_name == "drive_rename_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "newName": str(metadata.get("newName") or metadata.get("new_name") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileId"), payload.get("fileName"), payload.get("newName"))
        if tool_name == "drive_copy_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("targetName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "newName": str(metadata.get("newName") or metadata.get("new_name") or "").strip(),
                    "parentId": str(metadata.get("parentId") or metadata.get("targetFolderId") or "").strip(),
                    "targetFolderId": str(metadata.get("targetFolderId") or metadata.get("parentId") or "").strip(),
                    "targetFolderName": str(metadata.get("targetFolderName") or metadata.get("folderName") or "").strip(),
                    "folderName": str(metadata.get("folderName") or metadata.get("targetFolderName") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("fileId"),
                payload.get("fileName"),
                payload.get("targetName"),
                payload.get("newName"),
                payload.get("parentId"),
                payload.get("targetFolderId"),
                payload.get("targetFolderName"),
            )
        if tool_name == "drive_delete_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileId"), payload.get("fileName"), payload.get("targetName"))
        if tool_name == "drive_delete_folder":
            payload.update(
                {
                    "folderId": str(metadata.get("folderId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("folderId") or "").strip(),
                    "folderName": str(metadata.get("folderName") or metadata.get("targetName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("folderName") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("folderId"), payload.get("targetId"), payload.get("folderName"), payload.get("targetName"))
        if tool_name == "drive_export_file":
            payload.update(
                {
                    "fileId": str(metadata.get("fileId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("fileId") or "").strip(),
                    "fileName": str(metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "mimeType": str(metadata.get("mimeType") or metadata.get("mime_type") or "").strip(),
                    "format": str(metadata.get("format") or metadata.get("mimeType") or metadata.get("mime_type") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("fileId"), payload.get("fileName"), payload.get("mimeType"), payload.get("format"))
        if tool_name == "docs_create_doc":
            title = str(metadata.get("title") or metadata.get("docTitle") or metadata.get("targetName") or metadata.get("fileName") or "").strip()
            target_folder_id = str(metadata.get("targetFolderId") or metadata.get("folderId") or "").strip()
            payload.update(
                {
                    "title": title,
                    "docTitle": str(metadata.get("docTitle") or metadata.get("title") or metadata.get("targetName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("title") or metadata.get("docTitle") or metadata.get("fileName") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("title") or metadata.get("docTitle") or metadata.get("targetName") or "").strip(),
                    "documentTitle": str(metadata.get("documentTitle") or metadata.get("title") or metadata.get("docTitle") or metadata.get("targetName") or "").strip(),
                    "content": str(metadata.get("content") or metadata.get("docContent") or "").strip(),
                    "docContent": str(metadata.get("docContent") or metadata.get("content") or "").strip(),
                    "folderId": target_folder_id,
                    "targetFolderId": target_folder_id,
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("title"),
                payload.get("targetName"),
                payload.get("content"),
                payload.get("folderId"),
                payload.get("targetFolderId"),
            )
        if tool_name == "docs_append_doc":
            payload.update(
                {
                    "docId": str(metadata.get("docId") or metadata.get("documentId") or metadata.get("targetId") or "").strip(),
                    "documentId": str(metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
                    "fileId": str(metadata.get("fileId") or metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("documentId") or metadata.get("docId") or "").strip(),
                    "docName": str(metadata.get("docName") or metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("docName") or metadata.get("fileName") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("targetName") or metadata.get("docName") or "").strip(),
                    "content": str(metadata.get("content") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("docId"),
                payload.get("targetId"),
                payload.get("docName"),
                payload.get("targetName"),
                payload.get("content"),
            )
        if tool_name == "docs_delete_doc":
            payload.update(
                {
                    "docId": str(metadata.get("docId") or metadata.get("documentId") or metadata.get("targetId") or "").strip(),
                    "documentId": str(metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
                    "fileId": str(metadata.get("fileId") or metadata.get("documentId") or metadata.get("docId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("documentId") or metadata.get("docId") or "").strip(),
                    "docName": str(metadata.get("docName") or metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("docName") or metadata.get("fileName") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("targetName") or metadata.get("docName") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("docId"),
                payload.get("targetId"),
                payload.get("docName"),
                payload.get("targetName"),
                payload.get("fileName"),
            )
        if tool_name == "sheets_create_sheet":
            payload.update(
                {
                    "title": str(metadata.get("title") or metadata.get("sheetTitle") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "sheetTitle": str(metadata.get("sheetTitle") or metadata.get("title") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "sheetName": str(metadata.get("sheetName") or metadata.get("title") or metadata.get("sheetTitle") or metadata.get("targetName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("title") or metadata.get("sheetTitle") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("sheetName") or metadata.get("targetName") or metadata.get("title") or "").strip(),
                }
            )
            return with_optional_instruction(payload, payload.get("title"), payload.get("sheetTitle"), payload.get("sheetName"), payload.get("targetName"))
        if tool_name == "sheets_append_row":
            payload.update(
                {
                    "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
                    "sheetId": str(metadata.get("sheetId") or metadata.get("spreadsheetId") or metadata.get("targetId") or "").strip(),
                    "fileId": str(metadata.get("fileId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or "").strip(),
                    "sheetName": str(metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "title": str(metadata.get("title") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "query": str(metadata.get("query") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "sheetTab": str(metadata.get("sheetTab") or metadata.get("sheet_tab") or "").strip(),
                    "rowData": str(metadata.get("rowData") or metadata.get("content") or "").strip(),
                    "content": str(metadata.get("content") or metadata.get("rowData") or "").strip(),
                    "values": metadata.get("values") or [],
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("spreadsheetId"),
                payload.get("targetId"),
                payload.get("sheetName"),
                payload.get("targetName"),
                payload.get("rowData"),
                payload.get("content"),
                payload.get("values"),
                payload.get("sheetTab"),
            )
        if tool_name == "sheets_update_cell":
            payload.update(
                {
                    "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
                    "sheetId": str(metadata.get("sheetId") or metadata.get("spreadsheetId") or metadata.get("targetId") or "").strip(),
                    "fileId": str(metadata.get("fileId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or "").strip(),
                    "sheetName": str(metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("fileName") or metadata.get("title") or metadata.get("query") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "title": str(metadata.get("title") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "query": str(metadata.get("query") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                    "sheetTab": str(metadata.get("sheetTab") or metadata.get("sheet_tab") or "").strip(),
                    "cell": str(metadata.get("cell") or metadata.get("range") or "").strip(),
                    "range": str(metadata.get("range") or metadata.get("rangeName") or metadata.get("cell") or "").strip(),
                    "rangeName": str(metadata.get("rangeName") or metadata.get("range") or metadata.get("cell") or "").strip(),
                    "value": str(metadata.get("value") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("spreadsheetId"),
                payload.get("targetId"),
                payload.get("sheetName"),
                payload.get("targetName"),
                payload.get("cell"),
                payload.get("range"),
                payload.get("rangeName"),
                payload.get("value"),
            )
        if tool_name == "sheets_update_range":
            payload.update(
                {
                    "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or "").strip(),
                    "sheetName": str(metadata.get("sheetName") or metadata.get("targetName") or metadata.get("sheet_name") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("sheet_name") or "").strip(),
                    "range": str(metadata.get("range") or metadata.get("rangeName") or "").strip(),
                    "rangeName": str(metadata.get("rangeName") or metadata.get("range") or metadata.get("cell") or "").strip(),
                    "sheetTab": str(metadata.get("sheetTab") or metadata.get("sheet_tab") or "").strip(),
                    "content": str(metadata.get("content") or metadata.get("text") or text).strip(),
                    "values": metadata.get("values") or [],
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("spreadsheetId"),
                payload.get("targetId"),
                payload.get("sheetName"),
                payload.get("targetName"),
                payload.get("range"),
                payload.get("rangeName"),
                payload.get("content"),
                payload.get("values"),
                payload.get("sheetTab"),
            )
        if tool_name == "sheets_delete_sheet":
            payload.update(
                {
                    "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
                    "sheetId": str(metadata.get("sheetId") or metadata.get("spreadsheetId") or metadata.get("targetId") or "").strip(),
                    "fileId": str(metadata.get("fileId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or metadata.get("targetId") or "").strip(),
                    "targetId": str(metadata.get("targetId") or metadata.get("spreadsheetId") or metadata.get("sheetId") or "").strip(),
                    "sheetName": str(metadata.get("sheetName") or metadata.get("targetName") or metadata.get("fileName") or "").strip(),
                    "targetName": str(metadata.get("targetName") or metadata.get("sheetName") or metadata.get("fileName") or "").strip(),
                    "fileName": str(metadata.get("fileName") or metadata.get("sheetName") or metadata.get("targetName") or "").strip(),
                }
            )
            return with_optional_instruction(
                payload,
                payload.get("spreadsheetId"),
                payload.get("targetId"),
                payload.get("sheetName"),
                payload.get("targetName"),
                payload.get("fileName"),
            )
        return with_optional_instruction(payload)

    if tool_name == "drive_upload_file":
        file_id = str(metadata.get("fileId") or metadata.get("telegramFileId") or "").strip()
        file_name = str(metadata.get("fileName") or metadata.get("targetName") or "").strip()
        mime_type = str(metadata.get("mimeType") or "").strip()
        folder_id = str(metadata.get("folderId") or metadata.get("targetFolderId") or "").strip()
        attachment_kind = str(metadata.get("attachmentKind") or "").strip()
        return with_optional_instruction(
            {
            "fileId": file_id,
            "telegramFileId": file_id,
            "fileName": file_name,
            "targetName": file_name,
            "mimeType": mime_type,
            "folderId": folder_id,
            "targetFolderId": folder_id,
            "attachmentKind": attachment_kind,
            "hasAttachment": bool(metadata.get("hasAttachment")),
            },
            file_id,
            file_name,
            mime_type,
            folder_id,
            attachment_kind,
            bool(metadata.get("hasAttachment")),
        )

    return dict(DIRECT_TOOL_DEFAULT_ARGS.get(tool_name, {}))
