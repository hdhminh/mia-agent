from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from mia_core.capabilities import DETERMINISTIC_DIRECT_TOOLS, DIRECT_TOOL_DEFAULT_ARGS

from mia_core.parsers import (
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
from mia_core.parsers.common import SOFT_FOLLOWUP_PATTERN, GENERAL_TOOL_OVERVIEW_CUES
from mia_core.parsers.google import (
    _infer_google_service,
    _infer_calendar_hint,
    _infer_gmail_hint,
    _infer_workspace_hint,
)
from mia_core.parsers.github import (
    _infer_github_hint,
    GITHUB_ACCOUNT_REPO_CUES,
    GITHUB_REPO_SEARCH_CUES,
)
from mia_core.parsers.media import (
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

    if any_keyword_matches(normalized, ("gia vang", "sjc", "gold")):
        return RequestProfile(domain="general", hint_tool="gold_get_price", direct_confident=True, reason="gold request")

    if any_keyword_matches(normalized, ("ban con nho gi", "ban còn nhớ gì", "nho gi gan day", "nhớ gì gần đây", "memory gan day", "da luu gi", "đã lưu gì")):
        return RequestProfile(domain="general", hint_tool="memory_recent", direct_confident=True, reason="memory recent request")

    if any_keyword_matches(normalized, ("shortlink", "short link", "rut gon link", "rút gọn link", "tao link ngan", "tạo link ngắn")):
        return RequestProfile(domain="general", hint_tool="shortlink_create", direct_confident=True, reason="shortlink request")

    from mia_core.parsers.common import HELP_REQUEST_CUES
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
        from mia_core.parsers.web import URL_SUMMARY_CUES, URL_ASK_CUES, URL_READ_CUES
        if any_keyword_matches(normalized, URL_SUMMARY_CUES):
            return RequestProfile(domain="general", hint_tool="summarize_url", direct_confident=True, reason="specific url summary request")
        if any_keyword_matches(normalized, URL_ASK_CUES):
            return RequestProfile(domain="general", hint_tool="ask_url", direct_confident=False, reason="specific url question request")
        if any_keyword_matches(normalized, URL_READ_CUES) or normalize_query_text(text) == normalize_query_text(explicit_url):
            return RequestProfile(domain="general", hint_tool="read_url", direct_confident=True, reason="specific url read request")
        return RequestProfile(domain="general", hint_tool="read_url", direct_confident=True, reason="specific url read request")

    from mia_core.parsers.web import URL_ASK_CUES
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

    def normalize_url_instruction(value: str, url: str, *, fallback: str) -> str:
        cleaned = str(value or "")
        if url:
            cleaned = cleaned.replace(url, " ")
        cleaned = " ".join(cleaned.split()).strip()
        if normalize_query_text(cleaned) in {"nay", "link nay", "bai nay", "trang nay"}:
            cleaned = ""
        return cleaned or fallback

    if tool_name == "weather_get":
        location = strip_prefixes(
            text,
            ("thoi tiet", "thời tiết", "weather", "nhiet do", "nhiệt độ", "du bao thoi tiet", "dự báo thời tiết"),
        )
        location = re.sub(r"^(tai|tại|o|ở|cho toi|cho tôi|hom nay|hôm nay)\s+", "", location, flags=re.IGNORECASE)
        location = re.sub(
            r"\b(hom nay|hôm nay|bay gio|bây giờ|the nao|thế nào|ra sao|nhu the nao|như thế nào)\b",
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
            ("tim", "tìm", "tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "cho toi biet ve", "cho tôi biết về", "thong tin ve", "thông tin về"),
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
            fallback="tóm tắt link này" if tool_name == "summarize_url" else "đọc link này",
        )
        max_chars_value = metadata.get("maxChars") or metadata.get("max_chars") or 0
        try:
            max_chars = max(0, int(max_chars_value))
        except (TypeError, ValueError):
            max_chars = 0
        return {
            "url": url.strip(),
            "instruction": instruction.strip() or text,
            "text": instruction.strip() or text,
            "prompt": instruction.strip() or text,
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
            fallback="hỏi tiếp link này",
        )
        max_chars_value = metadata.get("maxChars") or metadata.get("max_chars") or 0
        try:
            max_chars = max(0, int(max_chars_value))
        except (TypeError, ValueError):
            max_chars = 0
        return {
            "url": url.strip(),
            "instruction": instruction.strip() or text,
            "question": instruction.strip() or text,
            "text": instruction.strip() or text,
            "prompt": instruction.strip() or text,
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
            return {
                "username": username,
                "visibility": visibility,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
                "page": max(1, int(metadata.get("page") or 1)),
                "instruction": text,
            }

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
            query_text = re.sub(r"^(ve|về)\s+", "", query_text, flags=re.IGNORECASE).strip()
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
            return {
                "query": query_value,
                "topic": raw_topic,
                "language": language,
                "sortBy": sort_by,
                "limit": max(1, min(int(metadata.get("limit") or 10), 100)),
                "page": max(1, int(metadata.get("page") or 1)),
                "instruction": text,
            }

        if tool_name == "github_get_repo_tree":
            tree_path = path or str(metadata.get("path") or metadata.get("filePath") or metadata.get("file_path") or "").strip()
            if tree_path.endswith("/"):
                tree_path = tree_path.rstrip("/")
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "path": tree_path,
                "ref": ref,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
                "instruction": text,
            }

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
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "query": query_text.strip(),
                "limit": max(1, min(int(metadata.get("limit") or 10), 10)),
                "instruction": text,
            }

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
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "path": file_path,
                "ref": ref,
                "maxChars": max(0, int(metadata.get("maxChars") or metadata.get("max_chars") or 4000)),
                "instruction": text,
            }

        if tool_name == "github_get_diff":
            if not base or not head:
                diff_match = re.search(r"\b([A-Za-z0-9_.:/-]+)\.\.\.([A-Za-z0-9_.:/-]+)\b", text)
                if diff_match:
                    base = base or diff_match.group(1)
                    head = head or diff_match.group(2)
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "base": base,
                "head": head,
                "instruction": text,
            }

        if tool_name == "github_get_commit":
            commit_ref = ref
            if not commit_ref:
                sha_match = re.search(r"\b[0-9a-f]{7,40}\b", text, flags=re.IGNORECASE)
                if sha_match:
                    commit_ref = sha_match.group(0)
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "ref": commit_ref,
                "instruction": text,
            }

        if tool_name == "github_list_commits":
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "ref": ref,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
                "instruction": text,
            }

        if tool_name == "github_list_branches":
            return {
                "repo": repo,
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": repo_url,
                "limit": max(1, min(int(metadata.get("limit") or 20), 100)),
                "instruction": text,
            }

        return {
            "repo": repo,
            "owner": owner,
            "repoName": repo_name,
            "repoUrl": repo_url,
            "instruction": text,
        }

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
            query = strip_prefixes(text, ("hoi", "hỏi", "search", "tim trong", "tìm trong", "trong file co", "trong file có"))
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
        query = strip_prefixes(text, ("tim doc", "tìm doc", "search doc", "tim tai lieu", "tìm tài liệu"))
        query = strip_soft_followup(query)
        return {"query": query.strip(), "docName": query.strip(), "limit": 3}

    if tool_name == "drive_search_file":
        query = strip_prefixes(text, ("tim file", "tìm file", "search file", "tim trong drive", "tìm trong drive", "tim tep", "tìm tệp"))
        query = strip_soft_followup(query)
        return {"query": query.strip(), "fileName": query.strip(), "limit": 3}

    if tool_name == "sheets_search_sheet":
        query = strip_prefixes(text, ("tim sheet", "tìm sheet", "search sheet", "tim bang tinh", "tìm bảng tính"))
        query = strip_soft_followup(query)
        return {"query": query.strip(), "sheetName": query.strip(), "limit": 3}

    if tool_name == "sheets_read_range":
        sheet_range = extract_sheet_range(text)
        sheet_name = strip_prefixes(
            text,
            ("xem range", "xem vung", "xem vùng", "read range", "doc range", "đọc range", "xem sheet", "doc sheet", "đọc sheet"),
        )
        if sheet_range:
            sheet_name = sheet_name.replace(sheet_range, " ")
        sheet_name = strip_soft_followup(" ".join(sheet_name.split()))
        return {
            "sheetName": sheet_name.strip(),
            "fileName": sheet_name.strip(),
            "range": sheet_range,
            "instruction": text,
        }

    if tool_name == "sheets_update_range":
        sheet_range = extract_sheet_range(text)
        sheet_name = strip_prefixes(
            text,
            ("cap nhat range", "cập nhật range", "cap nhat vung", "cập nhật vùng", "update range", "cap nhat sheet", "cập nhật sheet"),
        )
        if sheet_range:
            sheet_name = sheet_name.replace(sheet_range, " ")
        sheet_name = strip_soft_followup(" ".join(sheet_name.split()))
        return {
            "sheetName": sheet_name.strip(),
            "fileName": sheet_name.strip(),
            "range": sheet_range,
            "content": "",
            "values": [],
            "instruction": text,
        }

    if tool_name == "gmail_search_email":
        query = strip_prefixes(text, ("tim mail", "tìm mail", "tim email", "tìm email", "search mail", "search email"))
        query = strip_soft_followup(query)
        return {"query": query.strip(), "instruction": text}

    if tool_name == "gmail_search_by_sender":
        sender = strip_prefixes(text, ("tim email tu", "tìm email từ", "tim mail tu", "tìm mail từ", "from", "sender"))
        sender = re.sub(r"^(tu|từ)\s+", "", sender, flags=re.IGNORECASE)
        sender = strip_soft_followup(sender)
        return {
            "sender": sender.strip(),
            "query": sender.strip(),
            "subject": "",
            "limit": 3,
            "instruction": text,
        }

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
        return {
            "messageId": str(metadata.get("messageId") or metadata.get("message_id") or "").strip(),
            "query": query.strip(),
            "sender": str(metadata.get("sender") or "").strip(),
            "subject": str(metadata.get("subject") or "").strip(),
            "instruction": text,
        }

    if tool_name == "gmail_read_email":
        query = strip_prefixes(
            text,
            ("doc mail", "đọc mail", "doc email", "đọc email", "read mail", "read email", "chi tiet mail", "chi tiết mail", "chi tiet email", "chi tiết email"),
        )
        query = strip_soft_followup(query)
        return {"query": query.strip(), "instruction": text}

    if tool_name == "docs_read_doc":
        doc_name = strip_prefixes(
            text,
            ("xem doc", "doc doc", "đọc doc", "read doc", "noi dung doc", "nội dung doc", "xem tài liệu", "đọc tài liệu"),
        )
        doc_name = strip_soft_followup(doc_name)
        return {"docName": doc_name.strip(), "fileName": doc_name.strip(), "instruction": text}

    if tool_name == "sheets_read_sheet":
        sheet_name = strip_prefixes(
            text,
            ("xem sheet", "doc sheet", "đọc sheet", "read sheet", "xem bảng tính", "đọc bảng tính"),
        )
        sheet_range = extract_sheet_range(sheet_name)
        if sheet_range:
            sheet_name = sheet_name.replace(sheet_range, " ")
        sheet_name = strip_soft_followup(" ".join(sheet_name.split()))
        return {
            "sheetName": sheet_name.strip(),
            "fileName": sheet_name.strip(),
            "range": sheet_range,
            "instruction": text,
        }

    if tool_name == "calendar_find_event":
        query = strip_prefixes(
            text,
            ("tim lich", "tìm lịch", "tim su kien", "tìm sự kiện", "search event", "find event", "xem lich", "xem lịch", "lich", "lịch"),
        )
        query = re.sub(
            r"\b(hom nay|hôm nay|ngay mai|ngày mai|mai|tuan sau|tuần sau|tuan nay|tuần này|cuoi tuan nay|cuối tuần này|cuoi tuan sau|cuối tuần sau|thu\s*[2-7]|thứ\s*[2-7]|chu nhat|chủ nhật)\b",
            " ",
            query,
            flags=re.IGNORECASE,
        )
        query = strip_soft_followup(" ".join(query.split()))
        date_from, date_to = _calendar_range_from_text(text)
        return {
            "query": query.strip(),
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": 3,
        }

    if tool_name == "calendar_find_free_slot":
        start_at, end_at = _calendar_range_from_text(text)
        duration_minutes = int(metadata.get("durationMinutes") or metadata.get("duration_minutes") or 60)
        return {
            "date": "",
            "startAt": start_at,
            "endAt": end_at,
            "durationMinutes": max(15, min(duration_minutes, 1440)),
            "calendarId": str(metadata.get("calendarId") or "").strip(),
            "instruction": text,
        }

    if tool_name == "calendar_reschedule_event":
        start_at, end_at = _calendar_range_from_text(text)
        return {
            "eventId": str(metadata.get("eventId") or metadata.get("event_id") or "").strip(),
            "query": strip_soft_followup(
                strip_prefixes(text, ("doi lich", "đổi lịch", "doi gio", "đổi giờ", "reschedule", "move meeting", "postpone"))
            ),
            "startAt": str(metadata.get("startAt") or start_at).strip(),
            "endAt": str(metadata.get("endAt") or end_at).strip(),
            "timezone": str(metadata.get("timezone") or "").strip(),
            "calendarId": str(metadata.get("calendarId") or "").strip(),
            "instruction": text,
        }

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
        payload = {"instruction": text}
        if tool_name == "docs_update_doc":
            payload.update(
                {
                    "documentId": str(metadata.get("documentId") or metadata.get("docId") or "").strip(),
                    "docId": str(metadata.get("documentId") or metadata.get("docId") or "").strip(),
                    "docName": str(metadata.get("docName") or metadata.get("doc_name") or "").strip(),
                    "content": str(metadata.get("content") or metadata.get("text") or "").strip(),
                }
            )
        if tool_name == "sheets_update_range":
            payload.update(
                {
                    "spreadsheetId": str(metadata.get("spreadsheetId") or metadata.get("sheetId") or "").strip(),
                    "sheetName": str(metadata.get("sheetName") or metadata.get("sheet_name") or "").strip(),
                    "range": str(metadata.get("range") or metadata.get("rangeName") or "").strip(),
                    "sheetTab": str(metadata.get("sheetTab") or metadata.get("sheet_tab") or "").strip(),
                    "content": str(metadata.get("content") or text).strip(),
                    "values": metadata.get("values") or [],
                }
            )
        return payload

    if tool_name == "drive_upload_file":
        file_id = str(metadata.get("fileId") or "").strip()
        file_name = str(metadata.get("fileName") or "").strip()
        mime_type = str(metadata.get("mimeType") or "").strip()
        folder_id = str(metadata.get("folderId") or "").strip()
        attachment_kind = str(metadata.get("attachmentKind") or "").strip()
        return {
            "instruction": text,
            "fileId": file_id,
            "telegramFileId": file_id,
            "fileName": file_name,
            "mimeType": mime_type,
            "folderId": folder_id,
            "attachmentKind": attachment_kind,
            "hasAttachment": bool(metadata.get("hasAttachment")),
        }

    return dict(DIRECT_TOOL_DEFAULT_ARGS.get(tool_name, {}))
