from __future__ import annotations

from dataclasses import dataclass
import json
import re

from mia_core.capabilities import DIRECT_GATEWAY_TOOLS, DIRECT_ROUTE_TOOLS
from mia_core.error_envelope import ErrorEnvelope
from mia_core.memory import MemoryRepository
from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient
from mia_core.request_parser import build_direct_tool_args, should_allow_direct_route
from mia_core.response_normalizer import cap_visible_links, sanitize_final_text


def build_memory_recent_text(memory_repo: MemoryRepository, chat_id: str, limit: int = 5) -> str:
    rows = memory_repo.recent(chat_id=chat_id, limit=max(1, min(limit, 10)))
    if not rows:
        return "Mia chưa có memory nào đáng chú ý gần đây."

    lines = ["Memory gần đây:"]
    for index, row in enumerate(rows, start=1):
        memory_type = str(row.get("memory_type") or "general").strip()
        title = str(row.get("title") or "").strip()
        content = str(row.get("content") or row.get("chunk_text") or "").strip()
        snippet = content[:220].rstrip()
        if len(content) > 220:
            snippet += "..."
        prefix = f"{index}. [{memory_type}]"
        if title:
            prefix += f" {title}:"
        lines.append(f"{prefix} {snippet}".strip())
    return "\n".join(lines)


def _normalize_memory_text(value: str, limit: int = 7000) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _extract_payload_context(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    result = payload.get("result")
    if isinstance(result, dict):
        title = str(result.get("file_name") or result.get("fileName") or "").strip()
        text = str(
            result.get("formatted_summary")
            or result.get("summary")
            or result.get("text")
            or result.get("answer")
            or result.get("ocr_text")
            or ""
        ).strip()
        if title:
            parts.append(f"Tài liệu: {title}")
        if text:
            parts.append(f"Nội dung chính: {text}")
        document = result.get("document")
        if isinstance(document, dict):
            page_refs = document.get("page_refs") or document.get("pageRefs") or []
            if isinstance(page_refs, list) and page_refs:
                ref_lines: list[str] = []
                for ref in page_refs[:5]:
                    if not isinstance(ref, dict):
                        continue
                    page = ref.get("page") or ref.get("page_number") or ref.get("pageNumber")
                    snippet = str(ref.get("snippet") or ref.get("text") or ref.get("content") or "").strip()
                    if page and snippet:
                        ref_lines.append(f"Trang {page}: {snippet[:220]}")
                if ref_lines:
                    parts.append("Tham chiếu trang:\n" + "\n".join(ref_lines))
        if isinstance(result.get("data"), dict):
            data = result["data"]
            extra_text = str(
                data.get("formatted_summary")
                or data.get("summary")
                or data.get("text")
                or data.get("answer")
                or data.get("ocr_text")
                or ""
            ).strip()
            if extra_text and extra_text != text:
                parts.append(f"Chi tiết bổ sung: {_normalize_memory_text(extra_text, limit=2500)}")
            document = data.get("document")
            if isinstance(document, dict):
                page_refs = document.get("page_refs") or document.get("pageRefs") or []
                if isinstance(page_refs, list) and page_refs:
                    ref_lines = []
                    for ref in page_refs[:5]:
                        if not isinstance(ref, dict):
                            continue
                        page = ref.get("page") or ref.get("page_number") or ref.get("pageNumber")
                        snippet = str(ref.get("snippet") or ref.get("text") or ref.get("content") or "").strip()
                        if page and snippet:
                            ref_lines.append(f"Trang {page}: {snippet[:220]}")
                    if ref_lines:
                        parts.append("Tham chiếu trang:\n" + "\n".join(ref_lines))
    text_value = str(payload.get("text") or "").strip()
    if text_value and (not parts or text_value not in " ".join(parts)):
        parts.append(f"Kết quả: {text_value}")
    return "\n".join(parts).strip()


def _extract_web_payload_context(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    result = payload.get("result")
    if isinstance(result, dict):
        title = str(result.get("title") or result.get("canonical_url") or result.get("final_url") or "").strip()
        url = str(result.get("canonical_url") or result.get("final_url") or result.get("url") or "").strip()
        summary = str(result.get("summary") or result.get("text") or result.get("answer") or "").strip()
        data = result.get("data")
        content = ""
        if isinstance(data, dict):
            content = str(
                data.get("summary")
                or data.get("text")
                or data.get("content")
                or data.get("answer")
                or data.get("description")
                or ""
            ).strip()
        if title:
            parts.append(f"Tiêu đề: {title}")
        if url:
            parts.append(f"URL: {url}")
        if summary:
            parts.append(f"Tóm tắt: {summary}")
        if content and content != summary:
            parts.append(f"Nội dung: {_normalize_memory_text(content, limit=5000)}")
    text_value = str(payload.get("text") or "").strip()
    if text_value and (not parts or text_value not in " ".join(parts)):
        parts.append(f"Kết quả: {text_value}")
    return "\n".join(parts).strip()


def _parse_github_search_lines(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        match = re.match(
            r"^(?P<index>\d+)\.\s*(?P<name>[^|]+?)(?:\s*\|\s*(?P<rest>.*))?$",
            line,
        )
        if not match:
            continue
        name = str(match.group("name") or "").strip()
        rest = str(match.group("rest") or "").strip()
        url = ""
        description = ""
        stars = ""
        forks = ""
        language = ""
        if rest:
            parts = [part.strip() for part in rest.split("|") if part.strip()]
            for part in parts:
                if part.startswith("http://") or part.startswith("https://"):
                    url = part
                elif part.endswith("★") and not stars:
                    stars = part
                elif part.endswith("⑂") and not forks:
                    forks = part
                elif not language and len(part) <= 40 and re.fullmatch(r"[A-Za-z0-9_.#+-]+", part):
                    language = part
                elif not description:
                    description = part
                else:
                    description = f"{description} | {part}".strip(" |")
        rows.append(
            {
                "full_name": name,
                "html_url": url,
                "description": description,
                "stargazers_count": stars,
                "forks_count": forks,
                "language": language,
            }
        )
    return rows


def _extract_github_search_context(payload: dict[str, Any], *, limit: int = 10) -> str:
    text_value = str(payload.get("text") or "").strip()
    if text_value and ("1. " in text_value or text_value.startswith("Total matched")):
        return text_value

    parts: list[str] = []
    result = payload.get("result")
    data_value = payload.get("data")
    rows: list[dict[str, Any]] = []

    if isinstance(result, list):
        rows = [item for item in result if isinstance(item, dict)]
    elif isinstance(result, dict):
        nested_rows = result.get("items")
        if not isinstance(nested_rows, list):
            nested_rows = result.get("result")
        if isinstance(nested_rows, list):
            rows = [item for item in nested_rows if isinstance(item, dict)]
        elif isinstance(result.get("data"), list):
            rows = [item for item in result.get("data") if isinstance(item, dict)]
    if not rows and isinstance(data_value, list):
        rows = [item for item in data_value if isinstance(item, dict)]
    elif not rows and isinstance(data_value, dict):
        nested_rows = data_value.get("items")
        if not isinstance(nested_rows, list):
            nested_rows = data_value.get("result")
        if isinstance(nested_rows, list):
            rows = [item for item in nested_rows if isinstance(item, dict)]
        elif isinstance(data_value.get("data"), list):
            rows = [item for item in data_value.get("data") if isinstance(item, dict)]

    if text_value:
        parts.append(text_value)

    if not rows and text_value:
        rows = _parse_github_search_lines(text_value)

    if rows:
        repo_lines: list[str] = []
        for index, row in enumerate(rows[: max(1, min(limit, 10))], start=1):
            name = str(row.get("full_name") or row.get("name") or "").strip()
            description = str(row.get("description") or "").strip()
            stars = row.get("stargazers_count")
            forks = row.get("forks_count")
            language = str(row.get("language") or "").strip()
            url = str(row.get("html_url") or "").strip()
            if isinstance(stars, str) and stars.endswith("★"):
                star_text = stars
            else:
                star_text = f"{int(stars)}★" if isinstance(stars, (int, float)) and stars else ""
            if isinstance(forks, str) and forks.endswith("⑂"):
                fork_text = forks
            else:
                fork_text = f"{int(forks)}⑂" if isinstance(forks, (int, float)) and forks else ""
            metrics = [star_text, fork_text, language]
            metrics_text = " | ".join(part for part in metrics if part)
            line = f"{index}. {name}"
            if metrics_text:
                line += f" | {metrics_text}"
            if description:
                line += f" | {description}"
            if url:
                line += f" | {url}"
            repo_lines.append(line)
        if repo_lines:
            parts.append("Repos:\n" + "\n".join(repo_lines))

    return "\n".join(part for part in parts if part).strip()


def _extract_payload_trace(payload: dict[str, Any]) -> dict[str, Any]:
    trace = payload.get("trace")
    if isinstance(trace, dict):
        return trace
    result = payload.get("result")
    if isinstance(result, dict):
        nested_trace = result.get("trace")
        if isinstance(nested_trace, dict):
            return nested_trace
        data = result.get("data")
        if isinstance(data, dict):
            nested_trace = data.get("trace")
            if isinstance(nested_trace, dict):
                return nested_trace
    data = payload.get("data")
    if isinstance(data, dict):
        nested_trace = data.get("trace")
        if isinstance(nested_trace, dict):
            return nested_trace
    return {}


@dataclass
class DirectExecutor:
    memory_repo: MemoryRepository
    tool_gateway: N8nToolGatewayClient

    def execute(
        self,
        request: MiaChatRequest,
        context: MiaContext,
        hint_tool: str,
        *,
        allow_multistep: bool = False,
    ) -> MiaChatResponse | None:
        if not hint_tool or hint_tool not in DIRECT_ROUTE_TOOLS:
            return None
        if not allow_multistep and not should_allow_direct_route(hint_tool, request.text, request.metadata):
            return None

        request_id = context.request_id
        thread_id = request.resolved_thread_id()

        if hint_tool == "memory_recent":
            text = build_memory_recent_text(self.memory_repo, request.chat_id)
            return MiaChatResponse(
                final_text=cap_visible_links(sanitize_final_text(text), limit=3),
                tools_called=["memory_recent"],
                thread_id=thread_id,
                request_id=request_id,
                trace={},
            )

        gateway_name = DIRECT_GATEWAY_TOOLS.get(hint_tool)
        if not gateway_name:
            return None

        args = build_direct_tool_args(hint_tool, request.text, request.metadata)
        try:
            result = self.tool_gateway.run_tool(
                gateway_name,
                args,
                context,
                request_text=request.text,
            )
        except Exception:
            return None

        if not result.ok:
            error = result.error or ErrorEnvelope.build(
                code="tool_failed",
                category="external",
                severity="error",
                message=str(result.text or f"{hint_tool} failed."),
                user_message=str(result.text or "Mia gặp lỗi từ tool gateway."),
                retryable=False,
                request_id=request_id,
                thread_id=thread_id,
                chat_id=request.chat_id,
                details={
                    "tool_name": hint_tool,
                    "gateway_name": gateway_name,
                },
            )
            return MiaChatResponse(
                ok=False,
                final_text=error.display_text(),
                tools_called=[hint_tool],
                thread_id=thread_id,
                request_id=request_id,
                trace={
                    "error": error.model_dump(mode="json"),
                    "tool_gateway": result.payload,
                },
                error=error,
            )

        payload_data = result.payload.get("data") if isinstance(result.payload.get("data"), dict) else {}
        final_text_source = str(
            (payload_data or {}).get("text")
            or result.text
            or result.payload.get("text")
            or ""
        ).strip()
        final_text = cap_visible_links(sanitize_final_text(final_text_source), limit=3)
        if not final_text:
            return None

        if hint_tool in {"document_summarize", "document_search_answer", "document_extract_fields", "document_extract_text"}:
            try:
                file_name = str(args.get("fileName") or args.get("docName") or "").strip()
                title = file_name or f"{hint_tool}"
                context_text = _extract_payload_context(result.payload)
                if not context_text:
                    context_text = _normalize_memory_text(result.text, limit=4000)
                memory_content_lines = [f"Tài liệu: {title}", f"Tool: {hint_tool}", f"Yêu cầu: {request.text}"]
                if context_text:
                    memory_content_lines.append(context_text)
                self.memory_repo.write(
                    chat_id=request.chat_id,
                    content="\n".join(memory_content_lines).strip(),
                    memory_type="document_context",
                    title=title,
                    tags=["document", hint_tool, title] if title else ["document", hint_tool],
                    importance=4,
                    source_text=context_text or result.text,
                )
            except Exception:
                pass

        if hint_tool in {"read_url", "summarize_url"}:
            try:
                context_text = _extract_web_payload_context(result.payload)
                if context_text:
                    page_title = str(result.payload.get("title") or result.payload.get("data", {}).get("title") or "").strip()
                    self.memory_repo.write(
                        chat_id=request.chat_id,
                        content=context_text,
                        memory_type="url_context",
                        title=page_title or hint_tool,
                        tags=["web", "url_context", hint_tool, page_title or hint_tool],
                        importance=4,
                        source_text=context_text,
                    )
            except Exception:
                pass

        if hint_tool in {"github_search_repos", "github_list_user_repos"}:
            try:
                github_payload = payload_data if isinstance(payload_data, dict) and payload_data else result.payload
                search_context = _extract_github_search_context(github_payload, limit=int(args.get("limit") or 10))
                if search_context:
                    final_text = cap_visible_links(sanitize_final_text(search_context), limit=3)
                    title = str(args.get("query") or args.get("topic") or args.get("username") or "github search").strip() or "github search"
                    tags = ["github", "search_repos", title]
                    for value in (args.get("topic"), args.get("language"), args.get("sortBy")):
                        cleaned = str(value or "").strip()
                        if cleaned and cleaned not in tags:
                            tags.append(cleaned)
                    self.memory_repo.write(
                        chat_id=request.chat_id,
                        content=search_context,
                        memory_type="github_repo_search",
                        title=title,
                        tags=tags,
                        importance=4,
                        source_text=search_context,
                    )
                    followup = str(
                        (payload_data or {}).get("followupPrompt")
                        or (payload_data or {}).get("followup_prompt")
                        or result.payload.get("followupPrompt")
                        or result.payload.get("followup_prompt")
                        or ""
                    ).strip()
                    if not followup:
                        followup = (
                            "Anh muốn mình đi sâu repo nào? "
                            "Trả số thứ tự hoặc tên repo, ví dụ: repo 1."
                        )
                    if followup:
                        followup = f"\n\n{followup}"
                    final_text = f"{final_text}{followup}".strip()
            except Exception:
                pass

        return MiaChatResponse(
            final_text=final_text,
            tools_called=[hint_tool],
            thread_id=thread_id,
            request_id=request_id,
            trace=_extract_payload_trace(result.payload),
        )
