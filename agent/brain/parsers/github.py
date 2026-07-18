from __future__ import annotations

import re
from typing import Any

from agent.brain.parsers.common import (
    any_keyword_matches,
    keyword_matches,
    normalize_query_text,
    _matches_action,
    CREATE_ACTION_CUES,
    UPDATE_ACTION_CUES,
    READ_ACTION_CUES,
    SEND_ACTION_CUES,
    VIEW_ACTION_CUES,
)

GITHUB_REPO_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
    r"(?:/(?:tree|blob)/(?P<ref>[^/\s?#]+)(?:/(?P<path>[^\s?#]+))?)?",
    flags=re.IGNORECASE,
)

GITHUB_PULL_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>\d+)",
    flags=re.IGNORECASE,
)

GITHUB_ISSUE_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)",
    flags=re.IGNORECASE,
)

GITHUB_RELEASE_TAG_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/releases/tag/(?P<tag>[^/\s?#]+)",
    flags=re.IGNORECASE,
)

GITHUB_RELEASE_LATEST_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/releases/latest",
    flags=re.IGNORECASE,
)

GITHUB_RELEASES_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/releases(?:[/?#].*)?$",
    flags=re.IGNORECASE,
)

GITHUB_ACCOUNT_REPO_CUES = (
    "repo cua toi",
    "repo của tôi",
    "repo cua minh",
    "repo của mình",
    "repos cua toi",
    "repos của tôi",
    "repos cua minh",
    "repos của mình",
    "danh sach repo",
    "danh sách repo",
    "liet ke repo",
    "liệt kê repo",
    "xem repo cua toi",
    "xem repo của tôi",
    "xem repo cua minh",
    "xem repo của mình",
    "github repos",
    "my repos",
)

GITHUB_REPO_SEARCH_CUES = (
    "tim repo",
    "tìm repo",
    "tim kiem repo",
    "tìm kiếm repo",
    "tim kiem cac repo",
    "tìm kiếm các repo",
    "tim cac repo",
    "tìm các repo",
    "search repo",
    "search repositories",
    "search repository",
    "find repo",
    "find repositories",
    "find repository",
    "repo theo topic",
    "repo theo language",
    "repo theo ngon ngu",
    "repo theo ngôn ngữ",
    "repo ve",
    "repo về",
    "cac repo",
    "các repo",
    "topic repo",
    "github repos by topic",
)

GITHUB_PULL_CUES = (
    "pull request",
    "pull requests",
    "pr",
    "merge request",
    "merg request",
    "xem pr",
    "list pr",
    "danh sach pr",
    "danh sách pr",
    "pulls",
)

GITHUB_ISSUE_CUES = (
    "issue",
    "issues",
    "bug",
    "ticket",
    "xem issue",
    "xem issues",
    "danh sach issue",
    "danh sách issue",
)

GITHUB_RELEASE_CUES = (
    "release",
    "releases",
    "version",
    "versions",
    "tag",
    "tags",
    "latest release",
    "release moi nhat",
    "release mới nhất",
    "ban phat hanh",
    "bản phát hành",
)


def _infer_github_hint(
    normalized: str,
    metadata: dict[str, Any] | None,
    help_request: bool,
) -> tuple[str, bool]:
    context = extract_github_repo_context(normalized, metadata)
    if not context:
        if help_request:
            return "github_help", True
        return "", False

    path = str(context.get("path") or "").strip()
    ref = str(context.get("ref") or "").strip()
    repo = str(context.get("repo") or "").strip()
    number = str(context.get("number") or "").strip()
    tag = str(context.get("tag") or "").strip()
    release_id = str(context.get("releaseId") or context.get("release_id") or "").strip()
    item_type = str(context.get("itemType") or "").strip()

    if any_keyword_matches(normalized, ("diff", "compare", "so sanh", "so sánh", "patch", "changes")):
        return "github_get_diff", True
    if item_type in {"release", "release_list"} or any_keyword_matches(normalized, GITHUB_RELEASE_CUES):
        if tag or release_id or "latest" in normalized or any_keyword_matches(normalized, ("moi nhat", "mới nhất", "recent release", "newest release")):
            return "github_get_release", True
        if any_keyword_matches(normalized, ("list", "liet ke", "liệt kê", "danh sach", "danh sách", "xem", "show", "recent", "gần đây", "gan day")):
            return "github_list_releases", True
        return "github_list_releases", True
    if item_type == "pull_request" or any_keyword_matches(normalized, GITHUB_PULL_CUES):
        if any_keyword_matches(normalized, ("tao pr", "tạo pr", "tao pull request", "tạo pull request", "create pull request", "open pull request")):
            return "github_create_pull_request", False
        if any_keyword_matches(normalized, ("comment", "binh luan", "bình luận", "nhan xet", "nhận xét")):
            return "github_comment_pull_request", False
        if number or any_keyword_matches(normalized, ("detail", "chi tiet", "chi tiết", "read", "doc", "open")):
            return "github_get_pull_request", True
        if any_keyword_matches(normalized, ("list", "liet ke", "liệt kê", "danh sach", "danh sách", "xem", "show", "open", "closed", "all")):
            return "github_list_pull_requests", True
        return "github_list_pull_requests", True
    if item_type == "issue" or any_keyword_matches(normalized, GITHUB_ISSUE_CUES):
        if _matches_action(normalized, CREATE_ACTION_CUES) or any_keyword_matches(normalized, ("create issue", "open issue")):
            return "github_create_issue", False
        if _matches_action(normalized, UPDATE_ACTION_CUES) or any_keyword_matches(normalized, ("close issue", "dong issue", "đóng issue", "reopen issue")):
            return "github_update_issue", False
        if _matches_action(normalized, SEND_ACTION_CUES) or any_keyword_matches(normalized, ("comment", "binh luan", "bình luận", "nhan xet", "nhận xét")):
            return "github_comment_issue", False
        if number or any_keyword_matches(normalized, ("detail", "chi tiet", "chi tiết", "read", "doc", "open")):
            return "github_get_issue", True
        if any_keyword_matches(normalized, ("list", "liet ke", "liệt kê", "danh sach", "danh sách", "xem", "show", "open", "closed", "all")):
            return "github_list_issues", True
        return "github_list_issues", True
    if any_keyword_matches(normalized, ("cau truc repo", "cấu trúc repo", "repo tree", "tree", "cay repo", "cây repo", "directory structure", "file tree")):
        return "github_get_repo_tree", True
    if any_keyword_matches(normalized, ("branch", "branches", "nhanh", "nhánh")):
        return "github_list_branches", True
    if re.search(r"\b[0-9a-f]{7,40}\b", normalized):
        if any_keyword_matches(normalized, ("commit", "commits", "chi tiet", "chi tiết", "details")):
            return "github_get_commit", True
    if any_keyword_matches(normalized, ("commit", "commits", "lịch sử commit", "lich su commit", "history")):
        return "github_list_commits", True
    if path and (
        _matches_action(normalized, READ_ACTION_CUES)
        or _matches_action(normalized, VIEW_ACTION_CUES)
        or any_keyword_matches(normalized, ("file", "code", "source", "doc", "đọc", "xem"))
    ):
        return "github_get_file", True
    if any_keyword_matches(normalized, ("readme", "read me", "tóm tắt readme", "tom tat readme", "summary readme", "summarize readme", "overview readme")):
        return "github_get_file", False
    if any_keyword_matches(normalized, ("doc file", "đọc file", "xem file", "read file", "source file", "file")):
        return "github_get_file", True
    if path:
        return "github_get_file", True
    if any_keyword_matches(normalized, ("search code", "tim code", "tìm code", "tim trong repo", "tìm trong repo", "code search", "find code", "search repository")):
        return "github_search_code", True
    if any_keyword_matches(normalized, ("repo", "repository", "source repo", "github repo", "thong tin repo", "thông tin repo", "xem repo", "repo nay", "repo này")):
        return "github_get_repo", True
    if ref and (any_keyword_matches(normalized, ("commit", "history", "lịch sử", "lich su")) or help_request):
        return "github_get_commit", True
    if help_request:
        return "github_help", True
    if repo:
        return "github_get_repo", False
    return "github_get_repo", False


def extract_github_repo_context(text: str, metadata: dict[str, Any] | None = None) -> dict[str, str]:
    source = " ".join(
        part
        for part in [
            str(text or "").strip(),
            str((metadata or {}).get("repoUrl") or (metadata or {}).get("repo_url") or "").strip(),
            str((metadata or {}).get("repo") or "").strip(),
            str((metadata or {}).get("owner") or "").strip(),
            str((metadata or {}).get("repoName") or (metadata or {}).get("repo_name") or "").strip(),
            str((metadata or {}).get("path") or (metadata or {}).get("filePath") or (metadata or {}).get("file_path") or "").strip(),
            str((metadata or {}).get("ref") or "").strip(),
        ]
        if part
    ).strip()
    if not source:
        return {}
    normalized_source = normalize_query_text(source)

    match = GITHUB_PULL_URL_PATTERN.search(source)
    if match:
        owner = match.group("owner") or ""
        repo = match.group("repo") or ""
        number = match.group("number") or ""
        repo_url = f"https://github.com/{owner}/{repo}"
        return {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "repoName": repo,
            "repoUrl": repo_url,
            "number": number,
            "itemType": "pull_request",
        }

    match = GITHUB_ISSUE_URL_PATTERN.search(source)
    if match:
        owner = match.group("owner") or ""
        repo = match.group("repo") or ""
        number = match.group("number") or ""
        repo_url = f"https://github.com/{owner}/{repo}"
        return {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "repoName": repo,
            "repoUrl": repo_url,
            "number": number,
            "itemType": "issue",
        }

    match = GITHUB_RELEASE_TAG_URL_PATTERN.search(source)
    if match:
        owner = match.group("owner") or ""
        repo = match.group("repo") or ""
        tag = match.group("tag") or ""
        repo_url = f"https://github.com/{owner}/{repo}"
        return {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "repoName": repo,
            "repoUrl": repo_url,
            "tag": tag,
            "releaseId": tag,
            "itemType": "release",
        }

    match = GITHUB_RELEASE_LATEST_URL_PATTERN.search(source)
    if match:
        owner = match.group("owner") or ""
        repo = match.group("repo") or ""
        repo_url = f"https://github.com/{owner}/{repo}"
        return {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "repoName": repo,
            "repoUrl": repo_url,
            "releaseId": "latest",
            "itemType": "release",
        }

    match = GITHUB_RELEASES_URL_PATTERN.search(source)
    if match:
        owner = match.group("owner") or ""
        repo = match.group("repo") or ""
        repo_url = f"https://github.com/{owner}/{repo}"
        return {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "repoName": repo,
            "repoUrl": repo_url,
            "itemType": "release_list",
        }

    match = GITHUB_REPO_URL_PATTERN.search(source)
    if match:
        owner = match.group("owner") or ""
        repo = match.group("repo") or ""
        repo_url = f"https://github.com/{owner}/{repo}"
        ref = match.group("ref") or ""
        path = match.group("path") or ""
        number = str((metadata or {}).get("number") or (metadata or {}).get("issueNumber") or (metadata or {}).get("prNumber") or "").strip()
        tag = str((metadata or {}).get("tag") or "").strip()
        release_id = str((metadata or {}).get("releaseId") or (metadata or {}).get("release_id") or "").strip()
        if not number and any_keyword_matches(normalized_source, GITHUB_PULL_CUES + GITHUB_ISSUE_CUES):
            number_match = re.search(r"(?:pull request|pull|pr|issue|issues|#)\s*#?\s*(\d+)", source, flags=re.IGNORECASE)
            if number_match:
                number = number_match.group(1).strip()
        if not tag and any_keyword_matches(normalized_source, GITHUB_RELEASE_CUES):
            tag_match = re.search(r"(?:release\s+tag|tag|version)\s*[:=#-]?\s*([A-Za-z0-9_.+-]+)", source, flags=re.IGNORECASE)
            if tag_match:
                tag = tag_match.group(1).strip()
        if not release_id and "latest" in normalized_source and any_keyword_matches(normalized_source, GITHUB_RELEASE_CUES):
            release_id = "latest"
        return {
            "repo": f"{owner}/{repo}",
            "owner": owner,
            "repoName": repo,
            "repoUrl": repo_url,
            "ref": ref,
            "path": path,
            "number": number,
            "tag": tag,
            "releaseId": release_id,
        }

    repo = str((metadata or {}).get("repo") or "").strip()
    owner = str((metadata or {}).get("owner") or "").strip()
    repo_name = str((metadata or {}).get("repoName") or (metadata or {}).get("repo_name") or "").strip()
    if repo:
        if "/" in repo and not owner and not repo_name:
            owner, repo_name = repo.split("/", 1)
        elif owner and not repo_name:
            repo_name = repo
        elif repo_name and not owner:
            owner = repo
        repo_name = repo_name or ""
        if owner and repo_name:
            number = str((metadata or {}).get("number") or (metadata or {}).get("issueNumber") or (metadata or {}).get("prNumber") or "").strip()
            tag = str((metadata or {}).get("tag") or "").strip()
            release_id = str((metadata or {}).get("releaseId") or (metadata or {}).get("release_id") or "").strip()
            return {
                "repo": f"{owner}/{repo_name}",
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": f"https://github.com/{owner}/{repo_name}",
                "ref": str((metadata or {}).get("ref") or "").strip(),
                "path": str((metadata or {}).get("path") or (metadata or {}).get("filePath") or (metadata or {}).get("file_path") or "").strip(),
                "number": number,
                "tag": tag,
                "releaseId": release_id,
            }

    github_action_cues = (
        "github",
        "repo",
        "repository",
        "diff",
        "compare",
        "commit",
        "branch",
        "branches",
        "file",
        "code",
        "search",
    )
    if "github.com/" in normalized_source or any(keyword_matches(normalized_source, cue) for cue in github_action_cues):
        plain = re.search(r"\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b", source)
        if plain:
            owner = plain.group(1)
            repo_name = plain.group(2)
            return {
                "repo": f"{owner}/{repo_name}",
                "owner": owner,
                "repoName": repo_name,
                "repoUrl": f"https://github.com/{owner}/{repo_name}",
                "ref": str((metadata or {}).get("ref") or "").strip(),
                "path": str((metadata or {}).get("path") or (metadata or {}).get("filePath") or (metadata or {}).get("file_path") or "").strip(),
                "number": str((metadata or {}).get("number") or (metadata or {}).get("issueNumber") or (metadata or {}).get("prNumber") or "").strip(),
                "tag": str((metadata or {}).get("tag") or "").strip(),
                "releaseId": str((metadata or {}).get("releaseId") or (metadata or {}).get("release_id") or "").strip(),
            }

    return {}
